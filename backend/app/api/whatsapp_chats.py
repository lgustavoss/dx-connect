import base64
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_

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
    WhatsappChatDemandaUpdate,
    WhatsappChatMensagemCreate,
    WhatsappChatRead,
    WhatsappContatoRead,
    WhatsappEmpresaContextoBody,
    WhatsappIniciarChatBody,
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
from app.services.mensagem_status import status_inicial_outbound_whatsapp
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
from app.services.protocolo_mensal import gerar_protocolo_chat
from app.services.whatsapp_wa_id_lock import lock_wa_id_para_chat, unlock_wa_id_para_chat
from app.services.audit_operacional import audit_whatsapp_chat

router = APIRouter(prefix="/whatsapp/chats", tags=["whatsapp-chats"])

logger = logging.getLogger(__name__)

_MAX_PAGE = 100
_DEFAULT_PAGE = 20

_ESTADOS_HISTORICO_FINALIZADOS = ("encerrado", "aguardando_avaliacao")
_ESTADOS_HISTORICO_ATIVOS = ("em_atendimento", "aguardando_atendente")


def _estados_historico_filtro(estado: str | None) -> list[str]:
    s = (estado or "finalizados").strip().lower()
    if s in ("finalizados", "default"):
        return list(_ESTADOS_HISTORICO_FINALIZADOS)
    if s == "encerrado":
        return ["encerrado"]
    if s == "aguardando_avaliacao":
        return ["aguardando_avaliacao"]
    if s == "em_atendimento":
        return ["em_atendimento"]
    if s == "aguardando_atendente":
        return ["aguardando_atendente"]
    if s == "todos":
        return list(_ESTADOS_HISTORICO_FINALIZADOS + _ESTADOS_HISTORICO_ATIVOS)
    raise HTTPException(status_code=400, detail="Parâmetro estado inválido para histórico.")

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
    if s in ("figurinha", "sticker"):
        return "figurinha"
    return "documento"


def _rotulo_midia_outbound(tipo_db: str) -> str:
    """Rótulo interno legado — não enviar ao WhatsApp nem gravar como corpo sem caption."""
    return {
        "imagem": "[Imagem enviada]",
        "video": "[Vídeo enviado]",
        "audio": "[Áudio enviado]",
        "documento": "[Documento enviado]",
        "figurinha": "[Figurinha enviada]",
    }.get(tipo_db, "[Ficheiro enviado]")


def _prefixo_assinatura_whatsapp(
    db: Session,
    chat: WhatsappChat,
    atendente: Atendente | None,
) -> str:
    """Prefixo visível no WhatsApp do cliente: «[ Setor - Nome ]:» (#628)."""
    nome = (atendente.nome if atendente else "").strip()
    if not nome:
        return ""
    setor_nome: str | None = None
    if chat.setor_id:
        rel = getattr(chat, "setor", None)
        if rel and (rel.nome or "").strip():
            setor_nome = rel.nome.strip()
        else:
            s = db.query(Setor).filter(Setor.id == chat.setor_id).first()
            if s and (s.nome or "").strip():
                setor_nome = s.nome.strip()
    if setor_nome:
        return f"[ {setor_nome} - {nome} ]:"
    return f"[ Atendimento - {nome} ]:"


def _corpo_e_caption_midia_outbound(
    tipo_db: str,
    caption: str | None,
    *,
    prefixo: str | None = None,
) -> tuple[str, str]:
    """
    Retorna (corpo_db, caption_evolution).
    Sem legenda do utilizador: corpo vazio e caption vazia (só a mídia no WhatsApp).
    """
    if tipo_db == "figurinha":
        return "", ""
    cap = (caption or "").strip()
    if not cap:
        return "", ""
    pref = (prefixo or "").strip()
    texto = f"{pref}\n{cap}" if pref else cap
    return texto, texto


def _aplicar_setor_ao_assumir(
    db: Session,
    chat: WhatsappChat,
    atendente: Atendente,
    setor_id: int | None,
) -> None:
    """Opção 1 (#628): 1 setor → auto; vários → obrigatório; admin sem setores pode omitir."""
    if chat.setor_id is not None:
        return
    setores_atendente = list(getattr(atendente, "setores", None) or [])
    if setor_id is not None:
        if atendente.role != "admin":
            ids = {s.id for s in setores_atendente}
            if setor_id not in ids:
                raise HTTPException(status_code=403, detail="Sem permissão para este setor")
        else:
            s = db.query(Setor).filter(Setor.id == setor_id, Setor.ativo.is_(True)).first()
            if not s:
                raise HTTPException(status_code=400, detail="Setor inválido ou inativo")
        chat.setor_id = setor_id
        return
    if len(setores_atendente) == 1:
        chat.setor_id = setores_atendente[0].id
        return
    if len(setores_atendente) > 1:
        raise HTTPException(
            status_code=400,
            detail="Selecione o setor deste atendimento (atendente com vários setores).",
        )


