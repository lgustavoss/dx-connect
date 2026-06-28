import base64
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_

from app.database import get_db
from app.models.atendente import Atendente
from app.models.ticket import Ticket, TicketMensagem
from app.models.status_ticket import StatusTicket
from app.models.empresa import Empresa
from app.models.setor import Setor
from app.models.rede import Rede
from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa
from app.models.whatsapp_chat import WhatsappChat, WhatsappChatTicket, WhatsappMensagem, WhatsappSettings
from app.models.whatsapp_chat_read import WhatsappChatRead as WhatsappChatReadModel
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.whatsapp_chat import (
    WhatsappAbrirTicketBody,
    WhatsappAvaliacaoRead,
    WhatsappChatComentarioInternoCreate,
    WhatsappChatDemandaCreate,
    WhatsappChatDemandaRead,
    WhatsappChatMensagemCreate,
    WhatsappChatRead,
    WhatsappMensagemRead,
    WhatsappTransferirChatBody,
    WhatsappVincularFuncionarioBody,
    WhatsappCadastrarFuncionarioBody,
    WhatsappVincularTicketBody,
    WhatsappEmpresaOpcaoRead,
    WhatsappFuncionarioOpcaoRead,
    WhatsappFuncionarioCatalogoRead,
    WhatsappRedeCatalogoRead,
    WhatsappEmpresaCatalogoRead,
)
from app.services.funcionario_escopo import empresa_ids_vinculados, rede_id_efetiva, sincronizar_vinculos_empresas, validar_empresa_ids_na_rede
from app.services.funcionario_rede_resolver import assert_email_unico_por_rede
from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, obter_atendente_atual
from app.api.tickets import _gerar_protocolo, _pode_ver_ticket
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.config import settings
from app.services import evolution_api
from app.services.whatsapp_auto_messages import (
    DEFAULT_AUTO_MSG_ASSUMIDO,
    DEFAULT_AUTO_MSG_ENCERRADO,
    resolver_nome_empresa_para_template,
)
from app.services.whatsapp_avaliacao import mensagem_oculta_na_conversa
from app.services.whatsapp_media_storage import caminho_absoluto_arquivo, gravar_bytes_em_disco
from app.services.realtime_emit import emit_chat_fila_from_model, emit_chat_mensagem_from_models
from app.services.ticket_distribuicao import pos_criar_ticket_na_fila

router = APIRouter(prefix="/whatsapp/chats", tags=["whatsapp-chats"])

logger = logging.getLogger(__name__)

_MAX_PAGE = 100
_DEFAULT_PAGE = 20

_CHAT_LOAD_OPTIONS = (
    joinedload(WhatsappChat.atendente),
    joinedload(WhatsappChat.setor),
    joinedload(WhatsappChat.funcionario_rede),
    joinedload(WhatsappChat.empresa),
)


@router.get("/transfer/setores", response_model=list[dict])
def listar_setores_para_transferencia(
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    """Lista TODOS os setores ativos para transferência (não implica permissão de visualização de chats)."""
    rows = db.query(Setor).filter(Setor.ativo.is_(True)).order_by(Setor.nome.asc(), Setor.id.asc()).all()
    return [{"id": s.id, "nome": s.nome} for s in rows]


def _settings_envio(db: Session) -> WhatsappSettings:
    row = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if not row or not row.evolution_base_url or not row.evolution_instance_name or not row.evolution_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integração WhatsApp incompleta. Administrador deve preencher URL, instância e API key.",
        )
    return row


def _evolution_configurada(st: WhatsappSettings | None) -> bool:
    return bool(
        st
        and st.evolution_base_url
        and st.evolution_instance_name
        and st.evolution_api_key
    )


def _remote_jid_from_wa_id(wa_id: str) -> str:
    digits = re.sub(r"\D", "", wa_id or "")
    return f"{digits}@s.whatsapp.net" if digits else ""


def _quoted_message_body(ref: WhatsappMensagem) -> dict:
    corpo = (ref.corpo or "").strip()
    tipo = (ref.tipo_midia or "texto").strip().lower()
    if tipo in ("", "texto"):
        return {"conversation": corpo[:2000] or " "}
    if tipo == "imagem":
        return {"imageMessage": {"caption": corpo[:200]}} if corpo else {"conversation": "[Imagem]"}
    if tipo == "video":
        return {"videoMessage": {"caption": corpo[:200]}} if corpo else {"conversation": "[Vídeo]"}
    if tipo == "audio":
        return {"conversation": "[Áudio]"}
    if tipo == "figurinha":
        return {"conversation": "[Figurinha]"}
    return {"conversation": corpo[:200] or "[Documento]"}


def _quoted_evolution_payload(db: Session, chat: WhatsappChat, quoted_wa_message_id: str) -> dict:
    q = (quoted_wa_message_id or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Citação inválida.")
    ref = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.wa_message_id == q)
        .first()
    )
    if not ref:
        raise HTTPException(
            status_code=400,
            detail="Mensagem citada não encontrada neste chat (use o id da mensagem no WhatsApp, "
            "campo wa_message_id na listagem de mensagens).",
        )
    remote_jid = _remote_jid_from_wa_id(chat.wa_id)
    from_me = ref.direcao == "outbound"
    return {
        "key": {
            "id": q,
            "remoteJid": remote_jid,
            "fromMe": from_me,
        },
        "message": _quoted_message_body(ref),
    }


def _preview_citacao(ref: WhatsappMensagem) -> str | None:
    s = (ref.corpo or "").strip()[:500]
    return s or None


def _mediatype_evolution(slug: str) -> str:
    s = (slug or "").strip().lower()
    return {
        "imagem": "image",
        "image": "image",
        "video": "video",
        "audio": "audio",
        "documento": "document",
        "document": "document",
    }.get(s, "document")


def _tipo_midia_db(slug: str) -> str:
    s = (slug or "").strip().lower()
    if s in ("imagem", "image"):
        return "imagem"
    if s == "video":
        return "video"
    if s == "audio":
        return "audio"
    return "documento"


