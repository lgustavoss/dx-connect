"""
Janela configurável antes de enviar e-mail ao cliente (mensagem pública #140).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.services.system_email_config import get_singleton_email_settings

# Valores permitidos na UI de configurações (admin).
GRACE_OPCOES: list[tuple[int, str]] = [
    (0, "Envio imediato"),
    (30, "30 segundos"),
    (60, "1 minuto"),
    (120, "2 minutos"),
    (180, "3 minutos"),
    (300, "5 minutos"),
]

_GRACE_PERMITIDOS = {s for s, _ in GRACE_OPCOES}


def grace_opcoes_dict() -> list[dict[str, int | str]]:
    return [{"segundos": s, "rotulo": r} for s, r in GRACE_OPCOES]


def grace_padrao_segundos() -> int:
    return max(0, int(settings.TICKET_MENSAGEM_EMAIL_GRACE_SECONDS))


def validar_grace_seconds(valor: int) -> int:
    v = int(valor)
    if v not in _GRACE_PERMITIDOS:
        permitidos = ", ".join(str(s) for s in sorted(_GRACE_PERMITIDOS))
        raise ValueError(f"Tempo de espera inválido. Opções permitidas (segundos): {permitidos}.")
    return v


def resolver_grace_seconds(db: Session) -> int:
    """Preferência na BD (email_settings); fallback para variável de ambiente."""
    row = get_singleton_email_settings(db)
    if row is not None and row.ticket_mensagem_email_grace_seconds is not None:
        try:
            return validar_grace_seconds(row.ticket_mensagem_email_grace_seconds)
        except ValueError:
            pass
    return grace_padrao_segundos()
