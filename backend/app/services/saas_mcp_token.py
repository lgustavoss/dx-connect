"""Token Cursor por conta saas_ops (#915)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.models.atendente import Atendente

TOKEN_PREFIX = "drmcp_"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def hash_mcp_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def gerar_token_plaintext() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def estado(ops: Atendente) -> dict:
    return {
        "configurado": bool((ops.mcp_token_hash or "").strip()),
        "gerado_em": ops.mcp_token_gerado_em,
    }


def gerar(db: Session, ops: Atendente) -> str:
    token = gerar_token_plaintext()
    ops.mcp_token_hash = hash_mcp_token(token)
    ops.mcp_token_gerado_em = _agora()
    db.add(ops)
    registrar_audit(db, "atendente", ops.id, "gerar_mcp_token", ops.id)
    db.flush()
    return token


def revogar(db: Session, ops: Atendente) -> None:
    ops.mcp_token_hash = None
    ops.mcp_token_gerado_em = None
    db.add(ops)
    registrar_audit(db, "atendente", ops.id, "revogar_mcp_token", ops.id)
    db.flush()


def resolver_ops_mcp_token(db: Session, raw: str) -> Atendente | None:
    """Devolve o saas_ops dono do token, ou None se o Bearer não for um token pessoal."""
    token = (raw or "").strip()
    if not token:
        return None
    digest = hash_mcp_token(token)
    row = db.query(Atendente).filter(Atendente.mcp_token_hash == digest).first()
    if row is None:
        return None
    if row.role != "saas_ops" or not row.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")
    return row
