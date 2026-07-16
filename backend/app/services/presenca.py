"""Presença de atendentes online — deriva do hub SSE (#546)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.schemas.presenca import PresencaOnlineItem, PresencaOnlineLista, PresencaSetorResumo
from app.services.realtime_hub import hub


async def listar_online(db: Session, *, tenant_id: int) -> PresencaOnlineLista:
    """Lista atendentes ativos do tenant com conexão SSE no hub."""
    online = await hub.list_online()
    if not online:
        return PresencaOnlineLista(itens=[])

    por_id = {aid: desde for aid, desde in online}
    rows = (
        db.query(Atendente)
        .options(joinedload(Atendente.setores))
        .filter(
            Atendente.tenant_id == tenant_id,
            Atendente.id.in_(list(por_id.keys())),
            Atendente.ativo.is_(True),
        )
        .order_by(Atendente.nome.asc(), Atendente.id.asc())
        .all()
    )

    itens: list[PresencaOnlineItem] = []
    for a in rows:
        desde = por_id[a.id]
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
