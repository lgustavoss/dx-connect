"""Conta do ops no control-plane — token Cursor (#915)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth import exigir_saas_ops
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.saas_mcp_token import SaasMcpTokenEstado, SaasMcpTokenGerado
from app.services import saas_mcp_token as mcp_token

router = APIRouter(prefix="/saas/me", tags=["saas-ops-conta"])


def _exigir_control_plane() -> None:
    if not settings.SAAS_CONTROL_PLANE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Painel SaaS não disponível nesta instância",
        )


@router.get("/mcp-token", response_model=SaasMcpTokenEstado)
def obter_estado_mcp_token(
    _: None = Depends(_exigir_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
):
    """Estado do token Cursor desta conta. Nunca devolve o segredo."""
    return SaasMcpTokenEstado.model_validate(mcp_token.estado(ops))


@router.post("/mcp-token", response_model=SaasMcpTokenGerado)
def gerar_mcp_token(
    db: Session = Depends(get_db),
    _: None = Depends(_exigir_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
):
    """Gera ou regenera o token. O plaintext só sai nesta resposta."""
    token = mcp_token.gerar(db, ops)
    db.commit()
    db.refresh(ops)
    return SaasMcpTokenGerado(token=token, **mcp_token.estado(ops))


@router.delete("/mcp-token", response_model=SaasMcpTokenEstado)
def revogar_mcp_token(
    db: Session = Depends(get_db),
    _: None = Depends(_exigir_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
):
    mcp_token.revogar(db, ops)
    db.commit()
    db.refresh(ops)
    return SaasMcpTokenEstado.model_validate(mcp_token.estado(ops))
