"""Regras de negócio dos tickets no portal do cliente."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.portal_scope import (
    assert_empresa_no_escopo,
    empresa_ids_visiveis,
    tenant_id_do_funcionario,
    ticket_no_escopo,
)
from app.core.routing import RoutingCanal
from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede
from app.models.setor import Setor
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketMensagem
from app.models.ticket_anexo import TicketAnexo
from app.schemas.portal import (
    PortalAnexoRead,
    PortalMensagemRead,
    PortalTicketCreate,
    PortalTicketDetail,
    PortalTicketListItem,
)
from app.services.protocolo_mensal import gerar_protocolo_ticket
from app.services.routing_apply import acoes_efetivas_do_resultado, registrar_roteamento_aplicado
from app.services.routing_evaluate import RoutingContext, aplicar_roteamento_setor, evaluate_routing
from app.services.ticket_distribuicao import sincronizar_fila_desde_at, tentar_distribuicao_imediata
from app.services.realtime_emit import (
    emit_notificacao_after_counter_change,
    emit_ticket_fila,
    emit_ticket_mensagem_from_model,
)


TIPOS_PUBLICOS_PORTAL = frozenset({"abertura", "publico", "email_cliente"})


def _status_nome(ticket: Ticket) -> tuple[str | None, str | None]:
    st = getattr(ticket, "status", None)
    if st is None:
        return None, None
    return getattr(st, "nome", None), getattr(st, "slug", None)


def _empresa_nome(ticket: Ticket) -> str | None:
    emp = getattr(ticket, "empresa", None)
    return getattr(emp, "nome", None) if emp else None


def _setor_nome(ticket: Ticket) -> str | None:
    setor = getattr(ticket, "setor", None)
    return getattr(setor, "nome", None) if setor else None


def ticket_para_list_item(ticket: Ticket) -> PortalTicketListItem:
    status_nome, status_slug = _status_nome(ticket)
    ultima = None
    msgs = getattr(ticket, "mensagens", None)
    if msgs:
        publicas = [m for m in msgs if m.tipo in TIPOS_PUBLICOS_PORTAL]
        if publicas:
            ultima = max((m.created_at for m in publicas if m.created_at), default=None)
    return PortalTicketListItem(
        id=ticket.id,
        protocolo=ticket.protocolo,
        assunto=ticket.assunto,
        status_nome=status_nome,
        status_slug=status_slug,
        empresa_id=ticket.empresa_id,
        empresa_nome=_empresa_nome(ticket),
        setor_nome=_setor_nome(ticket),
        prioridade=str(ticket.prioridade) if ticket.prioridade else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        fechado_em=ticket.fechado_em,
        ultima_mensagem_em=ultima,
    )


def ticket_para_detail(db: Session, ticket: Ticket) -> PortalTicketDetail:
    base = ticket_para_list_item(ticket)
    csat_pendente = False
    if ticket.fechado_em is not None:
        from app.models.ticket_avaliacao import TicketAvaliacao

        ja_avaliou = (
            db.query(TicketAvaliacao).filter(TicketAvaliacao.ticket_id == ticket.id).first() is not None
        )
        csat_pendente = not ja_avaliou
    return PortalTicketDetail(
        **base.model_dump(),
        descricao=ticket.descricao,
        pode_responder=ticket.fechado_em is None,
        csat_token=None,
        csat_pendente=csat_pendente,
    )


def obter_ticket_escopo(db: Session, funcionario: FuncionarioRede, ticket_id: int) -> Ticket:
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.status),
            joinedload(Ticket.empresa),
            joinedload(Ticket.setor),
            joinedload(Ticket.mensagens),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket or not ticket_no_escopo(db, funcionario, ticket):
        raise LookupError("Ticket não encontrado")
    return ticket


def listar_tickets(
    db: Session,
    funcionario: FuncionarioRede,
    *,
    situacao: str = "abertos",
    busca: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Ticket], int]:
    ids = empresa_ids_visiveis(db, funcionario)
    from app.services.funcionario_escopo import escopo_efetivo, rede_id_efetiva

    rede_id = rede_id_efetiva(db, funcionario)
    q = db.query(Ticket).options(
        joinedload(Ticket.status),
        joinedload(Ticket.empresa),
        joinedload(Ticket.setor),
        joinedload(Ticket.mensagens),
    )
    filtros = []
    if ids:
        filtros.append(Ticket.empresa_id.in_(ids))
    if rede_id is not None and escopo_efetivo(funcionario) == "all":
        filtros.append((Ticket.empresa_id.is_(None)) & (Ticket.rede_id == rede_id))
    if not filtros:
        return [], 0
    q = q.filter(or_(*filtros))
    sit = (situacao or "abertos").strip().lower()
    if sit == "abertos":
        q = q.filter(Ticket.fechado_em.is_(None))
    elif sit == "fechados":
        q = q.filter(Ticket.fechado_em.is_not(None))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(Ticket.protocolo.ilike(term), Ticket.assunto.ilike(term)))
    total = q.count()
    rows = q.order_by(Ticket.id.desc()).offset(offset).limit(limit).all()
    return rows, total


def criar_ticket(
    db: Session,
    funcionario: FuncionarioRede,
    data: PortalTicketCreate,
) -> Ticket:
    emp = assert_empresa_no_escopo(db, funcionario, data.empresa_id)
    tenant_id = tenant_id_do_funcionario(db, funcionario)

    setor_id_efetivo = data.setor_id
    rota_resultado = evaluate_routing(
        db,
        tenant_id=tenant_id,
        context=RoutingContext(
            assunto=data.assunto,
            canal=RoutingCanal.manual,
            rede_id=emp.rede_id,
        ),
    )
    if rota_resultado.matched:
        setor_id_efetivo = aplicar_roteamento_setor(
            setor_atual=data.setor_id,
            resultado=rota_resultado,
            aplicar_setor=data.setor_id is None,
        )

    if setor_id_efetivo is None:
        raise ValueError("Selecione o setor de atendimento.")

    setor = db.query(Setor).filter(Setor.id == setor_id_efetivo, Setor.tenant_id == tenant_id, Setor.ativo.is_(True)).first()
    if not setor:
        raise ValueError("Setor não encontrado.")

    status_inicial = (
        db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    )
    if not status_inicial:
        raise ValueError("Cadastre ao menos um status de ticket.")

    descricao = (data.descricao or "").strip() or None
    if data.pdv_codigo and data.pdv_codigo.strip():
        pdv_line = f"PDV: {data.pdv_codigo.strip()}"
        descricao = f"{pdv_line}\n\n{descricao}" if descricao else pdv_line

    motivo_id_rota = data.motivo_id
    atendente_id_rota = None
    if rota_resultado.matched:
        mid, aid = acoes_efetivas_do_resultado(
            db,
            tenant_id=tenant_id,
            setor_id=setor_id_efetivo,
            resultado=rota_resultado,
        )
        if motivo_id_rota is None:
            motivo_id_rota = mid
        atendente_id_rota = aid

    protocolo = gerar_protocolo_ticket(db)
    ticket = Ticket(
        tenant_id=tenant_id,
        protocolo=protocolo,
        empresa_id=emp.id,
        rede_id=emp.rede_id,
        setor_id=setor_id_efetivo,
        status_id=status_inicial.id,
        prioridade="normal",
        assunto=data.assunto.strip(),
        descricao=descricao,
        aberto_por_id=funcionario.id,
        motivo_id=motivo_id_rota,
        motivo_outro_texto=(data.motivo_outro_texto or None),
        atendente_id=atendente_id_rota,
    )
    db.add(ticket)
    db.flush()
    from app.services.sla_policy import aplicar_sla_snapshot_ao_ticket

    aplicar_sla_snapshot_ao_ticket(db, ticket)
    if rota_resultado.matched:
        registrar_roteamento_aplicado(
            db,
            resultado=rota_resultado,
            ticket_id=ticket.id,
            atendente_audit_id=None,
        )

    corpo_abertura = descricao or "—"
    autor = (funcionario.nome or "").strip() or (funcionario.email or "Cliente")
    msg = TicketMensagem(
        ticket_id=ticket.id,
        atendente_id=None,
        tipo="abertura",
        corpo=corpo_abertura,
        autor_externo=autor,
    )
    db.add(msg)
    db.commit()
    db.refresh(ticket)

    contagem_ja_emitida = False
    if ticket.atendente_id is None:
        sincronizar_fila_desde_at(ticket)
        db.commit()
        if tentar_distribuicao_imediata(db, ticket):
            db.commit()
            emit_notificacao_after_counter_change(db)
            contagem_ja_emitida = True
        else:
            emit_ticket_fila(db, ticket)
            contagem_ja_emitida = True

    msg_abertura = (
        db.query(TicketMensagem)
        .filter(TicketMensagem.ticket_id == ticket.id, TicketMensagem.tipo == "abertura")
        .order_by(TicketMensagem.id.desc())
        .first()
    )
    if msg_abertura:
        emit_ticket_mensagem_from_model(
            db,
            ticket,
            msg_abertura,
            exclude_atendente_id=None,
            emit_notificacao=not contagem_ja_emitida,
        )
    return obter_ticket_escopo(db, funcionario, ticket.id)


def mensagem_para_read(
    db: Session,
    funcionario: FuncionarioRede,
    m: TicketMensagem,
) -> PortalMensagemRead:
    anexos_rows = (
        db.query(TicketAnexo)
        .filter(
            TicketAnexo.mensagem_id == m.id,
            TicketAnexo.visibilidade == "publico",
        )
        .order_by(TicketAnexo.id.asc())
        .all()
    )
    anexos = [
        PortalAnexoRead(
            id=a.id,
            nome_original=a.nome_original,
            content_type=a.content_type,
            tamanho_bytes=int(a.tamanho_bytes or 0),
            mensagem_id=a.mensagem_id,
            created_at=a.created_at,
            download_url=f"/v1/portal/tickets/{m.ticket_id}/anexos/{a.id}/download",
        )
        for a in anexos_rows
    ]
    if m.atendente_id:
        atendente = getattr(m, "atendente", None)
        nome = getattr(atendente, "nome", None) or "Equipe de suporte"
        papel: str = "equipe"
    elif m.tipo == "abertura" or m.tipo == "email_cliente":
        nome = (m.autor_externo or funcionario.nome or "Você")
        # Se o autor externo for o próprio funcionário ou abertura pelo portal
        papel = "voce"
    else:
        nome = m.autor_externo or "Sistema"
        papel = "sistema"
    return PortalMensagemRead(
        id=m.id,
        tipo=m.tipo,
        corpo=m.corpo,
        autor_nome=nome,
        autor_papel=papel,  # type: ignore[arg-type]
        created_at=m.created_at,
        anexos=anexos,
    )


def listar_mensagens_publicas(
    db: Session,
    funcionario: FuncionarioRede,
    ticket: Ticket,
) -> list[PortalMensagemRead]:
    rows = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(
            TicketMensagem.ticket_id == ticket.id,
            TicketMensagem.tipo.in_(list(TIPOS_PUBLICOS_PORTAL)),
        )
        .order_by(TicketMensagem.created_at.asc())
        .all()
    )
    return [mensagem_para_read(db, funcionario, m) for m in rows]


def criar_mensagem_portal(
    db: Session,
    funcionario: FuncionarioRede,
    ticket: Ticket,
    corpo: str,
) -> TicketMensagem:
    if ticket.fechado_em is not None:
        raise ValueError(
            "Este chamado está encerrado. Abra um novo chamado para continuar o atendimento."
        )
    texto = corpo.strip()
    if not texto:
        raise ValueError("Mensagem vazia")
    autor = (funcionario.nome or "").strip() or (funcionario.email or "Cliente")
    m = TicketMensagem(
        ticket_id=ticket.id,
        atendente_id=None,
        tipo="email_cliente",
        corpo=texto,
        autor_externo=autor,
    )
    db.add(m)
    db.flush()

    # Se estava aguardando cliente, volta para em atendimento quando houver esse status
    st = ticket.status
    if st is not None and (st.slug or "").lower() == "aguardando_cliente":
        em_atend = (
            db.query(StatusTicket)
            .filter(StatusTicket.slug == "em_atendimento", StatusTicket.ativo.is_(True))
            .first()
        )
        if em_atend:
            ticket.status_id = em_atend.id
            ticket.updated_at = datetime.now(timezone.utc)

    from app.services.notificacao_atendente_email import notificar_nova_mensagem_ticket

    notificar_nova_mensagem_ticket(db, ticket=ticket, mensagem=m, autor_atendente_id=None)
    db.commit()
    db.refresh(m)
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == m.id)
        .first()
    )
    assert m is not None
    emit_ticket_mensagem_from_model(db, ticket, m, exclude_atendente_id=None)
    return m


def listar_anexos_publicos(db: Session, ticket: Ticket) -> list[PortalAnexoRead]:
    rows = (
        db.query(TicketAnexo)
        .filter(TicketAnexo.ticket_id == ticket.id, TicketAnexo.visibilidade == "publico")
        .order_by(TicketAnexo.id.asc())
        .all()
    )
    return [
        PortalAnexoRead(
            id=a.id,
            nome_original=a.nome_original,
            content_type=a.content_type,
            tamanho_bytes=int(a.tamanho_bytes or 0),
            mensagem_id=a.mensagem_id,
            created_at=a.created_at,
            download_url=f"/v1/portal/tickets/{ticket.id}/anexos/{a.id}/download",
        )
        for a in rows
    ]


def obter_anexo_publico(db: Session, ticket: Ticket, anexo_id: int) -> TicketAnexo:
    a = (
        db.query(TicketAnexo)
        .filter(
            TicketAnexo.id == anexo_id,
            TicketAnexo.ticket_id == ticket.id,
            TicketAnexo.visibilidade == "publico",
        )
        .first()
    )
    if not a:
        raise LookupError("Anexo não encontrado")
    return a