def _rotulo_midia_outbound(tipo_db: str) -> str:
    return {
        "imagem": "[Imagem enviada]",
        "video": "[Vídeo enviado]",
        "audio": "[Áudio enviado]",
        "documento": "[Documento enviado]",
    }.get(tipo_db, "[Ficheiro enviado]")


def _sanitizar_nome_ficheiro(name: str | None, fallback: str) -> str:
    raw = (name or fallback or "file").strip() or "file"
    safe = "".join(ch for ch in raw if ch.isalnum() or ch in "._- ")
    return (safe.strip() or fallback)[:200]


def _render_template(
    template: str,
    *,
    db: Session,
    chat: WhatsappChat,
    atendente: Atendente | None = None,
    st: WhatsappSettings | None = None,
    atendente_nome: str | None = None,
) -> str:
    t = (template or "").strip()
    if not t:
        return ""
    nome = (chat.cliente_nome or "").strip() or "Cliente"
    nome_atendente = (atendente_nome or "").strip() or (atendente.nome if atendente else "").strip() or "BOT"
    nome_empresa = resolver_nome_empresa_para_template(db)
    return (
        t.replace("{nome}", nome)
        .replace("{atendente}", nome_atendente)
        .replace("{protocolo}", chat.protocolo)
        .replace("{telefone}", chat.wa_id)
        .replace("{{nome_cliente}}", nome)
        .replace("{{atendente}}", nome_atendente)
        .replace("{{protocolo}}", chat.protocolo)
        .replace("{{telefone}}", chat.wa_id)
        .replace("{{nome_empresa}}", nome_empresa)
    )