FOTO_PERFIL_TTL_SEC = 7 * 24 * 3600


def _maybe_refresh_foto_perfil(db: Session, chat: WhatsappChat, *, force: bool = False) -> bool:
    """Atualiza cache da foto via Evolution. Retorna True se gravou alteração."""
    now = datetime.now(timezone.utc)
    if not force:
        url = getattr(chat, "foto_perfil_url", None)
        atualizada = getattr(chat, "foto_perfil_atualizada_em", None)
        if url and atualizada is not None:
            ts = atualizada if atualizada.tzinfo else atualizada.replace(tzinfo=timezone.utc)
            if (now - ts).total_seconds() < FOTO_PERFIL_TTL_SEC:
                return False
    st = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if not st or not _evolution_configurada(st):
        return False
    ok, profile_url, err = evolution_api.evolution_fetch_profile_picture_url(
        st.evolution_base_url or "",
        st.evolution_instance_name or "",
        st.evolution_api_key or "",
        chat.wa_id,
    )
    if not ok:
        logger.info("Foto perfil Evolution falhou (chat=%s): %s", chat.protocolo, err)
        chat.foto_perfil_atualizada_em = now
        return True
    chat.foto_perfil_url = profile_url
    chat.foto_perfil_atualizada_em = now
    return True


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


def _sair_pausa_inatividade_por_atividade(chat: WhatsappChat) -> None:
    """Mensagem do cliente ou outbound humana reinicia o ciclo — sai da pausa manual."""
    if getattr(chat, "inatividade_pausada", False):
        chat.inatividade_pausada = False
        chat.inatividade_retomada_em = None


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
    # Prefixo no WhatsApp do cliente: "[ Setor - Nome ]:\nmensagem" (#628).
    # A saudação ao assumir usa o mesmo prefixo do atendente (não BOT).
    if atendente is not None and evento_sistema in (None, "auto_assumido"):
        prefixo = _prefixo_assinatura_whatsapp(db, chat, atendente)
        if prefixo and not texto_eff.startswith("["):
            texto_eff = f"{prefixo}\n{texto_eff}"
    elif evento_sistema is not None:
        if not texto_eff.startswith("["):
            texto_eff = f"[ BOT ]:\n{texto_eff}"
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
    if evento_sistema is None:
        _sair_pausa_inatividade_por_atividade(chat)
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
        status_entrega=status_inicial_outbound_whatsapp(wa_message_id=sent_wa_id) if evento_sistema is None else None,
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


