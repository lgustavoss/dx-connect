from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, asc, desc, nullslast, inspect as sa_inspect

from app.database import get_db
from app.models import Ticket, TicketHistorico, TicketMensagem, Empresa, Setor, StatusTicket, Atendente, Rede
from app.models.email_inbound_received import EmailInboundReceived
from app.models.funcionario_rede import FuncionarioRede
from app.models.ticket_anexo import TicketAnexo
from app.models.ticket_vinculo import TIPO_DUPLICADO_DE, TicketVinculo
from app.schemas.ticket import (
    EmpresaVinculoSugerida,
    TicketChildBrief,
    TicketCreate,
    TicketHistoricoRead,
    TicketMensagemCreate,
    TicketMensagemRead,
    TicketMensagemStartEditRead,
    TicketMensagemUpdate,
    TicketParentBrief,
    TicketRead,
    TicketTriagemInbound,
    TicketUpdate,
    TicketVinculoCreate,
    TicketVinculoOutroBrief,
    TicketVinculoRead,
    TicketFilhosMassaCreate,
    TicketFilhosMassaOpcoesRead,
    TicketFilhosMassaRead,
    TicketFilhoMassaCriado,
    TicketFilhoMassaEmpresaOpcao,
)
from app.schemas.ticket_anexo import TicketAnexoCreateResponse, TicketAnexoRead
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import obter_atendente_atual
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.core.setor_scope import (
    atendente_atende_algum_id_setor,
    ids_setores_visiveis_atendente,
    responsavel_elegivel_para_setor_do_ticket,
)
from app.services import ticket_anexo_storage
from app.services.protocolo_mensal import gerar_protocolo_ticket
from app.services.ticket_vinculos import (
    criar_vinculo as criar_vinculo_ticket,
    fechar_ticket_como_duplicado,
    listar_vinculos,
    outro_ticket_id,
    rotulo_vinculo,
)
from app.services.ticket_filhos_massa import criar_filhos_em_massa, listar_opcoes_filhos_massa
from app.services.ticket_escopo import (
    rede_id_de_empresa,
    rede_id_efetivo_ticket,
    ticket_e_coordenacao_rede,
    validar_escopo_criacao_manual,
)
from app.services.funcionario_rede_resolver import resolver_remetente_por_email
from app.services.ticket_client_email import extrair_email_de_from_address
from app.services.ticket_mensagem_email_outbox import (
    EMAIL_STATUS_ENVIADA,
    agendar_envio_email,
    cancelar_envio,
    forcar_envio_agora,
    iniciar_edicao,
    process_pending_ticket_mensagem_emails,
    salvar_edicao,
    validar_lock,
    validar_pode_agendar_email_cliente,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarTicketsPor(str, Enum):
    protocolo = "protocolo"
    rede = "rede"
    empresa = "empresa"
    setor = "setor"
    assunto = "assunto"
    status = "status"
    responsavel = "responsavel"
    fechado_em = "fechado_em"

class SituacaoTicket(str, Enum):
    abertos = "abertos"
    fechados = "fechados"
    todos = "todos"


def _gerar_protocolo(db: Session) -> str:
    """Próximo protocolo de ticket no formato #TYYYYMM-NNNN (mensal, America/Sao_Paulo)."""
    return gerar_protocolo_ticket(db)


def _attr_relacionamento_carregado(ticket: Ticket, nome: str) -> bool:
    """True se o relacionamento `nome` foi carregado (evita lazy-load na listagem)."""
    return nome not in sa_inspect(ticket).unloaded


def _rede_id_empresa(db: Session, empresa_id: int) -> int | None:
    return db.query(Empresa.rede_id).filter(Empresa.id == empresa_id).scalar()


def _ancestral_contem_ticket_id(db: Session, parent_id: int, proibido_id: int) -> bool:
    """Sobe a partir de `parent_id` pelos pais; se encontrar `proibido_id`, há ciclo."""
    cur: int | None = parent_id
    visto: set[int] = set()
    for _ in range(600):
        if cur is None:
            return False
        if cur == proibido_id:
            return True
        if cur in visto:
            return True
        visto.add(cur)
        cur = db.query(Ticket.parent_ticket_id).filter(Ticket.id == cur).scalar()
    return True


def _assert_parent_valido(
    db: Session,
    atendente: Atendente,
    *,
    filho_empresa_id: int,
    filho_ticket_id: int | None,
    parent_id: int,
) -> None:
    if filho_ticket_id is not None and parent_id == filho_ticket_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Um ticket não pode ser pai de si mesmo.")
    parent = (
        db.query(Ticket)
        .options(joinedload(Ticket.rede), joinedload(Ticket.empresa))
        .filter(Ticket.id == parent_id)
        .first()
    )
    if not parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket pai não encontrado")
    if not _pode_ver_ticket(db, atendente, parent):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para vincular a este ticket pai")
    r_filho = _rede_id_empresa(db, filho_empresa_id)
    r_pai = rede_id_efetivo_ticket(db, parent)
    if r_filho is None or r_pai is None or r_filho != r_pai:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O ticket filho deve ser de uma empresa da mesma rede do ticket pai.",
        )
    if filho_ticket_id is not None and _ancestral_contem_ticket_id(db, parent_id, filho_ticket_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vínculo inválido: esse vínculo formaria um ciclo entre tickets.",
        )