def _enviar_texto_whatsapp(
    db: Session,
    *,
    chat: WhatsappChat,
    texto: str,
    atendente: Atendente | None,
    evento_sistema: str | None,
    quoted_wa_message_id: str | None = None,
) -> WhatsappMensagem:
    texto_eff = (texto or "").strip()
    if not texto_eff:
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    # Quando o atendente envia manualmente pelo DX Connect, prefixa o nome no texto
    # para ficar visível no WhatsApp do cliente (padrão: "[ Nome ]: mensagem").
    # A saudação ao assumir o chat usa o mesmo prefixo do atendente (não BOT).
    if atendente is not None and evento_sistema in (None, "auto_assumido"):
        nome = (atendente.nome or "").strip()
        if nome and not texto_eff.startswith("["):
            texto_eff = f"[ {nome} ]: {texto_eff}"
    elif evento_sistema is not None:
        if not texto_eff.startswith("["):
            texto_eff = f"[ BOT ]: {texto_eff}"
    if evento_sistema:
        exist = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.evento_sistema == evento_sistema)
            .first()
        )
        if exist:
            return exist
    st = _settings_envio(db)
    quoted_payload = None
    q_wa: str | None = None
    q_prev: str | None = None
    if quoted_wa_message_id and str(quoted_wa_message_id).strip() and evento_sistema is None:
        q_wa = str(quoted_wa_message_id).strip()
        quoted_payload = _quoted_evolution_payload(db, chat, q_wa)
        ref = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.wa_message_id == q_wa)
            .first()
        )
        q_prev = _preview_citacao(ref) if ref else None
    ok, err, sent_wa_id = evolution_api.evolution_send_text(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        chat.wa_id,
        texto_eff,
        quoted=quoted_payload,
    )
    if not ok:
        raise HTTPException(status_code=502, detail=err or "Falha ao enviar pela Evolution API")
    m = WhatsappMensagem(
        chat_id=chat.id,
        direcao="outbound",
        corpo=texto_eff,
        tipo_midia="texto",
        mimetype=None,
        midia_nome_arquivo=None,
        wa_message_id=sent_wa_id,
        quoted_wa_message_id=q_wa,
        quoted_corpo_preview=q_prev,
        atendente_id=atendente.id if atendente else None,
        evento_sistema=evento_sistema,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    emit_chat_mensagem_from_models(db, chat, m, exclude_atendente_id=atendente.id if atendente else None)
    return m


def _ticket_ids(db: Session, chat_id: int) -> list[int]:
    return [x[0] for x in db.query(WhatsappChatTicket.ticket_id).filter(WhatsappChatTicket.chat_id == chat_id).all()]


def _empresa_nome_exibicao(emp: Empresa | None) -> str | None:
    if not emp:
        return None
    for raw in (emp.nome_fantasia, emp.nome, emp.razao_social):
        if raw and str(raw).strip():
            return str(raw).strip()
    return None


def _funcionario_no_tenant(db: Session, atendente: Atendente, funcionario_id: int) -> FuncionarioRede | None:
    func = db.query(FuncionarioRede).filter(FuncionarioRede.id == funcionario_id).first()
    if not func or not func.ativo:
        return None
    rede_id = rede_id_efetiva(db, func)
    if rede_id is not None:
        rede = db.query(Rede).filter(Rede.id == rede_id, Rede.tenant_id == atendente.tenant_id).first()
        if rede:
            return func
    if func.empresa_id is not None:
        emp = (
            db.query(Empresa)
            .filter(Empresa.id == func.empresa_id, Empresa.tenant_id == atendente.tenant_id)
            .first()
        )
        if emp:
            return func
    vinculo = (
        db.query(FuncionarioRedeEmpresa)
        .join(Empresa, Empresa.id == FuncionarioRedeEmpresa.empresa_id)
        .filter(
            FuncionarioRedeEmpresa.funcionario_id == func.id,
            Empresa.tenant_id == atendente.tenant_id,
        )
        .first()
    )
    return func if vinculo else None


def _empresas_funcionario(db: Session, func: FuncionarioRede) -> list[WhatsappEmpresaOpcaoRead]:
    ids = empresa_ids_vinculados(db, func, apenas_ativas=True)
    if not ids:
        return []
    rows = db.query(Empresa).filter(Empresa.id.in_(ids)).order_by(Empresa.nome.asc(), Empresa.id.asc()).all()
    return [WhatsappEmpresaOpcaoRead(id=e.id, nome=_empresa_nome_exibicao(e) or e.nome) for e in rows]


def _resolver_empresa_vinculo(
    db: Session,
    atendente: Atendente,
    func: FuncionarioRede,
    empresa_id: int | None,
) -> Empresa:
    emp_ids = empresa_ids_vinculados(db, func, apenas_ativas=True)
    if not emp_ids:
        raise HTTPException(status_code=400, detail="Funcionário sem empresas vinculadas")
    escolhida: int
    if len(emp_ids) == 1:
        escolhida = next(iter(emp_ids))
    elif empresa_id is None:
        raise HTTPException(status_code=400, detail="Selecione a empresa do funcionário")
    elif int(empresa_id) not in emp_ids:
        raise HTTPException(status_code=400, detail="Empresa inválida para este funcionário")
    else:
        escolhida = int(empresa_id)
    emp = db.query(Empresa).filter(Empresa.id == escolhida, Empresa.tenant_id == atendente.tenant_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return emp


def _criar_funcionario_rede(
    db: Session,
    atendente: Atendente,
    *,
    nome: str,
    email: str | None,
    tipo: str,
    escopo_empresas: str,
    rede_id: int,
    empresa_id: int | None,
    empresa_ids: list[int],
) -> FuncionarioRede:
    tipo_eff = (tipo or "colaborador").strip().lower()
    if tipo_eff not in ("colaborador", "supervisor", "socio"):
        raise HTTPException(status_code=400, detail="Tipo de funcionário inválido")
    escopo = (escopo_empresas or "selected").strip().lower()
    if escopo not in ("all", "selected"):
        raise HTTPException(status_code=400, detail="escopo_empresas deve ser all ou selected")
    if tipo_eff == "socio" and escopo != "all":
        escopo = "all"
    ids = list(dict.fromkeys(empresa_ids or []))
    if empresa_id and int(empresa_id) not in ids:
        ids.insert(0, int(empresa_id))
    rede = db.query(Rede).filter(Rede.id == rede_id, Rede.tenant_id == atendente.tenant_id).first()
    if not rede:
        raise HTTPException(status_code=404, detail="Rede não encontrada")
    if escopo == "selected" and not ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma empresa da rede")
    if escopo == "selected":
        try:
            validar_empresa_ids_na_rede(db, int(rede_id), ids)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        emps = db.query(Empresa).filter(Empresa.id.in_(ids)).all()
        if any(int(e.tenant_id) != int(atendente.tenant_id) for e in emps):
            raise HTTPException(status_code=400, detail="Empresa inválida para este tenant")
    email_norm = (email or "").strip() or None
    if email_norm:
        try:
            assert_email_unico_por_rede(db, email=email_norm, rede_id=int(rede_id))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    emp_colab_id: int | None = None
    if escopo == "selected" and tipo_eff == "colaborador" and len(ids) == 1:
        emp_colab_id = ids[0]
    f = FuncionarioRede(
        nome=nome.strip(),
        email=email_norm,
        tipo=tipo_eff,
        escopo_empresas=escopo,
        ativo=True,
        rede_id=int(rede_id),
        empresa_id=emp_colab_id,
    )
    db.add(f)
    db.flush()
    registrar_audit(db, "funcionario_rede", f.id, "create", atendente.id)
    sincronizar_vinculos_empresas(
        db,
        f,
        escopo=escopo,
        rede_id=int(rede_id),
        empresa_ids=ids if escopo == "selected" else None,
    )
    db.refresh(f)
    return f


def _chat_read(db: Session, c: WhatsappChat, *, revelar_avaliacao: bool = False) -> WhatsappChatRead:
    nota = getattr(c, "avaliacao_nota", None) if revelar_avaliacao else None
    respondida = getattr(c, "avaliacao_respondida_at", None) if revelar_avaliacao else None
    solicitada = bool(getattr(c, "avaliacao_solicitada", False)) if revelar_avaliacao else False
    func = getattr(c, "funcionario_rede", None)
    emp = getattr(c, "empresa", None)
    return WhatsappChatRead(
        id=c.id,
        protocolo=c.protocolo,
        wa_id=c.wa_id,
        cliente_nome=c.cliente_nome,
        estado=c.estado,
        setor_id=getattr(c, "setor_id", None),
        setor_nome=c.setor.nome if getattr(c, "setor", None) else None,
        atendente_id=c.atendente_id,
        atendente_nome=c.atendente.nome if c.atendente else None,
        created_at=c.created_at,
        atendimento_inicio_at=c.atendimento_inicio_at,
        encerramento_at=c.encerramento_at,
        avaliacao_nota=nota,
        avaliacao_respondida_at=respondida,
        avaliacao_solicitada=solicitada,
        ticket_ids=_ticket_ids(db, c.id),
        funcionario_rede_id=getattr(c, "funcionario_rede_id", None),
        funcionario_nome=func.nome if func else None,
        funcionario_email=func.email if func else None,
        funcionario_tipo=func.tipo if func else None,
        empresa_id=getattr(c, "empresa_id", None),
        empresa_nome=_empresa_nome_exibicao(emp),
    )


def _avaliacao_read(c: WhatsappChat) -> WhatsappAvaliacaoRead:
    nota = getattr(c, "avaliacao_nota", None)
    solicitada = bool(getattr(c, "avaliacao_solicitada", False))
    return WhatsappAvaliacaoRead(
        chat_id=c.id,
        protocolo=c.protocolo,
        wa_id=c.wa_id,
        cliente_nome=c.cliente_nome,
        atendente_id=c.atendente_id,
        atendente_nome=c.atendente.nome if c.atendente else None,
        setor_id=getattr(c, "setor_id", None),
        setor_nome=c.setor.nome if getattr(c, "setor", None) else None,
        nota=nota,
        avaliacao_respondida_at=getattr(c, "avaliacao_respondida_at", None),
        encerramento_at=c.encerramento_at,
        sem_avaliacao=solicitada and nota is None,
    )


def _exigir_responsavel_envio_cliente(c: WhatsappChat, atendente: Atendente) -> None:
    """Somente o atendente responsável envia mensagem/mídia ao WhatsApp do cliente (#403)."""
    if c.atendente_id != atendente.id:
        raise HTTPException(
            status_code=403,
            detail="Apenas o atendente responsável pode enviar mensagens ao cliente. Use comentário interno.",
        )


def _pode_registrar_demanda(db: Session, atendente: Atendente, c: WhatsappChat) -> bool:
    if c.estado != "em_atendimento":
        return False
    if not _pode_ver_chat(db, atendente, c):
        return False
    if atendente.role == "admin":
        return True
    return c.atendente_id == atendente.id


def _pode_ver_chat(db: Session, atendente: Atendente, c: WhatsappChat) -> bool:
    if atendente.role == "admin":
        return True
    if c.atendente_id == atendente.id:
        return True
    vis = ids_setores_visiveis_atendente(db, atendente)
    # Chats without a setor_id are considered public (the queue). Allow
    # visibility to attendants for queue items (so they can assume and
    # view messages while waiting). For other states (e.g. encerrado)
    # require either being the attendant or having the setor visible.
    if c.setor_id is None:
        return c.estado == "aguardando_atendente"
    if c.estado in ("aguardando_atendente", "encerrado", "aguardando_avaliacao"):
        return c.setor_id in vis
    return False


def _mensagem_read(m: WhatsappMensagem) -> WhatsappMensagemRead:
    midia_ok = bool(m.midia_nome_arquivo and str(m.midia_nome_arquivo).strip())
    return WhatsappMensagemRead(
        id=m.id,
        chat_id=m.chat_id,
        direcao=m.direcao,
        corpo=m.corpo,
        tipo_midia=m.tipo_midia,
        mimetype=m.mimetype,
        midia_disponivel=midia_ok,
        evento_sistema=getattr(m, "evento_sistema", None),
        wa_message_id=m.wa_message_id,
        quoted_wa_message_id=getattr(m, "quoted_wa_message_id", None),
        quoted_corpo_preview=getattr(m, "quoted_corpo_preview", None),
        atendente_id=m.atendente_id,
        atendente_nome=m.atendente.nome if m.atendente else None,
        created_at=m.created_at,
    )


@router.get("/fila", response_model=list[WhatsappChatRead])
def listar_fila(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(
        WhatsappChat.estado == "aguardando_atendente"
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter((WhatsappChat.setor_id.is_(None)) | (WhatsappChat.setor_id.in_(vis)))
    rows = q.order_by(WhatsappChat.created_at.asc()).all()
    return [_chat_read(db, c) for c in rows]


@router.get("/meus", response_model=list[WhatsappChatRead])
def listar_meus_ativos(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(WhatsappChat.estado == "em_atendimento")
    )
    if atendente.role != "admin":
        q = q.filter(WhatsappChat.atendente_id == atendente.id)
    rows = q.order_by(WhatsappChat.atendimento_inicio_at.desc().nullslast()).all()
    return [_chat_read(db, c) for c in rows]


@router.get("/encerrados", response_model=ListaPaginada[WhatsappChatRead])
def listar_encerrados(
    busca: str | None = Query(None, description="Busca por protocolo, telefone ou contato"),
    protocolo: str | None = Query(None, description="Filtro por protocolo"),
    wa_id: str | None = Query(None, description="Filtro por número ou WhatsApp ID"),
    atendente_id: int | None = Query(None, ge=1, description="Filtro por atendente que encerrou"),
    encerramento_inicio: datetime | None = Query(None, description="Filtro por data de encerramento a partir de"),
    encerramento_fim: datetime | None = Query(None, description="Filtro por data de encerramento até"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.estado == "encerrado")
    if protocolo:
        q = q.filter(WhatsappChat.protocolo.ilike(f"%{protocolo}%"))
    if wa_id:
        q = q.filter(WhatsappChat.wa_id.ilike(f"%{wa_id}%"))
    if busca:
        term = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                WhatsappChat.protocolo.ilike(term),
                WhatsappChat.wa_id.ilike(term),
                WhatsappChat.cliente_nome.ilike(term),
            )
        )
    if atendente_id:
        q = q.filter(WhatsappChat.atendente_id == atendente_id)
    if encerramento_inicio:
        q = q.filter(WhatsappChat.encerramento_at >= encerramento_inicio)
    if encerramento_fim:
        q = q.filter(WhatsappChat.encerramento_at <= encerramento_fim)
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(or_(WhatsappChat.atendente_id == atendente.id, WhatsappChat.setor_id.in_(vis)))
    total = q.count()
    rows = q.order_by(desc(WhatsappChat.encerramento_at), desc(WhatsappChat.id)).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_chat_read(db, c, revelar_avaliacao=True) for c in rows], total=total)


@router.get("/avaliacoes", response_model=ListaPaginada[WhatsappAvaliacaoRead])
def listar_avaliacoes(
    busca: str | None = Query(None, description="Busca por protocolo, telefone ou contato"),
    atendente_id: int | None = Query(None, ge=1),
    nota_min: int | None = Query(None, ge=1, le=5),
    nota_max: int | None = Query(None, ge=1, le=5),
    encerramento_inicio: datetime | None = Query(None),
    encerramento_fim: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    q = (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(WhatsappChat.avaliacao_solicitada.is_(True))
    )
    if busca:
        term = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                WhatsappChat.protocolo.ilike(term),
                WhatsappChat.wa_id.ilike(term),
                WhatsappChat.cliente_nome.ilike(term),
            )
        )
    if atendente_id:
        q = q.filter(WhatsappChat.atendente_id == atendente_id)
    if nota_min is not None:
        q = q.filter(WhatsappChat.avaliacao_nota >= nota_min)
    if nota_max is not None:
        q = q.filter(WhatsappChat.avaliacao_nota <= nota_max)
    if encerramento_inicio:
        q = q.filter(WhatsappChat.encerramento_at >= encerramento_inicio)
    if encerramento_fim:
        q = q.filter(WhatsappChat.encerramento_at <= encerramento_fim)
    total = q.count()
    rows = q.order_by(desc(WhatsappChat.encerramento_at), desc(WhatsappChat.id)).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_avaliacao_read(c) for c in rows], total=total)


