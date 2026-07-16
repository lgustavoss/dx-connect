"""Presença online de atendentes — admin (#546 / #547)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import exigir_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.presenca import PresencaOnlineLista
from app.services import presenca as presenca_service

router = APIRouter(prefix="/presenca", tags=["presenca"])


@router.get("/online", response_model=PresencaOnlineLista)
async def listar_online(
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return await presenca_service.listar_online(db, tenant_id=admin.tenant_id)


@router.post("/online/{atendente_id}/forcar-saida", status_code=status.HTTP_204_NO_CONTENT)
async def forcar_saida(
    atendente_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    """Encerra a sessão do atendente (invalida tokens) e remove da lista online."""
    await presenca_service.forcar_saida(db, admin=admin, alvo_id=atendente_id)
    return None
