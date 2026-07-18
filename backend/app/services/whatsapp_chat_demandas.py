"""Serviço de demandas por sessão WhatsApp (#423)."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.models.whatsapp_chat_demanda import DESFECHOS_DEMANDA, WhatsappChatDemanda
from app.schemas.dashboard import ContagemIdNome
from app.schemas.whatsapp_chat import WhatsappChatDemandaCreate, WhatsappChatDemandaRead, WhatsappChatDemandaUpdate
from app.services.chat_dashboard_filters import apply_chat_dashboard_filters, period_bounds

DESFECHO_MARCO = {
    "resolvido_sessao": "Resolvido na sessão",
    "escalado_ticket": "Escalado para ticket",
}


def _rotulo_demanda(row: WhatsappChatDemanda) -> str:
    nat = row.natureza.nome if row.natureza else "Demanda"
    if row.motivo and row.motivo.nome:
        return f"{nat} · {row.motivo.nome}"
    return nat


def corpo_marco_demanda(row: WhatsappChatDemanda) -> str:
    desfecho = DESFECHO_MARCO.get(row.desfecho, row.desfecho)
    return f"[demanda_id={row.id}] Demanda registada: {_rotulo_demanda(row)} — {desfecho}"


def criar_marco_demanda_mensagem(
    db: Session,
    *,
    chat: WhatsappChat,
    atendente: Atendente,
    demanda: WhatsappChatDemanda,
) -> WhatsappMensagem:
    evento = "demanda_registrada" if demanda.desfecho == "resolvido_sessao" else "demanda_escalada"
    m = WhatsappMensagem(
        chat_id=chat.id,
        direcao="outbound",
        corpo=corpo_marco_demanda(demanda),
        tipo_midia="texto",
        mimetype=None,
        midia_nome_arquivo=None,
        wa_message_id=None,
        atendente_id=atendente.id,
        evento_sistema=evento,
    )
    db.add(m)
    db.flush()
    return m


def remover_marco_demanda_mensagem(db: Session, *, chat_id: int, demanda_id: int) -> None:
    tag = f"[demanda_id={demanda_id}]"
    rows = (
        db.query(WhatsappMensagem)
        .filter(
            WhatsappMensagem.chat_id == chat_id,
            WhatsappMensagem.evento_sistema.in_(("demanda_registrada", "demanda_escalada")),
            WhatsappMensagem.corpo.like(f"{tag}%"),
        )
        .all()
    )
    for row in rows:
        db.delete(row)


def _validar_natureza_motivo(
    db: Session,
    *,
    natureza_id: int,
    motivo_id: int | None,
) -> tuple[TicketNatureza, TicketMotivo | None]:
    natureza = db.query(TicketNatureza).filter(TicketNatureza.id == natureza_id, TicketNatureza.ativo.is_(True)).first()
    if not natureza:
        raise HTTPException(status_code=400, detail="Natureza inválida ou inativa")
    motivo = None
    if motivo_id is not None:
        motivo = (
            db.query(TicketMotivo)
            .filter(
                TicketMotivo.id == motivo_id,
                TicketMotivo.natureza_id == natureza.id,
                TicketMotivo.ativo.is_(True),
            )
            .first()
        )
        if not motivo:
            raise HTTPException(status_code=400, detail="Motivo inválido, inativo ou não pertence à natureza")
    return natureza, motivo


def demanda_para_read(row: WhatsappChatDemanda) -> WhatsappChatDemandaRead:
    return WhatsappChatDemandaRead(
        id=row.id,
        chat_id=row.chat_id,
        natureza_id=row.natureza_id,
        natureza_nome=row.natureza.nome if row.natureza else None,
        motivo_id=row.motivo_id,
        motivo_nome=row.motivo.nome if row.motivo else None,
        desfecho=row.desfecho,
        ticket_id=row.ticket_id,
        descricao_curta=row.descricao_curta,
        atendente_id=row.atendente_id,
        atendente_nome=row.atendente.nome if row.atendente else None,
        created_at=row.created_at,
    )


def criar_demanda_chat(
    db: Session,
    chat: WhatsappChat,
    atendente: Atendente,
    data: WhatsappChatDemandaCreate,
    *,
    desfecho: str = "resolvido_sessao",
    ticket_id: int | None = None,
) -> WhatsappChatDemanda:
    if chat.estado not in ("em_atendimento", "aguardando_avaliacao", "encerrado"):
        raise HTTPException(status_code=400, detail="Registre demandas apenas em chats em atendimento ou pós-inatividade")
    desfecho_eff = (desfecho or "resolvido_sessao").strip()
    if desfecho_eff not in DESFECHOS_DEMANDA:
        raise HTTPException(status_code=400, detail="Desfecho inválido")
    _validar_natureza_motivo(db, natureza_id=data.natureza_id, motivo_id=data.motivo_id)
    desc = (data.descricao_curta or "").strip() or None
    if desc and len(desc) > 500:
        raise HTTPException(status_code=400, detail="Descrição curta excede 500 caracteres")
    row = WhatsappChatDemanda(
        chat_id=chat.id,
        natureza_id=data.natureza_id,
        motivo_id=data.motivo_id,
        desfecho=desfecho_eff,
        ticket_id=ticket_id,
        descricao_curta=desc,
        atendente_id=atendente.id,
    )
    db.add(row)
    db.flush()
    return (
        db.query(WhatsappChatDemanda)
        .options(
            joinedload(WhatsappChatDemanda.natureza),
            joinedload(WhatsappChatDemanda.motivo),
            joinedload(WhatsappChatDemanda.atendente),
        )
        .filter(WhatsappChatDemanda.id == row.id)
        .first()
    )


def listar_demandas_chat(db: Session, chat_id: int) -> list[WhatsappChatDemandaRead]:
    rows = (
        db.query(WhatsappChatDemanda)
        .options(
            joinedload(WhatsappChatDemanda.natureza),
            joinedload(WhatsappChatDemanda.motivo),
            joinedload(WhatsappChatDemanda.atendente),
        )
        .filter(WhatsappChatDemanda.chat_id == chat_id)
        .order_by(WhatsappChatDemanda.created_at.asc(), WhatsappChatDemanda.id.asc())
        .all()
    )
    return [demanda_para_read(r) for r in rows]


def atualizar_demanda_chat(
    db: Session,
    chat: WhatsappChat,
    row: WhatsappChatDemanda,
    data: WhatsappChatDemandaUpdate,
    *,
    atendente: Atendente,
) -> WhatsappChatDemanda:
    if chat.estado not in ("em_atendimento", "aguardando_avaliacao", "encerrado"):
        raise HTTPException(status_code=400, detail="Edite demandas apenas em chats em atendimento ou pós-inatividade")
    if row.desfecho != "resolvido_sessao":
        raise HTTPException(status_code=400, detail="Demandas escaladas para ticket não podem ser editadas")
    if atendente.role != "admin" and row.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Somente quem registrou ou admin pode editar")
    update = data.model_dump(exclude_unset=True)
    natureza_id = update.get("natureza_id", row.natureza_id)
    motivo_id = update.get("motivo_id", row.motivo_id)
    if "motivo_id" in update and update["motivo_id"] is None:
        motivo_id = None
    _validar_natureza_motivo(db, natureza_id=int(natureza_id), motivo_id=motivo_id)
    if "natureza_id" in update:
        row.natureza_id = int(natureza_id)
    if "motivo_id" in update or "natureza_id" in update:
        row.motivo_id = motivo_id
    if "descricao_curta" in update:
        desc = (update["descricao_curta"] or "").strip() or None
        if desc and len(desc) > 500:
            raise HTTPException(status_code=400, detail="Descrição curta excede 500 caracteres")
        row.descricao_curta = desc
    db.flush()
    refreshed = (
        db.query(WhatsappChatDemanda)
        .options(
            joinedload(WhatsappChatDemanda.natureza),
            joinedload(WhatsappChatDemanda.motivo),
            joinedload(WhatsappChatDemanda.atendente),
        )
        .filter(WhatsappChatDemanda.id == row.id)
        .first()
    )
    assert refreshed is not None
    return refreshed


def agregar_demandas_por_natureza(
    db: Session,
    atendente: Atendente,
    *,
    de: date,
    ate: date,
    setor_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
) -> list[ContagemIdNome]:
    de_dt, ate_dt = period_bounds(de, ate)
    stmt = (
        select(TicketNatureza.id, TicketNatureza.nome, func.count())
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .join(TicketNatureza, TicketNatureza.id == WhatsappChatDemanda.natureza_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
        )
        .group_by(TicketNatureza.id, TicketNatureza.nome)
        .order_by(func.count().desc(), TicketNatureza.nome.asc())
    )
    if empresa_id is not None:
        stmt = stmt.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt = stmt.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(Empresa.rede_id == rede_id)
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, setor_id=setor_id)
    return [ContagemIdNome(id=int(nid), nome=str(nome), total=int(total)) for nid, nome, total in db.execute(stmt)]


def agregar_demandas_por_motivo(
    db: Session,
    atendente: Atendente,
    *,
    de: date,
    ate: date,
    setor_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
) -> list[ContagemIdNome]:
    de_dt, ate_dt = period_bounds(de, ate)
    stmt = (
        select(TicketMotivo.id, TicketMotivo.nome, func.count())
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .join(TicketMotivo, TicketMotivo.id == WhatsappChatDemanda.motivo_id)
        .where(
            WhatsappChatDemanda.motivo_id.isnot(None),
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
        )
        .group_by(TicketMotivo.id, TicketMotivo.nome)
        .order_by(func.count().desc(), TicketMotivo.nome.asc())
    )
    if empresa_id is not None:
        stmt = stmt.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt = stmt.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(Empresa.rede_id == rede_id)
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, setor_id=setor_id)
    return [ContagemIdNome(id=int(mid), nome=str(nome), total=int(total)) for mid, nome, total in db.execute(stmt)]
