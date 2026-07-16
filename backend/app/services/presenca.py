"""Presença de atendentes online — heartbeat no DB (#546+ multi-worker)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.schemas.presenca import PresencaOnlineItem, PresencaOnlineLista, PresencaSetorResumo
from app.services.realtime_hub import publish_to_atendente

logger = logging.getLogger(__name__)

# SSE ping a cada 30s — offline após ~3 pings perdidos.
PRESENCA_TTL_SEC = 90


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _limite_online(agora: datetime | None = None) -> datetime:
    return (agora or _agora_utc()) - timedelta(seconds=PRESENCA_TTL_SEC)


def tocar_presenca(db: Session, atendente_id: int) -> None:
    """Atualiza heartbeat; reinicia `online_desde` se a sessão anterior expirou."""
    a = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if a is None:
        return
    agora = _agora_utc()
    limite = _limite_online(agora)
    hb = a.presenca_heartbeat_em
    if hb is not None and hb.tzinfo is None:
        hb = hb.replace(tzinfo=timezone.utc)
    if a.presenca_online_desde is None or hb is None or hb < limite:
        a.presenca_online_desde = agora
    a.presenca_heartbeat_em = agora
    db.add(a)


def limpar_presenca(db: Session, atendente_id: int) -> None:
    a = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if a is None:
        return
    a.presenca_online_desde = None
    a.presenca_heartbeat_em = None
    db.add(a)


async def listar_online(db: Session, *, tenant_id: int) -> PresencaOnlineLista:
    """Lista atendentes ativos do tenant com heartbeat recente."""
    limite = _limite_online()
    rows = (
        db.query(Atendente)
        .options(joinedload(Atendente.setores))
        .filter(
            Atendente.tenant_id == tenant_id,
            Atendente.ativo.is_(True),
            Atendente.presenca_heartbeat_em.isnot(None),
            Atendente.presenca_heartbeat_em >= limite,
        )
        .order_by(Atendente.nome.asc(), Atendente.id.asc())
        .all()
    )

    itens: list[PresencaOnlineItem] = []
    for a in rows:
        desde = a.presenca_online_desde or a.presenca_heartbeat_em
        if desde is None:
            continue
        if desde.tzinfo is None:
            desde = desde.replace(tzinfo=timezone.utc)
        itens.append(
            PresencaOnlineItem(
                atendente_id=a.id,
                nome=a.nome,
                email=a.email,
                role=a.role,
                online_desde=desde,
                setores=[PresencaSetorResumo(id=s.id, nome=s.nome) for s in sorted(a.setores, key=lambda x: x.nome)],
            )
        )
    return PresencaOnlineLista(itens=itens)


async def forcar_saida(db: Session, *, admin: Atendente, alvo_id: int) -> None:
    """Invalida tokens do alvo e remove presença; notifica via SSE se no mesmo worker."""
    alvo = (
        db.query(Atendente)
        .filter(Atendente.id == alvo_id, Atendente.tenant_id == admin.tenant_id)
        .first()
    )
    if alvo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    if not alvo.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Atendente já está inativo")

    alvo.token_version = int(getattr(alvo, "token_version", 0) or 0) + 1
    alvo.presenca_online_desde = None
    alvo.presenca_heartbeat_em = None
    db.add(alvo)
    db.commit()

    try:
        await publish_to_atendente(
            alvo.id,
            "sessao.encerrada",
            {"motivo": "forcada_por_admin", "admin_id": admin.id},
        )
    except Exception:
        logger.exception("Falha ao publicar sessao.encerrada para atendente %s", alvo.id)