def _resolver_empresa_contexto_opcional(
    db: Session,
    atendente: Atendente,
    func: FuncionarioRede,
    empresa_id: int | None,
) -> int | None:
    """Resolve empresa de contexto sem bloquear multi-empresa (#592).

    - 1 empresa → usa automaticamente
    - >1 e sem empresa_id → None (atendente pergunta ao cliente e vincula depois)
    - empresa_id informado → valida pertencer ao funcionário
    """
    emp_ids = empresa_ids_vinculados(db, func, apenas_ativas=True)
    if not emp_ids:
        return None
    if len(emp_ids) == 1:
        return next(iter(emp_ids))
    if empresa_id is None:
        return None
    if int(empresa_id) not in emp_ids:
        raise HTTPException(status_code=400, detail="Empresa inválida para este funcionário")
    emp = db.query(Empresa).filter(Empresa.id == int(empresa_id), Empresa.tenant_id == atendente.tenant_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return int(empresa_id)


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


def _aplicar_empresa_contexto_chat(
    db: Session,
    atendente: Atendente,
    chat: WhatsappChat,
    empresa_id: int | None,
    *,
    apenas_se_vazio: bool = True,
) -> None:
    """Define/atualiza chat.empresa_id a partir do funcionário vinculado (#592)."""
    if apenas_se_vazio and getattr(chat, "empresa_id", None):
        return
    func = getattr(chat, "funcionario_rede", None)
    if func is None and getattr(chat, "funcionario_rede_id", None):
        func = db.query(FuncionarioRede).filter(FuncionarioRede.id == chat.funcionario_rede_id).first()
    if not func:
        return
    resolvido = _resolver_empresa_contexto_opcional(db, atendente, func, empresa_id)
    if resolvido is not None:
        chat.empresa_id = resolvido


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
        empresas_opcoes=_empresas_funcionario(db, func) if func else [],
        inatividade_pausada=bool(getattr(c, "inatividade_pausada", False)),
        inatividade_retomada_em=getattr(c, "inatividade_retomada_em", None),
        classificacao_demanda_pendente=bool(getattr(c, "classificacao_demanda_pendente", False)),
        foto_perfil_url=getattr(c, "foto_perfil_url", None),
        foto_perfil_atualizada_em=getattr(c, "foto_perfil_atualizada_em", None),
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
    """Responsável/admin: em atendimento, ou após encerramento automático por inatividade."""
    if not _pode_ver_chat(db, atendente, c):
        return False
    if atendente.role != "admin" and c.atendente_id != atendente.id:
        return False
    if c.estado == "em_atendimento":
        return True
    if c.estado in ("aguardando_avaliacao", "encerrado") and _chat_encerrado_por_inatividade(db, c):
        return True
    return False


def _chat_encerrado_por_inatividade(db: Session, c: WhatsappChat) -> bool:
    return (
        db.query(WhatsappMensagem.id)
        .filter(
            WhatsappMensagem.chat_id == c.id,
            WhatsappMensagem.evento_sistema.in_(
                ("auto_encerrado_inatividade", "auto_inativ_aviso"),
            ),
        )
        .limit(1)
        .first()
        is not None
    )


def _pode_ver_chat(db: Session, atendente: Atendente, c: WhatsappChat) -> bool:
    if atendente.role == "admin":
        return True
    if c.atendente_id == atendente.id:
        return True
    vis = ids_setores_visiveis_atendente(db, atendente)
    if c.setor_id is None:
        return c.estado == "aguardando_atendente"
    if c.estado in ("aguardando_atendente", "encerrado", "aguardando_avaliacao", "em_atendimento"):
        return c.setor_id in vis
    return False


def _mensagem_read(m: WhatsappMensagem) -> WhatsappMensagemRead:
    midia_ok = bool(m.midia_nome_arquivo and str(m.midia_nome_arquivo).strip())
    status = m.status_entrega if m.direcao == "outbound" and not m.evento_sistema else None
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
        status_entrega=status,
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
    """Chats em atendimento + encerrados por inatividade ainda sem classificação de demanda."""
    from sqlalchemy import or_

    q = (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(
            or_(
                WhatsappChat.estado == "em_atendimento",
                WhatsappChat.classificacao_demanda_pendente.is_(True),
            )
        )
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
    empresa_id: int | None = Query(None, ge=1, description="Filtrar chats desta empresa (#591)"),
    encerramento_inicio: datetime | None = Query(None, description="Filtro por data de encerramento a partir de"),
    encerramento_fim: datetime | None = Query(None, description="Filtro por data de encerramento até"),
    estado: str | None = Query(
        None,
        description="finalizados (padrão) | encerrado | aguardando_avaliacao | em_atendimento | aguardando_atendente | todos",
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    estados = _estados_historico_filtro(estado)
    q = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.estado.in_(estados))
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
    if empresa_id is not None:
        emp = (
            db.query(Empresa.id)
            .filter(Empresa.id == empresa_id, Empresa.tenant_id == atendente.tenant_id)
            .first()
        )
        if not emp:
            return ListaPaginada(items=[], total=0)
        q = q.filter(WhatsappChat.empresa_id == empresa_id)
    ref_data = func.coalesce(
        WhatsappChat.encerramento_at,
        WhatsappChat.atendimento_inicio_at,
        WhatsappChat.created_at,
    )
    if encerramento_inicio:
        q = q.filter(ref_data >= encerramento_inicio)
    if encerramento_fim:
        q = q.filter(ref_data <= encerramento_fim)
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(or_(WhatsappChat.atendente_id == atendente.id, WhatsappChat.setor_id.in_(vis)))
    total = q.count()
    rows = q.order_by(desc(ref_data), desc(WhatsappChat.id)).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_chat_read(db, c, revelar_avaliacao=True) for c in rows], total=total)