def _opcoes_carregamento_ticket_detalhe():
    return (
        joinedload(Ticket.empresa).joinedload(Empresa.rede),
        joinedload(Ticket.rede),
        joinedload(Ticket.setor),
        joinedload(Ticket.status),
        joinedload(Ticket.atendente),
        joinedload(Ticket.parent).joinedload(Ticket.status),
        joinedload(Ticket.children).joinedload(Ticket.status),
        joinedload(Ticket.children).joinedload(Ticket.atendente),
    )


def _triagem_inbound_para_ticket(db: Session, t: Ticket) -> TicketTriagemInbound | None:
    row = (
        db.query(EmailInboundReceived)
        .filter(EmailInboundReceived.ticket_id == t.id)
        .order_by(EmailInboundReceived.id.desc())
        .first()
    )
    if not row:
        return None
    email = extrair_email_de_from_address(row.from_address)
    if not email and t.aberto_por_id:
        f = db.query(FuncionarioRede).filter(FuncionarioRede.id == t.aberto_por_id).first()
        email = (f.email or "").strip().lower() if f else None
    rem = resolver_remetente_por_email(db, email)
    if t.empresa_id is not None and not rem.requer_cadastro and len(rem.empresa_ids_opcao) <= 1:
        return None
    empresas: list[EmpresaVinculoSugerida] = []
    for eid in rem.empresa_ids_opcao:
        emp = db.query(Empresa).filter(Empresa.id == eid).first()
        if emp:
            empresas.append(EmpresaVinculoSugerida(id=emp.id, nome=emp.nome))
    if not rem.requer_cadastro and not empresas and t.empresa_id is not None:
        return None
    return TicketTriagemInbound(
        requer_cadastro_funcionario=rem.requer_cadastro,
        remetente_email=rem.email or email,
        conflito_multiplas_redes=rem.conflito_multiplas_redes,
        empresas_vinculo_sugeridas=empresas,
    )


def _ticket_vinculo_brief(t: Ticket) -> TicketVinculoOutroBrief:
    return TicketVinculoOutroBrief(
        id=t.id,
        protocolo=t.protocolo,
        assunto=t.assunto,
        status_nome=t.status.nome if t.status else None,
    )


def _vinculo_para_read(
    v: TicketVinculo,
    perspectiva_ticket_id: int,
    db: Session,
    *,
    duplicado_fechado: bool = False,
) -> TicketVinculoRead:
    other_id = outro_ticket_id(v, perspectiva_ticket_id)
    other = v.related_ticket if v.related_ticket_id == other_id else v.ticket
    if other is None or other.id != other_id:
        other = (
            db.query(Ticket)
            .options(joinedload(Ticket.status))
            .filter(Ticket.id == other_id)
            .first()
        )
    if other is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ticket vinculado em falta")
    return TicketVinculoRead(
        id=v.id,
        tipo=v.tipo,
        rotulo=rotulo_vinculo(v, perspectiva_ticket_id),
        outro_ticket=_ticket_vinculo_brief(other),
        duplicado_fechado=duplicado_fechado,
    )


def _vinculos_para_read(db: Session, t: Ticket) -> list[TicketVinculoRead]:
    return [_vinculo_para_read(v, t.id, db) for v in listar_vinculos(db, t.id)]


def _ticket_para_read(t: Ticket, db: Session | None = None) -> TicketRead:
    parent_brief = None
    if t.parent_ticket_id and _attr_relacionamento_carregado(t, "parent") and t.parent is not None:
        p = t.parent
        parent_brief = TicketParentBrief(
            id=p.id,
            protocolo=p.protocolo,
            assunto=p.assunto,
            status_nome=p.status.nome if p.status else None,
            fechado_em=p.fechado_em,
        )
    children_out: list[TicketChildBrief] = []
    if _attr_relacionamento_carregado(t, "children") and t.children is not None:
        for c in sorted(t.children, key=lambda x: x.id):
            children_out.append(
                TicketChildBrief(
                    id=c.id,
                    protocolo=c.protocolo,
                    assunto=c.assunto,
                    status_nome=c.status.nome if c.status else None,
                    atendente_nome=c.atendente.nome if c.atendente else None,
                    fechado_em=c.fechado_em,
                )
            )
    triagem = _triagem_inbound_para_ticket(db, t) if db is not None else None
    rede_id_out = t.rede_id
    rede_nome_out = t.rede.nome if t.rede is not None else None
    if rede_id_out is None and t.empresa is not None:
        rede_id_out = t.empresa.rede_id
        rede_nome_out = t.empresa.rede.nome if t.empresa.rede else rede_nome_out
    if db and triagem and triagem.requer_cadastro_funcionario is False and rede_id_out is None and t.aberto_por_id:
        f = db.query(FuncionarioRede).filter(FuncionarioRede.id == t.aberto_por_id).first()
        if f and f.rede_id:
            rede_id_out = f.rede_id
            r = db.query(Rede).filter(Rede.id == f.rede_id).first()
            rede_nome_out = r.nome if r else rede_nome_out
    return TicketRead(
        id=t.id,
        protocolo=t.protocolo,
        empresa_id=t.empresa_id,
        setor_id=t.setor_id,
        status_id=t.status_id,
        atendente_id=t.atendente_id,
        aberto_por_id=t.aberto_por_id,
        assunto=t.assunto,
        descricao=t.descricao,
        fechado_em=t.fechado_em,
        created_at=t.created_at,
        updated_at=t.updated_at,
        rede_id=rede_id_out,
        empresa_nome=t.empresa.nome if t.empresa else None,
        rede_nome=rede_nome_out,
        coordenacao_rede=ticket_e_coordenacao_rede(t),
        setor_nome=t.setor.nome if t.setor else None,
        status_nome=t.status.nome if t.status else None,
        atendente_nome=t.atendente.nome if t.atendente else None,
        parent_ticket_id=t.parent_ticket_id,
        parent=parent_brief,
        children=children_out,
        vinculos=_vinculos_para_read(db, t) if db is not None else [],
        triagem_inbound=triagem,
    )


