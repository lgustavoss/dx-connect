from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    """
    Deriva uma chave Fernet a partir do SECRET_KEY do backend.

    Requisitos:
    - Não expor segredos via GET.
    - Evitar armazenamento em claro no banco.
    """

    raw = (settings.SECRET_KEY or "").encode("utf-8")
    # Fernet exige 32 bytes urlsafe base64.
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_str(value: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValueError("Segredo vazio.")
    return _fernet().encrypt(v.encode("utf-8")).decode("ascii")


def decrypt_str(value_enc: str) -> str:
    v = (value_enc or "").strip()
    if not v:
        raise ValueError("Segredo vazio.")
    try:
        return _fernet().decrypt(v.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Segredo inválido ou chave alterada.") from e

