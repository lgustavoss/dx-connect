"""Redefinição de senha por e-mail (instância single-tenant)."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.atendente import Atendente
from app.models.password_reset_token import PasswordResetToken
from app.services.email_send_sistema import enviar_mensagem_texto_sistema

logger = logging.getLogger(__name__)

MSG_SOLICITACAO_OK = (
    "Se o e-mail estiver cadastrado e ativo, você receberá instruções para redefinir a senha em breve."
)
MSG_LINK_INVALIDO = "Link inválido ou expirado. Solicite uma nova redefinição de senha."


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _public_app_origin() -> str:
    host = (settings.CLIENT_APP_HOST or "").strip()
    if host:
        host = host.removeprefix("https://").removeprefix("http://").split("/")[0]
        proto = "https" if settings.is_production else "http"
        return f"{proto}://{host}"
    if not settings.is_production:
        return "http://localhost:5173"
    base = (settings.CONNECT_APP_BASE_DOMAIN or "").strip()
    if base:
        return f"https://{base}"
    return "http://localhost:5173"


def build_reset_link(raw_token: str) -> str:
    origin = _public_app_origin().rstrip("/")
    return f"{origin}/redefinir-senha?token={raw_token}"


def _invalidate_pending_tokens(db: Session, atendente_id: int) -> None:
    now = datetime.now(timezone.utc)
    pending = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.atendente_id == atendente_id,
            PasswordResetToken.used_at.is_(None),
        )
        .all()
    )
    for row in pending:
        if _as_utc_aware(row.expires_at) > now:
            row.used_at = now


def solicitar_redefinicao(db: Session, email: str) -> str:
    """
    Cria token e envia e-mail se existir atendente ativo.
    Sempre retorna a mesma mensagem genérica (não revela existência do e-mail).
    """
    email_norm = email.strip().lower()
    atendente = (
        db.query(Atendente)
        .filter(
            func.lower(Atendente.email) == email_norm,
            Atendente.ativo.is_(True),
        )
        .first()
    )
    if not atendente:
        return MSG_SOLICITACAO_OK

    raw = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    _invalidate_pending_tokens(db, atendente.id)
    row = PasswordResetToken(
        atendente_id=atendente.id,
        token_hash=_hash_token(raw),
        expires_at=expires,
    )
    db.add(row)
    db.commit()

    link = build_reset_link(raw)
    nome = (atendente.nome or "").strip() or "usuário"
    subject = "Redefinição de senha — DX Connect"
    body = (
        f"Olá, {nome},\n\n"
        "Recebemos um pedido para redefinir a senha da sua conta no DX Connect.\n\n"
        f"Acesse o link abaixo (válido por {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hora(s)):\n"
        f"{link}\n\n"
        "Se você não solicitou esta alteração, ignore este e-mail.\n\n"
        "— Equipe DX Connect"
    )
    try:
        enviar_mensagem_texto_sistema(db, to_addr=atendente.email, subject=subject, body=body)
    except ValueError as e:
        logger.warning("Redefinição de senha: envio de e-mail indisponível (%s)", e)
    except Exception:
        logger.exception("Redefinição de senha: falha ao enviar e-mail para atendente_id=%s", atendente.id)
    return MSG_SOLICITACAO_OK


def redefinir_senha_com_token(db: Session, raw_token: str, senha_nova: str) -> None:
    """Aplica nova senha ou levanta ValueError com mensagem para o cliente."""
    from app.core.security import hash_senha, verificar_senha

    token = raw_token.strip()
    if not token:
        raise ValueError(MSG_LINK_INVALIDO)

    now = datetime.now(timezone.utc)
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == _hash_token(token))
        .first()
    )
    if not row or row.used_at is not None or _as_utc_aware(row.expires_at) <= now:
        raise ValueError(MSG_LINK_INVALIDO)

    atendente = db.query(Atendente).filter(Atendente.id == row.atendente_id, Atendente.ativo.is_(True)).first()
    if not atendente:
        raise ValueError(MSG_LINK_INVALIDO)

    if verificar_senha(senha_nova, atendente.senha_hash):
        raise ValueError("A nova senha deve ser diferente da senha atual.")

    atendente.senha_hash = hash_senha(senha_nova)
    atendente.must_change_password = False
    row.used_at = now
    _invalidate_pending_tokens(db, atendente.id)
    db.commit()