def _pode_ver_ticket(db: Session, atendente: Atendente, ticket: Ticket) -> bool:
    if ticket.tenant_id != atendente.tenant_id:
        return False
    if atendente.role == "admin":
        return True
    vis = ids_setores_visiveis_atendente(db, atendente)
    return ticket.setor_id in vis


def _pode_enviar_mensagem_publica(atendente: Atendente, ticket: Ticket) -> bool:
    """Andamento visível na conversa (tipo publico): admin, responsável ou fila sem responsável."""
    if atendente.role == "admin":
        return True
    if ticket.atendente_id is None:
        return True
    return ticket.atendente_id == atendente.id


def _pode_editar_mensagem_email(atendente: Atendente, mensagem: TicketMensagem) -> bool:
    if atendente.role == "admin":
        return True
    return mensagem.atendente_id == atendente.id


def _obter_mensagem_ticket(
    db: Session,
    *,
    ticket_id: int,
    mensagem_id: int,
    atendente: Atendente,
) -> tuple[Ticket, TicketMensagem]:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == mensagem_id, TicketMensagem.ticket_id == ticket_id)
        .first()
    )
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem não encontrada")
    return ticket, m


@router.get("", response_model=ListaPaginada[TicketRead])
def listar(
    empresa_id: int | None = Query(None),
    rede_id: int | None = Query(None, description="Tickets de empresas desta rede"),
    setor_id: int | None = Query(None),
    status_id: int | None = Query(None),
    protocolo: str | None = Query(None, description="Filtra por trecho do protocolo (ex.: #T202605-0001)"),
    busca: str | None = Query(None, description="Protocolo, assunto ou nome da empresa"),
    sem_responsavel: bool = Query(
        False,
        description="Somente tickets sem atendente atribuído (fila do setor)",
    ),
    meus: bool = Query(False, description="Somente tickets em que você é o responsável"),
    atendente_id: int | None = Query(
        None,
        description="Filtrar por responsável (apenas administradores)",
    ),
    situacao: SituacaoTicket = Query(
        SituacaoTicket.abertos,
        description="abertos = fechado_em vazio; fechados = fechado_em preenchido; todos = sem filtro",
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarTicketsPor | None = Query(
        None,
        description="Coluna para ordenação (default: data de criação, mais recentes primeiro)",
    ),
    ordem: OrdemLista = Query(
        OrdemLista.asc,
        description="asc = A→Z / menor primeiro; desc = Z→A / maior primeiro",
    ),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = (
        db.query(Ticket)
        .outerjoin(Ticket.empresa)
        .join(Ticket.setor)
        .join(Ticket.status)
        .filter(Ticket.tenant_id == atendente.tenant_id)
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(Ticket.setor_id.in_(vis))
    if empresa_id is not None:
        q = q.filter(Ticket.empresa_id == empresa_id)
    if rede_id is not None:
        q = q.filter(or_(Ticket.rede_id == rede_id, Empresa.rede_id == rede_id))
    if setor_id is not None:
        q = q.filter(Ticket.setor_id == setor_id)
    if status_id is not None:
        q = q.filter(Ticket.status_id == status_id)
    if atendente_id is not None:
        if atendente.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores podem filtrar por outro responsável",
            )
        q = q.filter(Ticket.atendente_id == atendente_id)
    elif meus:
        q = q.filter(Ticket.atendente_id == atendente.id)
    if sem_responsavel:
        q = q.filter(Ticket.atendente_id.is_(None))

    if situacao == SituacaoTicket.abertos:
        q = q.filter(Ticket.fechado_em.is_(None))
    elif situacao == SituacaoTicket.fechados:
        q = q.filter(Ticket.fechado_em.is_not(None))
    if protocolo and protocolo.strip():
        q = q.filter(Ticket.protocolo.ilike(f"%{protocolo.strip()}%"))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                Ticket.protocolo.ilike(term),
                Ticket.assunto.ilike(term),
                Empresa.nome.ilike(term),
            )
        )
    total = q.count()

    if ordenar_por is None:
        # Em finalizados, o mais útil é ordenar por data de fechamento (mais recentes primeiro).
        if situacao == SituacaoTicket.fechados:
            order_cols = [Ticket.fechado_em.desc().nullslast(), Ticket.id.desc()]
        else:
            order_cols = [Ticket.created_at.desc(), Ticket.id.desc()]
    else:
        if ordenar_por == OrdenarTicketsPor.responsavel:
            q = q.outerjoin(Ticket.atendente)
        elif ordenar_por == OrdenarTicketsPor.rede:
            q = q.outerjoin(Empresa.rede)

        if ordenar_por == OrdenarTicketsPor.protocolo:
            primary = expr_ordem(Ticket.protocolo, ordem)
        elif ordenar_por == OrdenarTicketsPor.rede:
            primary = expr_ordem(Rede.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.empresa:
            primary = expr_ordem(Empresa.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.setor:
            primary = expr_ordem(Setor.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.assunto:
            primary = expr_ordem(Ticket.assunto, ordem)
        elif ordenar_por == OrdenarTicketsPor.status:
            primary = expr_ordem(StatusTicket.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.fechado_em:
            primary = nullslast(expr_ordem(Ticket.fechado_em, ordem))
        else:
            primary = nullslast(expr_ordem(Atendente.nome, ordem))
        tie = expr_ordem(Ticket.id, ordem)
        order_cols = [primary, tie]

    rows = (
        q.options(
            joinedload(Ticket.empresa).joinedload(Empresa.rede),
            joinedload(Ticket.rede),
            joinedload(Ticket.setor),
            joinedload(Ticket.status),
            joinedload(Ticket.atendente),
        )
        .order_by(*order_cols)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ListaPaginada(items=[_ticket_para_read(t, db) for t in rows], total=total)


@router.post("", response_model=TicketRead, status_code=201)
def criar(
    data: TicketCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    # Atendente só pode abrir ticket em setor que ele atende
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        if data.setor_id not in vis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor")
    try:
        modo = validar_escopo_criacao_manual(
            empresa_id=data.empresa_id,
            rede_id=data.rede_id,
            parent_ticket_id=data.parent_ticket_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    setor = (
        db.query(Setor)
        .filter(Setor.id == data.setor_id, Setor.tenant_id == atendente.tenant_id)
        .first()
    )
    if not setor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")

    ticket_empresa_id: int | None
    ticket_rede_id: int | None
    if modo == "empresa":
        empresa = (
            db.query(Empresa)
            .filter(Empresa.id == data.empresa_id, Empresa.tenant_id == atendente.tenant_id)
            .first()
        )
        if not empresa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
        if not empresa.ativo:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa inativa")
        ticket_empresa_id = data.empresa_id
        ticket_rede_id = empresa.rede_id
    else:
        rede = (
            db.query(Rede)
            .filter(Rede.id == data.rede_id, Rede.tenant_id == atendente.tenant_id)
            .first()
        )
        if not rede:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rede não encontrada")
        if not rede.ativo:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rede inativa")
        ticket_empresa_id = None
        ticket_rede_id = rede.id

    if data.parent_ticket_id is not None:
        _assert_parent_valido(
            db,
            atendente,
            filho_empresa_id=data.empresa_id,
            filho_ticket_id=None,
            parent_id=data.parent_ticket_id,
        )
    # Status inicial: primeiro status ativo por ordem (ex.: «Aguardando atendimento» na fila do setor)
    status_inicial = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    if not status_inicial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cadastre ao menos um status de ticket")
    protocolo = _gerar_protocolo(db)
    ticket = Ticket(
        tenant_id=atendente.tenant_id,
        protocolo=protocolo,
        empresa_id=ticket_empresa_id,
        rede_id=ticket_rede_id,
        setor_id=data.setor_id,
        status_id=status_inicial.id,
        assunto=data.assunto,
        descricao=data.descricao,
        aberto_por_id=data.aberto_por_id,
        parent_ticket_id=data.parent_ticket_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    corpo_abertura = (data.descricao or "").strip() or "—"
    db.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=atendente.id,
            tipo="abertura",
            corpo=corpo_abertura,
        )
    )
    db.commit()
    ticket_out = (
        db.query(Ticket)
        .options(*_opcoes_carregamento_ticket_detalhe())
        .filter(Ticket.id == ticket.id)
        .first()
    )
    return _ticket_para_read(ticket_out or ticket, db)


@router.delete("/{ticket_id}")
def excluir_nao_permitido(ticket_id: int):
    """Tickets não podem ser excluídos; use alteração de status (ex.: fechado) conforme regra de negócio."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tickets não podem ser excluídos. Para encerrar, altere o status do ticket (ex.: Fechado).",
    )


@router.get("/{ticket_id}", response_model=TicketRead)
def obter(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = (
        db.query(Ticket)
        .options(*_opcoes_carregamento_ticket_detalhe())
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    return _ticket_para_read(ticket, db)


@router.get("/{ticket_id}/historico", response_model=list[TicketHistoricoRead])
def historico(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    rows = (
        db.query(TicketHistorico)
        .options(joinedload(TicketHistorico.atendente))
        .filter(TicketHistorico.ticket_id == ticket_id)
        .order_by(TicketHistorico.created_at.desc())
        .all()
    )
    return [
        TicketHistoricoRead(
            id=h.id,
            ticket_id=h.ticket_id,
            atendente_id=h.atendente_id,
            atendente_nome=h.atendente.nome if h.atendente else None,
            campo=h.campo,
            valor_antigo=h.valor_antigo,
            valor_novo=h.valor_novo,
            created_at=h.created_at,
        )
        for h in rows
    ]


@router.post("/{ticket_id}/vinculos", response_model=TicketVinculoRead, status_code=status.HTTP_201_CREATED)
def criar_vinculo(
    ticket_id: int,
    data: TicketVinculoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    related = db.query(Ticket).filter(Ticket.id == data.related_ticket_id).first()
    if not related:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket relacionado não encontrado")
    if not _pode_ver_ticket(db, atendente, related):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para vincular a este ticket",
        )
    try:
        v = criar_vinculo_ticket(
            db,
            ticket=ticket,
            related=related,
            tipo=data.tipo,
            atendente=atendente,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    duplicado_fechado = False
    if data.tipo == TIPO_DUPLICADO_DE and data.fechar_como_duplicado:
        try:
            status_antigo = ticket.status_id
            if fechar_ticket_como_duplicado(db, duplicado=ticket, original=related, atendente=atendente):
                duplicado_fechado = True
                _registrar_historico(
                    db,
                    ticket.id,
                    atendente.id,
                    "status_id",
                    str(status_antigo),
                    str(ticket.status_id),
                )
                _registrar_historico(
                    db,
                    ticket.id,
                    atendente.id,
                    "fechado_em",
                    "",
                    ticket.fechado_em.isoformat() if ticket.fechado_em else "",
                )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    _registrar_historico(
        db,
        ticket.id,
        atendente.id,
        "vinculo_ticket",
        "",
        f"{data.tipo}:{related.id}",
    )
    db.commit()
    db.refresh(v)
    return _vinculo_para_read(v, ticket.id, db, duplicado_fechado=duplicado_fechado)


@router.delete("/{ticket_id}/vinculos/{vinculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_vinculo(
    ticket_id: int,
    vinculo_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    v = db.query(TicketVinculo).filter(TicketVinculo.id == vinculo_id).first()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vínculo não encontrado")
    if ticket_id not in (v.ticket_id, v.related_ticket_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vínculo não encontrado neste ticket")
    other_id = outro_ticket_id(v, ticket_id)
    other = db.query(Ticket).filter(Ticket.id == other_id).first()
    if other and not _pode_ver_ticket(db, atendente, other):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para remover este vínculo")
    _registrar_historico(
        db,
        ticket.id,
        atendente.id,
        "vinculo_ticket",
        f"{v.tipo}:{other_id}",
        "",
    )
    db.delete(v)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{ticket_id}/filhos-em-massa/opcoes", response_model=TicketFilhosMassaOpcoesRead)
def opcoes_filhos_em_massa(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = (
        db.query(Ticket)
        .options(joinedload(Ticket.empresa).joinedload(Empresa.rede), joinedload(Ticket.rede))
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    try:
        rede_id, rede_nome, opcoes = listar_opcoes_filhos_massa(db, ticket)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return TicketFilhosMassaOpcoesRead(
        rede_id=rede_id,
        rede_nome=rede_nome,
        assunto_padrao=ticket.assunto,
        descricao_padrao=ticket.descricao,
        setor_id=ticket.setor_id,
        empresas=[
            TicketFilhoMassaEmpresaOpcao(id=o.id, nome=o.nome, ja_tem_filho=o.ja_tem_filho) for o in opcoes
        ],
    )


@router.post("/{ticket_id}/filhos-em-massa", response_model=TicketFilhosMassaRead, status_code=status.HTTP_201_CREATED)
def criar_filhos_em_massa_endpoint(
    ticket_id: int,
    data: TicketFilhosMassaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")

    setor_id = data.setor_id if data.setor_id is not None else ticket.setor_id
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        if setor_id not in vis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor")
    setor = db.query(Setor).filter(Setor.id == setor_id, Setor.tenant_id == atendente.tenant_id).first()
    if not setor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")

    assunto = (data.assunto if data.assunto is not None else ticket.assunto).strip()
    if not assunto:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assunto é obrigatório")
    descricao = data.descricao if data.descricao is not None else ticket.descricao

    for empresa_id in data.empresa_ids:
        _assert_parent_valido(
            db,
            atendente,
            filho_empresa_id=empresa_id,
            filho_ticket_id=None,
            parent_id=ticket.id,
        )

    try:
        criados = criar_filhos_em_massa(
            db,
            parent=ticket,
            atendente=atendente,
            empresa_ids=data.empresa_ids,
            assunto=assunto,
            descricao=descricao,
            setor_id=setor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    _registrar_historico(db, ticket.id, atendente.id, "filhos_em_massa", "", str(len(criados)))
    db.commit()

    empresa_nomes = {
        e.id: e.nome
        for e in db.query(Empresa).filter(Empresa.id.in_([t.empresa_id for t in criados if t.empresa_id])).all()
    }
    return TicketFilhosMassaRead(
        criados=[
            TicketFilhoMassaCriado(
                id=t.id,
                protocolo=t.protocolo,
                empresa_id=t.empresa_id,
                empresa_nome=empresa_nomes.get(t.empresa_id, ""),
            )
            for t in criados
        ],
        total=len(criados),
    )


def _mensagem_para_read(m: TicketMensagem) -> TicketMensagemRead:
    from app.services.email_body_sanitize import sanitize_inbound_email_body
    from app.services.ticket_mensagem_email_outbox import _as_utc

    corpo = m.corpo
    if m.tipo in ("abertura", "email_cliente"):
        corpo = sanitize_inbound_email_body(corpo)
    return TicketMensagemRead(
        id=m.id,
        ticket_id=m.ticket_id,
        atendente_id=m.atendente_id,
        atendente_nome=m.atendente.nome if m.atendente else None,
        autor_externo=getattr(m, "autor_externo", None),
        tipo=m.tipo,
        corpo=corpo,
        created_at=m.created_at,
        cliente_notificado_por_email=m.email_status == EMAIL_STATUS_ENVIADA,
        status=m.email_status,
        # Compat: alguns DBs/tests podem persistir datetimes sem tzinfo; a API sempre expõe em UTC.
        scheduled_at=_as_utc(m.scheduled_at),
        sent_at=_as_utc(m.sent_at),
        updated_at=_as_utc(m.updated_at),
    )


@router.get("/{ticket_id}/mensagens", response_model=list[TicketMensagemRead])
def listar_mensagens(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    rows = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.ticket_id == ticket_id)
        .order_by(TicketMensagem.created_at.asc())
        .all()
    )
    return [_mensagem_para_read(m) for m in rows]


@router.post("/{ticket_id}/mensagens", response_model=TicketMensagemRead, status_code=201)
def criar_mensagem(
    ticket_id: int,
    data: TicketMensagemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    if ticket.fechado_em is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket fechado. Reabra o ticket para enviar novas mensagens.",
        )
    if data.tipo == "publico" and not _pode_enviar_mensagem_publica(atendente, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o responsável pelo chamado ou um administrador pode enviar mensagem da equipe. "
            "Colaboradores do mesmo setor podem usar comentário interno.",
        )
    if data.notificar_cliente_por_email and data.tipo != "publico":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A notificação por e-mail só está disponível para mensagens públicas.",
        )
    corpo = data.corpo.strip()
    if not corpo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem vazia")

    if data.notificar_cliente_por_email:
        try:
            validar_pode_agendar_email_cliente(db, ticket.id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    m = TicketMensagem(
        ticket_id=ticket_id,
        atendente_id=atendente.id,
        tipo=data.tipo,
        corpo=corpo,
    )
    if data.notificar_cliente_por_email:
        agendar_envio_email(m, db)
    db.add(m)
    db.flush()
    db.commit()
    db.refresh(m)
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == m.id)
        .first()
    )
    assert m is not None
    return _mensagem_para_read(m)


@router.post(
    "/{ticket_id}/mensagens/{mensagem_id}/start-edit",
    response_model=TicketMensagemStartEditRead,
)
def iniciar_edicao_mensagem(
    ticket_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket, m = _obter_mensagem_ticket(db, ticket_id=ticket_id, mensagem_id=mensagem_id, atendente=atendente)
    if ticket.fechado_em is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket fechado.")
    if m.tipo != "publico" or not m.email_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem sem fila de e-mail.")
    if not _pode_enviar_mensagem_publica(atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão.")
    if not _pode_editar_mensagem_email(atendente, m):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só o autor ou admin pode editar.")
    try:
        token = iniciar_edicao(m)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    db.commit()
    db.refresh(m)
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == m.id)
        .first()
    )
    assert m is not None
    return TicketMensagemStartEditRead(edit_lock_token=token, mensagem=_mensagem_para_read(m))


@router.patch("/{ticket_id}/mensagens/{mensagem_id}", response_model=TicketMensagemRead)
def atualizar_mensagem(
    ticket_id: int,
    mensagem_id: int,
    data: TicketMensagemUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket, m = _obter_mensagem_ticket(db, ticket_id=ticket_id, mensagem_id=mensagem_id, atendente=atendente)
    if ticket.fechado_em is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket fechado.")
    if not _pode_editar_mensagem_email(atendente, m):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só o autor ou admin pode editar.")
    corpo = data.corpo.strip()
    if not corpo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem vazia")
    try:
        validar_lock(m, data.edit_lock_token.strip())
        salvar_edicao(m, db, corpo=corpo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    db.commit()
    db.refresh(m)
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == m.id)
        .first()
    )
    assert m is not None
    return _mensagem_para_read(m)


@router.post("/{ticket_id}/mensagens/{mensagem_id}/cancel", response_model=TicketMensagemRead)
def cancelar_mensagem_email(
    ticket_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket, m = _obter_mensagem_ticket(db, ticket_id=ticket_id, mensagem_id=mensagem_id, atendente=atendente)
    if not _pode_editar_mensagem_email(atendente, m):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só o autor ou admin pode cancelar.")
    try:
        cancelar_envio(m)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    db.commit()
    db.refresh(m)
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == m.id)
        .first()
    )
    assert m is not None
    return _mensagem_para_read(m)


@router.post("/{ticket_id}/mensagens/{mensagem_id}/send-now", response_model=TicketMensagemRead)
def enviar_mensagem_email_agora(
    ticket_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket, m = _obter_mensagem_ticket(db, ticket_id=ticket_id, mensagem_id=mensagem_id, atendente=atendente)
    if not _pode_enviar_mensagem_publica(atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão.")
    if not _pode_editar_mensagem_email(atendente, m):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só o autor ou admin pode enviar agora.")
    try:
        forcar_envio_agora(m)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    db.commit()
    process_pending_ticket_mensagem_emails(db, limit=5)
    db.commit()
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == m.id)
        .first()
    )
    assert m is not None
    return _mensagem_para_read(m)


def _registrar_historico(db: Session, ticket_id: int, atendente_id: int | None, campo: str, valor_antigo: str | None, valor_novo: str | None):
    db.add(TicketHistorico(
        ticket_id=ticket_id,
        atendente_id=atendente_id,
        campo=campo,
        valor_antigo=valor_antigo,
        valor_novo=valor_novo,
    ))


def _anexo_para_read(a: TicketAnexo) -> TicketAnexoRead:
    return TicketAnexoRead(
        id=a.id,
        ticket_id=a.ticket_id,
        mensagem_id=a.mensagem_id,
        atendente_id=a.atendente_id,
        atendente_nome=a.atendente.nome if a.atendente else None,
        visibilidade=(a.visibilidade or "publico"),  # type: ignore[arg-type]
        nome_original=a.nome_original,
        content_type=a.content_type,
        tamanho_bytes=a.tamanho_bytes,
        created_at=a.created_at,
    )


@router.get("/{ticket_id}/anexos", response_model=list[TicketAnexoRead])
def listar_anexos(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    rows = (
        db.query(TicketAnexo)
        .options(joinedload(TicketAnexo.atendente))
        .filter(TicketAnexo.ticket_id == ticket_id)
        .order_by(TicketAnexo.created_at.asc(), TicketAnexo.id.asc())
        .all()
    )
    return [_anexo_para_read(a) for a in rows]


@router.get("/{ticket_id}/anexos/{anexo_id}/download")
def download_anexo(
    ticket_id: int,
    anexo_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")

    a = (
        db.query(TicketAnexo)
        .filter(TicketAnexo.id == anexo_id, TicketAnexo.ticket_id == ticket_id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado")
    p = ticket_anexo_storage.caminho_absoluto_arquivo(a.storage_key)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado no storage")

    # Força download (evita execução inline de tipos perigosos).
    return FileResponse(
        path=str(p),
        filename=a.nome_original,
        media_type="application/octet-stream",
    )


@router.post("/{ticket_id}/anexos", response_model=TicketAnexoCreateResponse, status_code=201)
def upload_anexo(
    ticket_id: int,
    file: UploadFile = File(...),
    mensagem_id: int | None = Form(None, description="Opcional: associa o anexo a uma mensagem do ticket"),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    if ticket.fechado_em is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket fechado. Reabra o ticket para enviar anexos.",
        )

    msg: TicketMensagem | None = None
    vis = "publico"
    if mensagem_id is not None:
        msg = (
            db.query(TicketMensagem)
            .filter(TicketMensagem.id == mensagem_id, TicketMensagem.ticket_id == ticket_id)
            .first()
        )
        if not msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem inválida para este ticket")
        if msg.tipo == "interno":
            vis = "interno"

    data = file.file.read()
    try:
        nome_original, mime = ticket_anexo_storage.validar_upload(file.filename, file.content_type, len(data))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        storage_key = ticket_anexo_storage.gravar_bytes_em_disco(data, mimetype=mime, nome_original=nome_original)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OSError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gravar arquivo")

    a = TicketAnexo(
        ticket_id=ticket_id,
        mensagem_id=msg.id if msg else None,
        atendente_id=atendente.id,
        visibilidade=vis,
        nome_original=nome_original,
        content_type=mime,
        tamanho_bytes=len(data),
        storage_key=storage_key,
    )
    db.add(a)
    db.flush()
    _registrar_historico(db, ticket_id, atendente.id, "anexo", "", f"{a.id}")
    db.commit()
    db.refresh(a)

    return TicketAnexoCreateResponse(
        anexo=_anexo_para_read(a),
        download_url=f"/v1/tickets/{ticket_id}/anexos/{a.id}/download",
    )


@router.post("/{ticket_id}/reabrir", response_model=TicketRead)
def reabrir(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    if atendente.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores podem reabrir tickets")
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if ticket.fechado_em is None:
        return _ticket_para_read(ticket, db)

    # Status para retorno: primeiro status ativo que não seja "fechado"
    status_reaberto = (
        db.query(StatusTicket)
        .filter(StatusTicket.ativo.is_(True))
        .order_by(StatusTicket.ordem.asc(), StatusTicket.id.asc())
        .all()
    )
    novo_status = None
    for st in status_reaberto:
        if (st.slug or "").lower() != "fechado":
            novo_status = st
            break
    if not novo_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cadastre um status não-final para reabrir")

    _registrar_historico(db, ticket.id, atendente.id, "fechado_em", str(ticket.fechado_em), "")
    if ticket.status_id != novo_status.id:
        _registrar_historico(db, ticket.id, atendente.id, "status_id", str(ticket.status_id), str(novo_status.id))

    ticket.fechado_em = None
    ticket.status_id = novo_status.id
    db.commit()
    db.refresh(ticket)
    return _ticket_para_read(ticket, db)


@router.patch("/{ticket_id}", response_model=TicketRead)
def atualizar(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    if ticket.fechado_em is not None and atendente.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket fechado. Apenas administradores podem reabrir ou alterar este ticket.",
        )
    update = data.model_dump(exclude_unset=True)

    if "status_id" in update:
        st_novo = db.query(StatusTicket).filter(StatusTicket.id == update["status_id"]).first()
        if st_novo and (st_novo.slug or "").lower() == "fechado":
            filho_aberto = (
                db.query(Ticket.id)
                .filter(Ticket.parent_ticket_id == ticket.id, Ticket.fechado_em.is_(None))
                .first()
            )
            if filho_aberto is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não é possível fechar este ticket enquanto existir ticket filho direto ainda em aberto.",
                )

    if "parent_ticket_id" in update:
        novo_p = update["parent_ticket_id"]
        if novo_p != ticket.parent_ticket_id:
            if novo_p is not None:
                _assert_parent_valido(
                    db,
                    atendente,
                    filho_empresa_id=ticket.empresa_id,
                    filho_ticket_id=ticket.id,
                    parent_id=novo_p,
                )
            antigo_pid = ticket.parent_ticket_id
            _registrar_historico(
                db,
                ticket.id,
                atendente.id,
                "parent_ticket_id",
                str(antigo_pid) if antigo_pid is not None else "",
                str(novo_p) if novo_p is not None else "",
            )

    if "setor_id" in update:
        if atendente.role != "admin":
            permitidos = ids_setores_visiveis_atendente(db, atendente)
            if update["setor_id"] not in permitidos:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para mover o ticket para este setor",
                )
        novo_setor = db.query(Setor).filter(Setor.id == update["setor_id"]).first()
        if not novo_setor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")

    setor_final = update["setor_id"] if "setor_id" in update else ticket.setor_id

    if "atendente_id" in update and atendente.role != "admin":
        novo_at = update["atendente_id"]
        if novo_at is not None and novo_at != atendente.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente administradores podem definir outro responsável.",
            )

    if "atendente_id" in update and update["atendente_id"] is not None:
        if not responsavel_elegivel_para_setor_do_ticket(db, update["atendente_id"], setor_final):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O responsável indicado não pode ser atribuído a este setor.",
            )

    # Transferência de setor: se o responsável atual não atende o setor de destino, volta à fila.
    # Administradores permanecem responsáveis mesmo sem vínculo ao setor (#38).
    if "setor_id" in update and update["setor_id"] != ticket.setor_id and "atendente_id" not in update:
        if ticket.atendente_id is not None:
            atual_resp = db.query(Atendente).filter(Atendente.id == ticket.atendente_id).first()
            if atual_resp and atual_resp.role == "admin":
                pass
            elif not atendente_atende_algum_id_setor(db, ticket.atendente_id, update["setor_id"]):
                update["atendente_id"] = None

    if "status_id" in update:
        antigo = str(ticket.status_id)
        novo = str(update["status_id"])
        _registrar_historico(db, ticket.id, atendente.id, "status_id", antigo, novo)
    if "atendente_id" in update:
        antigo = str(ticket.atendente_id) if ticket.atendente_id else ""
        novo_s = update["atendente_id"]
        novo = str(novo_s) if novo_s is not None else ""
        _registrar_historico(db, ticket.id, atendente.id, "atendente_id", antigo, novo)
    if "setor_id" in update:
        antigo = str(ticket.setor_id)
        novo = str(update["setor_id"])
        _registrar_historico(db, ticket.id, atendente.id, "setor_id", antigo, novo)
    if "empresa_id" in update:
        novo_eid = update["empresa_id"]
        if novo_eid is not None:
            empresa = (
                db.query(Empresa)
                .filter(Empresa.id == novo_eid, Empresa.tenant_id == ticket.tenant_id)
                .first()
            )
            if not empresa:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
            email_rem = None
            if ticket.aberto_por_id:
                f_ab = db.query(FuncionarioRede).filter(FuncionarioRede.id == ticket.aberto_por_id).first()
                email_rem = (f_ab.email or "").strip() if f_ab else None
            if not email_rem:
                row_in = (
                    db.query(EmailInboundReceived)
                    .filter(EmailInboundReceived.ticket_id == ticket.id)
                    .order_by(EmailInboundReceived.id.desc())
                    .first()
                )
                if row_in:
                    email_rem = extrair_email_de_from_address(row_in.from_address)
            rem = resolver_remetente_por_email(db, email_rem)
            if rem.empresa_ids_opcao and int(novo_eid) not in rem.empresa_ids_opcao:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Esta empresa não está vinculada ao funcionário remetente do e-mail.",
                )
            ticket.rede_id = empresa.rede_id
        antigo = str(ticket.empresa_id) if ticket.empresa_id is not None else ""
        novo = str(novo_eid) if novo_eid is not None else ""
        _registrar_historico(db, ticket.id, atendente.id, "empresa_id", antigo, novo)

    for k, v in update.items():
        setattr(ticket, k, v)

    if "status_id" in update:
        st = db.query(StatusTicket).filter(StatusTicket.id == ticket.status_id).first()
        slug = (st.slug or "").lower() if st else ""
        if slug == "fechado":
            ticket.fechado_em = datetime.now(timezone.utc)
        else:
            ticket.fechado_em = None

    db.commit()
    ticket_out = (
        db.query(Ticket)
        .options(*_opcoes_carregamento_ticket_detalhe())
        .filter(Ticket.id == ticket_id)
        .first()
    )
    return _ticket_para_read(ticket_out or ticket, db)