@router.get("/por-ticket/{ticket_id}", response_model=list[WhatsappChatRead])
def listar_por_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=403, detail="Sem permissão para este ticket")
    chat_ids = [r[0] for r in db.query(WhatsappChatTicket.chat_id).filter(WhatsappChatTicket.ticket_id == ticket_id).all()]
    if not chat_ids:
        return []
    rows = (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(WhatsappChat.id.in_(chat_ids))
        .order_by(desc(WhatsappChat.id))
        .all()
    )
    return [_chat_read(db, c) for c in rows]


@router.get("/funcionarios", response_model=list[WhatsappFuncionarioOpcaoRead])
def buscar_funcionarios(
    busca: str = Query(..., min_length=1, description="Nome ou e-mail do funcionário"),
    limit: int = Query(20, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    term = f"%{busca.strip()}%"
    rede_ids = [int(r[0]) for r in db.query(Rede.id).filter(Rede.tenant_id == atendente.tenant_id).all()]
    empresa_ids = [int(r[0]) for r in db.query(Empresa.id).filter(Empresa.tenant_id == atendente.tenant_id).all()]
    func_ids_junction = [
        int(r[0])
        for r in db.query(FuncionarioRedeEmpresa.funcionario_id)
        .join(Empresa, Empresa.id == FuncionarioRedeEmpresa.empresa_id)
        .filter(Empresa.tenant_id == atendente.tenant_id)
        .distinct()
        .all()
    ]
    filtros = []
    if rede_ids:
        filtros.append(FuncionarioRede.rede_id.in_(rede_ids))
    if empresa_ids:
        filtros.append(FuncionarioRede.empresa_id.in_(empresa_ids))
    if func_ids_junction:
        filtros.append(FuncionarioRede.id.in_(func_ids_junction))
    if not filtros:
        return []
    q = (
        db.query(FuncionarioRede)
        .filter(
            FuncionarioRede.ativo.is_(True),
            or_(*filtros),
            or_(FuncionarioRede.nome.ilike(term), FuncionarioRede.email.ilike(term)),
        )
        .order_by(FuncionarioRede.nome.asc(), FuncionarioRede.id.asc())
        .limit(limit)
    )
    rows = q.all()
    out: list[WhatsappFuncionarioOpcaoRead] = []
    for func in rows:
        if _funcionario_no_tenant(db, atendente, func.id) is None:
            continue
        out.append(
            WhatsappFuncionarioOpcaoRead(
                id=func.id,
                nome=func.nome,
                email=func.email,
                tipo=func.tipo,
                empresas=_empresas_funcionario(db, func),
            )
        )
    return out


@router.get("/funcionarios/catalogo", response_model=WhatsappFuncionarioCatalogoRead)
def catalogo_funcionarios(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    redes = (
        db.query(Rede)
        .filter(Rede.tenant_id == atendente.tenant_id, Rede.ativo.is_(True))
        .order_by(Rede.nome.asc(), Rede.id.asc())
        .all()
    )
    empresas = (
        db.query(Empresa)
        .filter(Empresa.tenant_id == atendente.tenant_id, Empresa.ativo.is_(True))
        .order_by(Empresa.nome.asc(), Empresa.id.asc())
        .all()
    )
    return WhatsappFuncionarioCatalogoRead(
        redes=[WhatsappRedeCatalogoRead(id=r.id, nome=r.nome) for r in redes],
        empresas=[WhatsappEmpresaCatalogoRead(id=e.id, nome=_empresa_nome_exibicao(e) or e.nome, rede_id=int(e.rede_id)) for e in empresas],
    )


@router.get("/{chat_id}", response_model=WhatsappChatRead)
def obter(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(WhatsappChat.id == chat_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este chat")
    return _chat_read(db, c)


@router.get("/{chat_id}/mensagens/{mensagem_id}/midia")
def obter_midia_da_mensagem(
    chat_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Devolve o ficheiro binário guardado para mensagens inbound com mídia."""
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este chat")
    m = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat_id, WhatsappMensagem.id == mensagem_id)
        .first()
    )
    if not m or not m.midia_nome_arquivo:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    path = caminho_absoluto_arquivo(m.midia_nome_arquivo)
    if not path:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado em disco")
    media_type = m.mimetype or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/{chat_id}/mensagens", response_model=list[WhatsappMensagemRead])
def listar_mensagens(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este chat")
    rows = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.chat_id == chat_id)
        .order_by(WhatsappMensagem.created_at.asc())
        .all()
    )
    visiveis = [m for m in rows if not mensagem_oculta_na_conversa(getattr(m, "evento_sistema", None))]
    return [_mensagem_read(m) for m in visiveis]


@router.get("/{chat_id}/demandas", response_model=list[WhatsappChatDemandaRead])
def listar_demandas(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.services.whatsapp_chat_demandas import listar_demandas_chat

    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para este chat")
    return listar_demandas_chat(db, chat_id)


@router.post("/{chat_id}/demandas", response_model=WhatsappChatDemandaRead, status_code=201)
def registrar_demanda(
    chat_id: int,
    data: WhatsappChatDemandaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.services.whatsapp_chat_demandas import criar_demanda_chat, demanda_para_read

    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_registrar_demanda(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para registrar demanda neste chat")
    row = criar_demanda_chat(db, c, atendente, data, desfecho="resolvido_sessao")
    db.commit()
    assert row is not None
    return demanda_para_read(row)


@router.delete("/{chat_id}/demandas/{demanda_id}", status_code=204)
def excluir_demanda(
    chat_id: int,
    demanda_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.models.whatsapp_chat_demanda import WhatsappChatDemanda

    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_registrar_demanda(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para alterar demandas neste chat")
    row = (
        db.query(WhatsappChatDemanda)
        .filter(WhatsappChatDemanda.id == demanda_id, WhatsappChatDemanda.chat_id == chat_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    if atendente.role != "admin" and row.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Somente quem registrou ou admin pode excluir")
    db.delete(row)
    db.commit()


@router.post("/{chat_id}/assumir", response_model=WhatsappChatRead)
def assumir(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado != "aguardando_atendente":
        raise HTTPException(status_code=400, detail="Só é possível assumir chats na fila de espera")
    estado_anterior = c.estado
    c.estado = "em_atendimento"
    c.atendente_id = atendente.id
    c.atendimento_inicio_at = datetime.now(timezone.utc)
    from app.services.audit_operacional import audit_whatsapp_chat

    audit_whatsapp_chat(
        db,
        chat_id=c.id,
        action="assign",
        atendente_id=atendente.id,
        payload={"de_estado": estado_anterior, "protocolo": c.protocolo},
    )
    db.commit()
    db.refresh(c)
    emit_chat_fila_from_model(db, c, estado_anterior=estado_anterior)
    st_auto = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if st_auto and bool(getattr(st_auto, "auto_msg_assumido_ativa", True)) and _evolution_configurada(st_auto):
        raw = (getattr(st_auto, "auto_msg_assumido_texto", "") or "").strip() or DEFAULT_AUTO_MSG_ASSUMIDO
        txt = _render_template(
            raw,
            db=db,
            chat=c,
            atendente=atendente,
            st=st_auto,
            # Conteúdo automático, mas assinatura no WhatsApp como o atendente responsável.
            atendente_nome=(atendente.nome or "").strip() or "BOT",
        )
        if txt:
            try:
                _enviar_texto_whatsapp(db, chat=c, texto=txt, atendente=atendente, evento_sistema="auto_assumido")
            except HTTPException as exc:
                logger.warning("Auto-msg assumido falhou (chat=%s): %s", c.protocolo, exc.detail)
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c is not None
    return _chat_read(db, c)


@router.post("/{chat_id}/encerrar", response_model=WhatsappChatRead)
def encerrar(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado == "encerrado":
        return _chat_read(db, c)
    if c.estado == "aguardando_avaliacao":
        return _chat_read(db, c)
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Encerre apenas chats em atendimento")
    if atendente.role != "admin" and c.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode encerrar este chat")
    st_auto = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    from app.services.whatsapp_avaliacao import finalizar_atendimento_whatsapp

    try:
        from app.services.audit_operacional import audit_whatsapp_chat

        audit_whatsapp_chat(
            db,
            chat_id=c.id,
            action="close",
            atendente_id=atendente.id,
            payload={"protocolo": c.protocolo},
        )
        finalizar_atendimento_whatsapp(db, c, st_auto, evento_encerrado="auto_encerrado")
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Encerramento WhatsApp falhou (chat=%s): %s", c.protocolo, exc)
        raise HTTPException(status_code=502, detail="Falha ao encerrar o atendimento no WhatsApp") from exc
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c is not None
    emit_chat_fila_from_model(db, c, estado_anterior="em_atendimento")
    return _chat_read(db, c)


@router.post("/{chat_id}/mensagens", response_model=WhatsappMensagemRead, status_code=201)
def enviar_mensagem(
    chat_id: int,
    data: WhatsappChatMensagemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Só é possível enviar mensagens em chats ativos")
    _exigir_responsavel_envio_cliente(c, atendente)
    texto = data.texto.strip()
    m = _enviar_texto_whatsapp(
        db,
        chat=c,
        texto=texto,
        atendente=atendente,
        evento_sistema=None,
        quoted_wa_message_id=data.quoted_wa_message_id,
    )
    m = db.query(WhatsappMensagem).options(joinedload(WhatsappMensagem.atendente)).filter(WhatsappMensagem.id == m.id).first()
    assert m is not None
    return _mensagem_read(m)


@router.post("/{chat_id}/mensagens/midia", response_model=WhatsappMensagemRead, status_code=201)
async def enviar_mensagem_midia(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
    file: UploadFile = File(...),
    mediatipo: str = Form(..., description="imagem | video | audio | documento"),
    caption: str = Form(""),
    quoted_wa_message_id: str | None = Form(None),
):
    """Envia mídia para o cliente via Evolution API (base64). Opcionalmente cita uma mensagem anterior."""
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Só é possível enviar mensagens em chats ativos")
    _exigir_responsavel_envio_cliente(c, atendente)

    data = await file.read()
    if len(data) > settings.WHATSAPP_MEDIA_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Ficheiro excede o tamanho máximo permitido.")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")

    mime = (file.content_type or "application/octet-stream").split(";")[0].strip()
    tipo_db = _tipo_midia_db(mediatipo)
    nome_guardado = gravar_bytes_em_disco(data, mime)
    if not nome_guardado:
        raise HTTPException(status_code=500, detail="Não foi possível guardar o ficheiro em disco.")

    cap = (caption or "").strip()
    base_legenda = cap if cap else _rotulo_midia_outbound(tipo_db)
    nome_atend = (atendente.nome or "").strip()
    legenda_whatsapp = f"[ {nome_atend} ]: {base_legenda}" if nome_atend else base_legenda
    corpo_eff = legenda_whatsapp

    b64 = base64.b64encode(data).decode("ascii")
    st = _settings_envio(db)
    ev_mt = _mediatype_evolution(mediatipo)
    fname = _sanitizar_nome_ficheiro(file.filename, f"envio.{tipo_db}")

    quoted_payload = None
    q_wa: str | None = None
    q_prev: str | None = None
    if quoted_wa_message_id and str(quoted_wa_message_id).strip():
        q_wa = str(quoted_wa_message_id).strip()
        quoted_payload = _quoted_evolution_payload(db, c, q_wa)
        ref = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.chat_id == chat_id, WhatsappMensagem.wa_message_id == q_wa)
            .first()
        )
        q_prev = _preview_citacao(ref) if ref else None

    ok, err, sent_wa_id = evolution_api.evolution_send_media(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        c.wa_id,
        mediatype=ev_mt,
        mimetype=mime,
        caption=legenda_whatsapp,
        media_base64=b64,
        file_name=fname,
        quoted=quoted_payload,
    )
    if not ok:
        raise HTTPException(status_code=502, detail=err or "Falha ao enviar mídia pela Evolution API")

    m = WhatsappMensagem(
        chat_id=c.id,
        direcao="outbound",
        corpo=corpo_eff,
        tipo_midia=tipo_db,
        mimetype=mime,
        midia_nome_arquivo=nome_guardado,
        wa_message_id=sent_wa_id,
        quoted_wa_message_id=q_wa,
        quoted_corpo_preview=q_prev,
        atendente_id=atendente.id,
        evento_sistema=None,
    )
    db.add(m)
    db.commit()
    m2 = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.id == m.id)
        .first()
    )
    assert m2 is not None
    emit_chat_mensagem_from_models(db, c, m2, exclude_atendente_id=atendente.id)
    return _mensagem_read(m2)


@router.post("/{chat_id}/comentarios-internos", response_model=WhatsappMensagemRead, status_code=201)
def comentar_interno(
    chat_id: int,
    data: WhatsappChatComentarioInternoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado in ("encerrado", "aguardando_avaliacao"):
        raise HTTPException(status_code=400, detail="Chat encerrado (somente leitura)")
    texto = data.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Comentário vazio")
    nome = (atendente.nome or "").strip() or "Equipe"
    corpo = f"[ INTERNO / {nome} ]: {texto}"
    m = WhatsappMensagem(
        chat_id=c.id,
        direcao="outbound",
        corpo=corpo,
        tipo_midia="texto",
        mimetype=None,
        midia_nome_arquivo=None,
        wa_message_id=None,
        atendente_id=atendente.id,
        evento_sistema="comentario_interno",
    )
    db.add(m)
    db.commit()
    m2 = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.id == m.id)
        .first()
    )
    assert m2 is not None
    emit_chat_mensagem_from_models(db, c, m2, exclude_atendente_id=atendente.id)
    return _mensagem_read(m2)


@router.post("/{chat_id}/visto", status_code=204)
def marcar_chat_visto(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")

    now = datetime.now(timezone.utc)
    row = (
        db.query(WhatsappChatReadModel)
        .filter(WhatsappChatReadModel.chat_id == chat_id, WhatsappChatReadModel.atendente_id == atendente.id)
        .first()
    )
    if row:
        row.last_seen_at = now
    else:
        db.add(WhatsappChatReadModel(chat_id=chat_id, atendente_id=atendente.id, last_seen_at=now))
    db.commit()
    from app.services.realtime_emit import emit_notificacao_contagem

    emit_notificacao_contagem(db, [atendente.id])
    return None


@router.post("/{chat_id}/vincular-ticket", response_model=WhatsappChatRead)
def vincular_ticket(
    chat_id: int,
    data: WhatsappVincularTicketBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    ticket = db.query(Ticket).filter(Ticket.id == data.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=403, detail="Sem permissão para este ticket")
    exist = (
        db.query(WhatsappChatTicket)
        .filter(WhatsappChatTicket.chat_id == chat_id, WhatsappChatTicket.ticket_id == data.ticket_id)
        .first()
    )
    if not exist:
        db.add(WhatsappChatTicket(chat_id=chat_id, ticket_id=data.ticket_id, atendente_id=atendente.id))
        db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/vincular-funcionario", response_model=WhatsappChatRead)
def vincular_funcionario(
    chat_id: int,
    data: WhatsappVincularFuncionarioBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para este chat")
    func = _funcionario_no_tenant(db, atendente, data.funcionario_rede_id)
    if not func:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    emp = _resolver_empresa_vinculo(db, atendente, func, data.empresa_id)
    c.funcionario_rede_id = func.id
    c.empresa_id = emp.id
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/desvincular-funcionario", response_model=WhatsappChatRead)
def desvincular_funcionario(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para este chat")
    c.funcionario_rede_id = None
    c.empresa_id = None
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/cadastrar-funcionario", response_model=WhatsappChatRead)
def cadastrar_funcionario(
    chat_id: int,
    data: WhatsappCadastrarFuncionarioBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para este chat")
    tipo = (data.tipo or "colaborador").strip().lower()
    if tipo not in ("colaborador", "supervisor"):
        raise HTTPException(status_code=400, detail="No chat, cadastre como colaborador ou supervisor")
    escopo = (data.escopo_empresas or "selected").strip().lower()
    empresa_ids = list(dict.fromkeys(data.empresa_ids or []))
    if data.empresa_id and int(data.empresa_id) not in empresa_ids:
        empresa_ids.insert(0, int(data.empresa_id))
    func = _criar_funcionario_rede(
        db,
        atendente,
        nome=data.nome,
        email=data.email,
        tipo=tipo,
        escopo_empresas=escopo,
        rede_id=data.rede_id,
        empresa_id=data.empresa_id,
        empresa_ids=empresa_ids,
    )
    emp = _resolver_empresa_vinculo(db, atendente, func, data.empresa_id)
    c.funcionario_rede_id = func.id
    c.empresa_id = emp.id
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/abrir-ticket", response_model=WhatsappChatRead)
def abrir_ticket(
    chat_id: int,
    data: WhatsappAbrirTicketBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        if data.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if not db.query(Empresa).filter(Empresa.id == data.empresa_id, Empresa.tenant_id == atendente.tenant_id).first():
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not db.query(Setor).filter(Setor.id == data.setor_id, Setor.tenant_id == atendente.tenant_id).first():
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    status_inicial = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    if not status_inicial:
        raise HTTPException(status_code=400, detail="Cadastre ao menos um status de ticket")
    protocolo = _gerar_protocolo(db)
    desc = (data.descricao or "").strip()
    linha_chat = f"Vinculado ao chat WhatsApp {c.protocolo} (contato {c.wa_id})."
    descricao_final = f"{linha_chat}\n\n{desc}" if desc else linha_chat
    ticket = Ticket(
        tenant_id=atendente.tenant_id,
        protocolo=protocolo,
        empresa_id=data.empresa_id,
        setor_id=data.setor_id,
        status_id=status_inicial.id,
        assunto=data.assunto.strip(),
        descricao=descricao_final,
        aberto_por_id=None,
    )
    db.add(ticket)
    db.flush()
    from app.services.sla_policy import aplicar_sla_snapshot_ao_ticket

    aplicar_sla_snapshot_ao_ticket(db, ticket)
    corpo_abertura = desc or linha_chat
    db.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=atendente.id,
            tipo="abertura",
            corpo=corpo_abertura,
        )
    )
    db.flush()
    from app.services.sla_calculo import registrar_primeira_resposta_se_necessario

    registrar_primeira_resposta_se_necessario(db, ticket)
    db.add(WhatsappChatTicket(chat_id=chat_id, ticket_id=ticket.id, atendente_id=atendente.id))
    if data.natureza_id is not None:
        from app.services.whatsapp_chat_demandas import criar_demanda_chat

        criar_demanda_chat(
            db,
            c,
            atendente,
            WhatsappChatDemandaCreate(
                natureza_id=data.natureza_id,
                motivo_id=data.motivo_id,
                descricao_curta=data.assunto.strip()[:500],
            ),
            desfecho="escalado_ticket",
            ticket_id=ticket.id,
        )
    db.commit()
    db.refresh(ticket)
    pos_criar_ticket_na_fila(db, ticket)
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/transferir", response_model=WhatsappChatRead)
def transferir(
    chat_id: int,
    data: WhatsappTransferirChatBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(WhatsappChat.id == chat_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if c.estado in ("encerrado", "aguardando_avaliacao"):
        raise HTTPException(status_code=400, detail="Chat encerrado não pode ser transferido")
    # Permissão: admin ou atendente responsável atual
    if atendente.role != "admin" and c.atendente_id not in (None, atendente.id):
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode transferir este chat")

    setor = db.query(Setor).filter(Setor.id == data.setor_id, Setor.ativo.is_(True)).first()
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado ou inativo")

    # Atendente pode transferir para qualquer setor.
    # Porém, só pode escolher um responsável (atendente_id) se tiver acesso ao setor destino (ou for admin).
    vis_destino_ok = True
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        vis_destino_ok = data.setor_id in vis

    destino: Atendente | None = None
    if data.atendente_id is not None:
        if not vis_destino_ok:
            raise HTTPException(
                status_code=403,
                detail="Sem permissão para atribuir responsável no setor destino. Transfira sem atendente para cair na fila do setor.",
            )
        destino = db.query(Atendente).filter(Atendente.id == data.atendente_id, Atendente.ativo.is_(True)).first()
        if not destino:
            raise HTTPException(status_code=404, detail="Atendente não encontrado ou inativo")
        # destino deve pertencer ao setor escolhido (a menos que seja admin)
        if destino.role != "admin":
            setor_ids = {s.id for s in destino.setores}
            if data.setor_id not in setor_ids:
                raise HTTPException(status_code=400, detail="Atendente selecionado não pertence ao setor escolhido")

    estado_anterior = c.estado
    de_setor_id = c.setor_id
    de_atendente_id = c.atendente_id
    c.setor_id = data.setor_id
    c.atendente_id = destino.id if destino else None
    if destino:
        c.estado = "em_atendimento"
        c.atendimento_inicio_at = c.atendimento_inicio_at or datetime.now(timezone.utc)
    else:
        c.estado = "aguardando_atendente"
        c.atendimento_inicio_at = None

    nome_origem = (atendente.nome or "").strip() or "Equipe"
    if destino:
        texto_transfer = (
            f"Chat transferido por {nome_origem} para {destino.nome} (setor {setor.nome})."
        )
    else:
        texto_transfer = f"Chat transferido por {nome_origem} para a fila do setor {setor.nome}."
    db.add(
        WhatsappMensagem(
            chat_id=c.id,
            direcao="outbound",
            corpo=f"[ TRANSFERÊNCIA / {nome_origem} ]: {texto_transfer}",
            tipo_midia="texto",
            mimetype=None,
            midia_nome_arquivo=None,
            wa_message_id=None,
            atendente_id=atendente.id,
            evento_sistema="transferencia",
        )
    )
    from app.services.audit_operacional import audit_whatsapp_chat

    audit_whatsapp_chat(
        db,
        chat_id=c.id,
        action="transfer",
        atendente_id=atendente.id,
        payload={
            "protocolo": c.protocolo,
            "de_setor_id": de_setor_id,
            "para_setor_id": data.setor_id,
            "de_atendente_id": de_atendente_id,
            "para_atendente_id": destino.id if destino else None,
        },
    )
    db.commit()
    db.refresh(c)
    c2 = (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(WhatsappChat.id == chat_id)
        .first()
    )
    assert c2 is not None
    transfer_msg = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(
            WhatsappMensagem.chat_id == chat_id,
            WhatsappMensagem.evento_sistema == "transferencia",
        )
        .order_by(WhatsappMensagem.id.desc())
        .first()
    )
    emit_chat_fila_from_model(db, c2, estado_anterior=estado_anterior)
    if transfer_msg:
        emit_chat_mensagem_from_models(db, c2, transfer_msg, exclude_atendente_id=atendente.id)
    return _chat_read(db, c2)