@router.get("/avaliacoes", response_model=ListaPaginada[WhatsappAvaliacaoRead])
def listar_avaliacoes(
    busca: str | None = Query(None, description="Busca por protocolo, telefone ou contato"),
    atendente_id: int | None = Query(None, ge=1),
    nota_min: int | None = Query(None, ge=1, le=5),
    nota_max: int | None = Query(None, ge=1, le=5),
    encerramento_inicio: datetime | None = Query(None),
    encerramento_fim: datetime | None = Query(None),
    incluir_sem_resposta: bool = Query(
        False,
        description="Incluir chats com avaliação solicitada mas sem nota (auditoria)",
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    q = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS)
    if incluir_sem_resposta:
        q = q.filter(WhatsappChat.avaliacao_solicitada.is_(True))
    else:
        q = q.filter(WhatsappChat.avaliacao_nota.isnot(None))
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
    filtros = _filtros_funcionario_tenant(db, atendente)
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
    redes_cache: dict[int, str] = {
        int(r.id): r.nome
        for r in db.query(Rede).filter(Rede.tenant_id == atendente.tenant_id).all()
    }
    out: list[WhatsappFuncionarioOpcaoRead] = []
    for func in rows:
        if _funcionario_no_tenant(db, atendente, func.id) is None:
            continue
        rid = rede_id_efetiva(db, func)
        out.append(
            WhatsappFuncionarioOpcaoRead(
                id=func.id,
                nome=func.nome,
                email=func.email,
                telefone=getattr(func, "telefone", None),
                tipo=func.tipo,
                empresas=_empresas_funcionario(db, func),
                rede_id=rid,
                rede_nome=redes_cache.get(int(rid)) if rid is not None else None,
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


def _filtros_funcionario_tenant(db: Session, atendente: Atendente) -> list:
    """Filtros OR para funcionários ativos no tenant do atendente."""
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
    return filtros


@router.get("/funcionarios/similares", response_model=list[WhatsappFuncionarioOpcaoRead])
def buscar_funcionarios_similares(
    nome: str = Query(..., min_length=3, description="Nome digitado no cadastro"),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Sugestões por similaridade de nome (#593) — usado na aba Cadastrar do modal."""
    from app.services.funcionario_nome_similar import (
        LIMIAR_ALTA,
        LIMIAR_SIMILARIDADE,
        normalizar_nome,
        ranquear_similares,
        tokens_significativos,
    )

    nome_q = nome.strip()
    nome_norm = normalizar_nome(nome_q)
    if len(nome_norm) < 3:
        return []

    filtros = _filtros_funcionario_tenant(db, atendente)
    if not filtros:
        return []

    tokens = tokens_significativos(nome_norm)[:2]
    token_filters = [FuncionarioRede.nome.ilike(f"%{t}%") for t in tokens] if tokens else []
    q = db.query(FuncionarioRede).filter(FuncionarioRede.ativo.is_(True), or_(*filtros))
    if token_filters:
        q = q.filter(or_(*token_filters))
    candidatos_rows = q.order_by(FuncionarioRede.nome.asc(), FuncionarioRede.id.asc()).limit(300).all()

    candidatos: list[tuple[int, str]] = []
    for func in candidatos_rows:
        if _funcionario_no_tenant(db, atendente, func.id) is None:
            continue
        candidatos.append((int(func.id), func.nome or ""))

    ranked = ranquear_similares(nome_q, candidatos, limiar=LIMIAR_SIMILARIDADE, limit=limit)
    if not ranked:
        return []

    by_id = {int(f.id): f for f in candidatos_rows}
    redes_cache: dict[int, str] = {
        int(r.id): r.nome
        for r in db.query(Rede).filter(Rede.tenant_id == atendente.tenant_id).all()
    }
    out: list[WhatsappFuncionarioOpcaoRead] = []
    for fid, _nome, score in ranked:
        func = by_id.get(fid)
        if func is None:
            continue
        rid = rede_id_efetiva(db, func)
        out.append(
            WhatsappFuncionarioOpcaoRead(
                id=func.id,
                nome=func.nome,
                email=func.email,
                telefone=getattr(func, "telefone", None),
                tipo=func.tipo,
                empresas=_empresas_funcionario(db, func),
                rede_id=rid,
                rede_nome=redes_cache.get(int(rid)) if rid is not None else None,
                similaridade=round(float(score), 3),
                similaridade_alta=float(score) >= LIMIAR_ALTA,
            )
        )
    return out


def _normalize_wa_id(raw: str | None) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        raise HTTPException(status_code=400, detail="Informe um número WhatsApp válido.")
    # Aceita com ou sem DDI; se 10–11 dígitos BR, prefixa 55
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = "55" + digits
    if len(digits) < 12:
        raise HTTPException(status_code=400, detail="Número WhatsApp incompleto.")
    return digits


def _preencher_telefone_do_chat(func: FuncionarioRede, wa_id: str | None) -> None:
    """Se o cadastro não tem telefone, copia o WhatsApp do chat (aba Contatos / outbound)."""
    digits = re.sub(r"\D", "", wa_id or "")
    if not digits:
        return
    if re.sub(r"\D", "", getattr(func, "telefone", None) or ""):
        return
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = "55" + digits
    func.telefone = digits


def _chat_aberto_por_wa_id(db: Session, wa_id: str) -> WhatsappChat | None:
    return (
        db.query(WhatsappChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(
            WhatsappChat.wa_id == wa_id,
            WhatsappChat.estado.in_(("aguardando_atendente", "em_atendimento")),
        )
        .order_by(WhatsappChat.id.desc())
        .first()
    )


@router.get("/contatos", response_model=ListaPaginada[WhatsappContatoRead])
def listar_contatos(
    busca: str | None = Query(None, description="Nome, e-mail, telefone ou empresa"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
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
        return ListaPaginada(items=[], total=0)

    q = db.query(FuncionarioRede).filter(FuncionarioRede.ativo.is_(True), or_(*filtros))
    term_raw = (busca or "").strip()
    if term_raw:
        term = f"%{term_raw}%"
        digits = re.sub(r"\D", "", term_raw)
        conds = [
            FuncionarioRede.nome.ilike(term),
            FuncionarioRede.email.ilike(term),
        ]
        if digits:
            conds.append(FuncionarioRede.telefone.ilike(f"%{digits}%"))
        # empresas por nome: filtramos após ou via subquery
        emp_ids_match = [
            int(r[0])
            for r in db.query(Empresa.id)
            .filter(
                Empresa.tenant_id == atendente.tenant_id,
                or_(
                    Empresa.nome.ilike(term),
                    Empresa.nome_fantasia.ilike(term),
                    Empresa.razao_social.ilike(term),
                ),
            )
            .all()
        ]
        if emp_ids_match:
            sub_j = db.query(FuncionarioRedeEmpresa.funcionario_id).filter(
                FuncionarioRedeEmpresa.empresa_id.in_(emp_ids_match)
            )
            conds.append(FuncionarioRede.empresa_id.in_(emp_ids_match))
            conds.append(FuncionarioRede.id.in_(sub_j))
        q = q.filter(or_(*conds))

    total = q.count()
    rows = q.order_by(FuncionarioRede.nome.asc(), FuncionarioRede.id.asc()).offset(offset).limit(limit).all()
    redes_cache: dict[int, str] = {
        int(r.id): r.nome
        for r in db.query(Rede).filter(Rede.tenant_id == atendente.tenant_id).all()
    }
    items: list[WhatsappContatoRead] = []
    for func in rows:
        if _funcionario_no_tenant(db, atendente, func.id) is None:
            continue
        rid = rede_id_efetiva(db, func)
        items.append(
            WhatsappContatoRead(
                id=func.id,
                nome=func.nome,
                email=func.email,
                telefone=getattr(func, "telefone", None),
                tipo=func.tipo,
                empresas=_empresas_funcionario(db, func),
                rede_id=rid,
                rede_nome=redes_cache.get(int(rid)) if rid is not None else None,
            )
        )
    return ListaPaginada(items=items, total=total)


@router.post("/iniciar", response_model=WhatsappChatRead)
def iniciar_chat_outbound(
    data: WhatsappIniciarChatBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Atendente inicia contacto WhatsApp (contato cadastrado, número avulso ou retoma)."""
    func: FuncionarioRede | None = None
    if data.funcionario_id is not None:
        func = _funcionario_no_tenant(db, atendente, data.funcionario_id)
        if not func:
            raise HTTPException(status_code=404, detail="Funcionário não encontrado")
        if not func.ativo:
            raise HTTPException(status_code=400, detail="Funcionário inativo")

    telefone_body = data.telefone
    telefone_cadastro = re.sub(r"\D", "", getattr(func, "telefone", None) or "") if func else ""
    telefone_raw = telefone_body or telefone_cadastro or None
    if not telefone_raw:
        raise HTTPException(
            status_code=400,
            detail="Informe o número WhatsApp do contato (cadastro ou neste pedido).",
        )
    wa_id = _normalize_wa_id(telefone_raw)

    if func is not None and not telefone_cadastro:
        func.telefone = wa_id
        db.flush()

    empresa_id: int | None = None
    if func is not None:
        empresa_id = _resolver_empresa_contexto_opcional(db, atendente, func, data.empresa_id)

    lock_wa_id_para_chat(db, wa_id)
    try:
        existente = _chat_aberto_por_wa_id(db, wa_id)
        if existente:
            if existente.estado == "em_atendimento" and existente.atendente_id not in (None, atendente.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Já existe um atendimento aberto deste contacto com outro responsável.",
                )
            estado_anterior = existente.estado
            if existente.estado == "aguardando_atendente" or existente.atendente_id is None:
                existente.estado = "em_atendimento"
                existente.atendente_id = atendente.id
                existente.atendimento_inicio_at = datetime.now(timezone.utc)
                if func is not None and not existente.funcionario_rede_id:
                    existente.funcionario_rede_id = func.id
                if not existente.empresa_id:
                    _aplicar_empresa_contexto_chat(db, atendente, existente, data.empresa_id)
                audit_whatsapp_chat(
                    db,
                    chat_id=existente.id,
                    action="assign",
                    atendente_id=atendente.id,
                    payload={"de_estado": estado_anterior, "protocolo": existente.protocolo, "origem": "iniciar_outbound"},
                )
                db.commit()
                db.refresh(existente)
                emit_chat_fila_from_model(db, existente, estado_anterior=estado_anterior)
            elif not existente.empresa_id and (func is not None or existente.funcionario_rede_id):
                if func is not None and not existente.funcionario_rede_id:
                    existente.funcionario_rede_id = func.id
                _aplicar_empresa_contexto_chat(db, atendente, existente, data.empresa_id)
                db.commit()
                db.refresh(existente)
            msg_init = (data.mensagem_inicial or "").strip()
            if msg_init:
                try:
                    _enviar_texto_whatsapp(db, chat=existente, texto=msg_init, atendente=atendente, evento_sistema=None)
                except HTTPException:
                    raise
            c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == existente.id).first()
            assert c is not None
            return _chat_read(db, c)

        # Garante Evolution configurada se houver mensagem inicial (criar chat sem msg ainda exige settings para uso posterior)
        _settings_envio(db)

        chat = WhatsappChat(
            protocolo=gerar_protocolo_chat(db),
            wa_id=wa_id,
            cliente_nome=(func.nome if func else None),
            estado="em_atendimento",
            atendente_id=atendente.id,
            atendimento_inicio_at=datetime.now(timezone.utc),
            setor_id=None,
            funcionario_rede_id=func.id if func else None,
            empresa_id=empresa_id,
        )
        db.add(chat)
        db.flush()
        audit_whatsapp_chat(
            db,
            chat_id=chat.id,
            action="create",
            atendente_id=atendente.id,
            payload={"protocolo": chat.protocolo, "origem": "iniciar_outbound", "wa_id": wa_id},
        )
        db.commit()
        db.refresh(chat)
        emit_chat_fila_from_model(db, chat, estado_anterior=None)

        msg_init = (data.mensagem_inicial or "").strip()
        if msg_init:
            _enviar_texto_whatsapp(db, chat=chat, texto=msg_init, atendente=atendente, evento_sistema=None)

        c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat.id).first()
        assert c is not None
        return _chat_read(db, c)
    finally:
        unlock_wa_id_para_chat(db, wa_id)


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
    if _maybe_refresh_foto_perfil(db, c, force=False):
        db.commit()
        db.refresh(c)
    return _chat_read(db, c)


@router.post("/{chat_id}/foto-perfil", response_model=WhatsappChatRead)
def atualizar_foto_perfil(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Força refresh da foto de perfil do contacto via Evolution (#630)."""
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
    _maybe_refresh_foto_perfil(db, c, force=True)
    db.commit()
    db.refresh(c)
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
    from app.services.whatsapp_chat_demandas import (
        criar_demanda_chat,
        criar_marco_demanda_mensagem,
        demanda_para_read,
        remover_marco_demanda_mensagem,
    )

    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_registrar_demanda(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para registrar demanda neste chat")
    row = criar_demanda_chat(db, c, atendente, data, desfecho="resolvido_sessao")
    marco = criar_marco_demanda_mensagem(db, chat=c, atendente=atendente, demanda=row)
    if getattr(c, "classificacao_demanda_pendente", False):
        c.classificacao_demanda_pendente = False
    db.commit()
    db.refresh(marco)
    marco = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.id == marco.id)
        .first()
    )
    emit_chat_mensagem_from_models(db, c, marco, exclude_atendente_id=atendente.id)
    if c.estado != "em_atendimento":
        emit_chat_fila_from_model(db, c, estado_anterior=c.estado)
    return demanda_para_read(row)


@router.patch("/{chat_id}/demandas/{demanda_id}", response_model=WhatsappChatDemandaRead)
def atualizar_demanda(
    chat_id: int,
    demanda_id: int,
    data: WhatsappChatDemandaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.models.whatsapp_chat_demanda import WhatsappChatDemanda
    from app.services.whatsapp_chat_demandas import atualizar_demanda_chat, demanda_para_read

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
    if not data.model_dump(exclude_unset=True):
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
    updated = atualizar_demanda_chat(db, c, row, data, atendente=atendente)
    db.commit()
    return demanda_para_read(updated)


@router.delete("/{chat_id}/demandas/{demanda_id}", status_code=204)
def excluir_demanda(
    chat_id: int,
    demanda_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.models.whatsapp_chat_demanda import WhatsappChatDemanda
    from app.services.whatsapp_chat_demandas import remover_marco_demanda_mensagem

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
    remover_marco_demanda_mensagem(db, chat_id=chat_id, demanda_id=demanda_id)
    db.delete(row)
    db.commit()


@router.post("/{chat_id}/assumir", response_model=WhatsappChatRead)
def assumir(
    chat_id: int,
    empresa_id: int | None = Query(
        None,
        ge=1,
        description="Empresa de contexto opcional (pode ser definida depois na conversa).",
    ),
    setor_id: int | None = Query(
        None,
        ge=1,
        description="Setor do atendimento — obrigatório se o atendente tem vários setores e o chat ainda não tem setor (#628).",
    ),
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
    _aplicar_empresa_contexto_chat(db, atendente, c, empresa_id)
    _aplicar_setor_ao_assumir(db, c, atendente, setor_id)
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


@router.post("/{chat_id}/empresa-contexto", response_model=WhatsappChatRead)
def definir_empresa_contexto(
    chat_id: int,
    data: WhatsappEmpresaContextoBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Define ou altera a empresa de contexto a qualquer momento antes do encerramento (#592)."""
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este chat")
    if c.estado in ("encerrado", "aguardando_avaliacao"):
        raise HTTPException(status_code=400, detail="Não é possível alterar a empresa após o encerramento")
    if not c.funcionario_rede_id:
        raise HTTPException(status_code=400, detail="Chat sem funcionário vinculado")
    _aplicar_empresa_contexto_chat(db, atendente, c, data.empresa_id, apenas_se_vazio=False)
    if not c.empresa_id:
        raise HTTPException(status_code=400, detail="Selecione a empresa do funcionário")
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


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
    if getattr(c, "classificacao_demanda_pendente", False):
        raise HTTPException(
            status_code=400,
            detail="Chat aguarda classificação de demanda — não é possível enviar mensagens ao cliente",
        )
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
    mediatipo: str = Form(..., description="imagem | video | audio | documento | figurinha"),
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
    if getattr(c, "classificacao_demanda_pendente", False):
        raise HTTPException(
            status_code=400,
            detail="Chat aguarda classificação de demanda — não é possível enviar mensagens ao cliente",
        )
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
    prefixo = _prefixo_assinatura_whatsapp(db, c, atendente) if cap else None
    corpo_eff, legenda_whatsapp = _corpo_e_caption_midia_outbound(
        tipo_db, cap, prefixo=prefixo
    )
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

    if tipo_db == "audio":
        ok, err, sent_wa_id = evolution_api.evolution_send_whatsapp_audio(
            st.evolution_base_url,
            st.evolution_instance_name,
            st.evolution_api_key,
            c.wa_id,
            audio_base64=b64,
            quoted=quoted_payload,
        )
    elif tipo_db == "figurinha":
        ok, err, sent_wa_id = evolution_api.evolution_send_sticker(
            st.evolution_base_url,
            st.evolution_instance_name,
            st.evolution_api_key,
            c.wa_id,
            sticker_base64=b64,
            quoted=quoted_payload,
        )
    else:
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
    if tipo_db == "audio" and not sent_wa_id:
        raise HTTPException(
            status_code=502,
            detail="Evolution API não confirmou entrega do áudio (wa_message_id ausente).",
        )

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
        status_entrega=status_inicial_outbound_whatsapp(wa_message_id=sent_wa_id),
    )
    db.add(m)
    _sair_pausa_inatividade_por_atividade(c)
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

    # ✓✓ azul no WhatsApp do cliente: só o responsável, em atendimento
    if (
        c.estado == "em_atendimento"
        and c.atendente_id is not None
        and c.atendente_id == atendente.id
    ):
        _marcar_inbound_lido_evolution(db, c)

    db.commit()
    from app.services.realtime_emit import emit_notificacao_contagem

    emit_notificacao_contagem(db, [atendente.id])
    return None


def _marcar_inbound_lido_evolution(db: Session, chat: WhatsappChat) -> None:
    st = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if not st or not st.evolution_base_url or not st.evolution_instance_name or not st.evolution_api_key:
        return
    ids = [
        row[0]
        for row in (
            db.query(WhatsappMensagem.wa_message_id)
            .filter(
                WhatsappMensagem.chat_id == chat.id,
                WhatsappMensagem.direcao == "inbound",
                WhatsappMensagem.wa_message_id.isnot(None),
                WhatsappMensagem.wa_message_id != "",
            )
            .order_by(WhatsappMensagem.id.desc())
            .limit(40)
            .all()
        )
        if row[0]
    ]
    if not ids:
        return
    ok, err = evolution_api.evolution_mark_messages_as_read(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        remote_jid=chat.wa_id,
        message_ids=list(reversed(ids)),
    )
    if not ok:
        logger.warning("markMessageAsRead falhou (chat=%s): %s", chat.id, err)


@router.post("/{chat_id}/inatividade/pausar", response_model=WhatsappChatRead)
def pausar_inatividade(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Só é possível pausar inatividade em chats em atendimento")
    if c.atendente_id != atendente.id and atendente.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas o responsável pode pausar a inatividade")
    c.inatividade_pausada = True
    c.inatividade_retomada_em = None
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/inatividade/retomar", response_model=WhatsappChatRead)
def retomar_inatividade(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if c.atendente_id != atendente.id and atendente.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas o responsável pode retomar a inatividade")
    c.inatividade_pausada = False
    c.inatividade_retomada_em = datetime.now(timezone.utc)
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/classificacao-demanda/concluir", response_model=WhatsappChatRead)
def concluir_classificacao_demanda(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Marca classificação pós-inatividade como concluída (ex.: confirmar sem registar demanda)."""
    c = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not getattr(c, "classificacao_demanda_pendente", False):
        return _chat_read(db, c)
    if atendente.role != "admin" and c.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o responsável pode concluir a classificação")
    if c.estado not in ("encerrado", "aguardando_avaliacao"):
        raise HTTPException(status_code=400, detail="Classificação só se aplica a chats já encerrados por inatividade")
    c.classificacao_demanda_pendente = False
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    emit_chat_fila_from_model(db, c2, estado_anterior=c2.estado)
    return _chat_read(db, c2)


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
    _preencher_telefone_do_chat(func, c.wa_id)
    c.funcionario_rede_id = func.id
    c.empresa_id = emp.id
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    emit_chat_fila_from_model(db, c2, estado_anterior=c.estado)
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
    emit_chat_fila_from_model(db, c2, estado_anterior=c.estado)
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
    _preencher_telefone_do_chat(func, c.wa_id)
    emp = _resolver_empresa_vinculo(db, atendente, func, data.empresa_id)
    c.funcionario_rede_id = func.id
    c.empresa_id = emp.id
    db.commit()
    c2 = db.query(WhatsappChat).options(*_CHAT_LOAD_OPTIONS).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    emit_chat_fila_from_model(db, c2, estado_anterior=c.estado)
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
        from app.services.whatsapp_chat_demandas import criar_demanda_chat, criar_marco_demanda_mensagem

        row_dem = criar_demanda_chat(
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
        marco = criar_marco_demanda_mensagem(db, chat=c, atendente=atendente, demanda=row_dem)
        db.flush()
        marco_loaded = (
            db.query(WhatsappMensagem)
            .options(joinedload(WhatsappMensagem.atendente))
            .filter(WhatsappMensagem.id == marco.id)
            .first()
        )
        if marco_loaded:
            emit_chat_mensagem_from_models(db, c, marco_loaded, exclude_atendente_id=atendente.id)
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
