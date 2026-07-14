"""Serviço de demandas por sessão portal."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.portal_chat import PortalChat, PortalMensagem
from app.models.portal_chat_demanda import DESFECHOS_DEMANDA_PORTAL, PortalChatDemanda
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.schemas.portal_chat import PortalChatDemandaCreate, PortalChatDemandaRead, PortalChatDemandaUpdate

DESFECHO_MARCO = {
    "resolvido_sessao": "Resolvido na sessão",
    "escalado_ticket": "Escalado para ticket",
}


def _rotulo_demanda(row: PortalChatDemanda) -> str:
    nat = row.natureza.nome if row.natureza else "Demanda"
    if row.motivo and row.motivo.nome:
        return f"{nat} · {row.motivo.nome}"
    return nat


def corpo_marco_demanda(row: PortalChatDemanda) -> str:
    desfecho = DESFECHO_MARCO.get(row.desfecho, row.desfecho)
    return f"[demanda_id={row.id}] Demanda registada: {_rotulo_demanda(row)} — {desfecho}"


def criar_marco_demanda_mensagem(
    db: Session,
    *,
    chat: PortalChat,
    atendente: Atendente,
    demanda: PortalChatDemanda,
) -> PortalMensagem:
    evento = "demanda_registrada" if demanda.desfecho == "resolvido_sessao" else "demanda_escalada"
    m = PortalMensagem(
        chat_id=chat.id,
        direcao="outbound",
        corpo=corpo_marco_demanda(demanda),
        atendente_id=atendente.id,
        evento_sistema=evento,
    )
    db.add(m)
    db.flush()
    return m


def remover_marco_demanda_mensagem(db: Session, *, chat_id: int, demanda_id: int) -> None:
    tag = f"[demanda_id={demanda_id}]"
    rows = (
        db.query(PortalMensagem)
        .filter(
            PortalMensagem.chat_id == chat_id,
            PortalMensagem.evento_sistema.in_(("demanda_registrada", "demanda_escalada")),
            PortalMensagem.corpo.like(f"{tag}%"),
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


def demanda_para_read(row: PortalChatDemanda) -> PortalChatDemandaRead:
    return PortalChatDemandaRead(
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
    chat: PortalChat,
    atendente: Atendente,
    data: PortalChatDemandaCreate,
    *,
    desfecho: str = "resolvido_sessao",
    ticket_id: int | None = None,
) -> PortalChatDemanda:
    if chat.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Registre demandas apenas em chats em atendimento")
    desfecho_eff = (desfecho or "resolvido_sessao").strip()
    if desfecho_eff not in DESFECHOS_DEMANDA_PORTAL:
        raise HTTPException(status_code=400, detail="Desfecho inválido")
    _validar_natureza_motivo(db, natureza_id=data.natureza_id, motivo_id=data.motivo_id)
    desc = (data.descricao_curta or "").strip() or None
    if desc and len(desc) > 500:
        raise HTTPException(status_code=400, detail="Descrição curta excede 500 caracteres")
    row = PortalChatDemanda(
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
        db.query(PortalChatDemanda)
        .options(
            joinedload(PortalChatDemanda.natureza),
            joinedload(PortalChatDemanda.motivo),
            joinedload(PortalChatDemanda.atendente),
        )
        .filter(PortalChatDemanda.id == row.id)
        .first()
    )


def listar_demandas_chat(db: Session, chat_id: int) -> list[PortalChatDemandaRead]:
    rows = (
        db.query(PortalChatDemanda)
        .options(
            joinedload(PortalChatDemanda.natureza),
            joinedload(PortalChatDemanda.motivo),
            joinedload(PortalChatDemanda.atendente),
        )
        .filter(PortalChatDemanda.chat_id == chat_id)
        .order_by(PortalChatDemanda.created_at.asc(), PortalChatDemanda.id.asc())
        .all()
    )
    return [demanda_para_read(r) for r in rows]


def atualizar_demanda_chat(
    db: Session,
    chat: PortalChat,
    row: PortalChatDemanda,
    data: PortalChatDemandaUpdate,
    *,
    atendente: Atendente,
) -> PortalChatDemanda:
    if chat.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Edite demandas apenas em chats em atendimento")
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
        db.query(PortalChatDemanda)
        .options(
            joinedload(PortalChatDemanda.natureza),
            joinedload(PortalChatDemanda.motivo),
            joinedload(PortalChatDemanda.atendente),
        )
        .filter(PortalChatDemanda.id == row.id)
        .first()
    )
    assert refreshed is not None
    return refreshed
