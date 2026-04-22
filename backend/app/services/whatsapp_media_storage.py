"""Gravação local de ficheiros de mídia recebidos via Evolution (base64)."""

from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path

from app.config import settings

# Extensões comuns (mimetype pode vir com codecs=opus etc.)
_MIME_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
    "application/pdf": ".pdf",
}


def _normalizar_mimetype(mime: str | None) -> str | None:
    if not mime:
        return None
    return mime.split(";")[0].strip().lower() or None


def extensao_para_mimetype(mimetype: str | None) -> str:
    m = _normalizar_mimetype(mimetype)
    if not m:
        return ".bin"
    if m in _MIME_EXT:
        return _MIME_EXT[m]
    # fallback por prefixo
    if m.startswith("image/"):
        return ".img"
    if m.startswith("audio/"):
        return ".audio"
    if m.startswith("video/"):
        return ".mp4"
    return ".bin"


def _strip_data_url_prefix(b64: str) -> str:
    s = b64.strip()
    if s.startswith("data:") and "base64," in s:
        return s.split("base64,", 1)[-1]
    return s


def diretorio_midia() -> Path:
    p = Path(settings.WHATSAPP_MEDIA_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def gravar_bytes_em_disco(data: bytes, mimetype: str | None) -> str | None:
    """Grava bytes brutos (ex.: upload outbound). Devolve basename ou None."""
    if len(data) > settings.WHATSAPP_MEDIA_MAX_BYTES:
        return None
    if len(data) == 0:
        return None
    ext = extensao_para_mimetype(mimetype)
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_midia() / name
    try:
        path.write_bytes(data)
    except OSError:
        return None
    return name


def gravar_base64_em_disco(b64: str, mimetype: str | None) -> str | None:
    """
    Grava bytes em disco. Devolve apenas o nome do ficheiro (basename) ou None se falhar/limite.
    """
    raw_b64 = _strip_data_url_prefix(b64)
    raw_b64 = re.sub(r"\s+", "", raw_b64)
    try:
        data = base64.b64decode(raw_b64, validate=False)
    except Exception:
        return None
    if len(data) > settings.WHATSAPP_MEDIA_MAX_BYTES:
        return None
    if len(data) == 0:
        return None
    ext = extensao_para_mimetype(mimetype)
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_midia() / name
    try:
        path.write_bytes(data)
    except OSError:
        return None
    return name


def caminho_absoluto_arquivo(nome: str | None) -> Path | None:
    if not nome or not str(nome).strip():
        return None
    base = diretorio_midia()
    p = (base / nome).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None
