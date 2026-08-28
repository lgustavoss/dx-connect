"""Storage de anexos de justificativa de ponto (#977)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config import settings
from app.services.ticket_anexo_storage import validar_upload as _validar_ticket

# Allowlist mais restrita para RH: imagem + PDF
_ALLOW_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic"}
_ALLOW_MIME_PREFIX = ("image/",)
_ALLOW_MIME = {"application/pdf"}


def validar_anexo_justificativa(
    nome_original: str | None, content_type: str | None, tamanho_bytes: int
) -> tuple[str, str | None]:
    if tamanho_bytes > settings.PONTO_JUSTIFICATIVA_ANEXOS_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido (25 MB).")
    nome, mime = _validar_ticket(nome_original, content_type, tamanho_bytes)
    ext = Path(nome).suffix.lower()
    if ext not in _ALLOW_EXT:
        raise ValueError("Anexo deve ser imagem ou PDF.")
    if mime and not (mime in _ALLOW_MIME or mime.startswith(_ALLOW_MIME_PREFIX)):
        raise ValueError("Anexo deve ser imagem ou PDF.")
    return nome, mime


def diretorio_anexos() -> Path:
    p = Path(settings.PONTO_JUSTIFICATIVA_ANEXOS_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def gravar_bytes(data: bytes, *, mimetype: str | None, nome_original: str) -> str:
    if len(data) == 0:
        raise ValueError("Arquivo vazio.")
    if len(data) > settings.PONTO_JUSTIFICATIVA_ANEXOS_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido (25 MB).")
    ext = Path(nome_original).suffix.lower()
    if ext not in _ALLOW_EXT:
        ext = ".bin"
        if mimetype == "application/pdf":
            ext = ".pdf"
        elif mimetype and mimetype.startswith("image/"):
            ext = ".img"
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_anexos() / name
    path.write_bytes(data)
    return name


def caminho_absoluto(storage_key: str | None) -> Path | None:
    if not storage_key or not str(storage_key).strip():
        return None
    base = diretorio_anexos()
    s = str(storage_key).strip()
    if re.search(r"[\\/]", s):
        return None
    p = (base / s).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None
