"""Gravação local de mídia do chat interno."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config import settings
from app.services.ticket_anexo_storage import validar_upload


def diretorio_midia() -> Path:
    p = Path(settings.CHAT_INTERNO_MEDIA_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def gravar_bytes_em_disco(data: bytes, *, mimetype: str | None, nome_original: str) -> tuple[str, str, str | None]:
    """Grava bytes no diretório de mídia. Devolve (storage_key, nome_original, mimetype)."""
    if len(data) > settings.CHAT_INTERNO_MEDIA_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido.")
    nome, mime = validar_upload(nome_original, mimetype, len(data))
    ext = Path(nome).suffix
    if not ext or len(ext) > 10:
        ext = ".bin"
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_midia() / name
    path.write_bytes(data)
    return name, nome, mime


def caminho_absoluto_arquivo(storage_key: str | None) -> Path | None:
    if not storage_key or not str(storage_key).strip():
        return None
    base = diretorio_midia()
    s = str(storage_key).strip()
    if re.search(r"[\\/]", s):
        return None
    p = (base / s).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None
