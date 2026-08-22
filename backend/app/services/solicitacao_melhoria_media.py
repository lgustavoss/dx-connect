"""Mídia das solicitações de melhoria (prints no texto + anexos)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config import settings

PAPEL_INLINE = "inline"
PAPEL_ANEXO = "anexo"

_MIME_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "application/pdf": ".pdf",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}

INLINE_MIMES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})
ANEXO_MIMES = INLINE_MIMES | frozenset(
    {"application/pdf", "video/mp4", "video/webm", "video/quicktime"}
)


def _normalizar_mime(mime: str | None) -> str | None:
    if not mime:
        return None
    return mime.split(";", 1)[0].strip().lower() or None


def sanitizar_nome(name: str | None) -> str:
    raw = (name or "arquivo").strip() or "arquivo"
    safe = "".join(ch for ch in raw if ch.isalnum() or ch in "._- ()[]{}@+")
    return (safe.strip(" .") or "arquivo")[:200]


def diretorio_media() -> Path:
    p = Path(settings.SOLICITACAO_MEDIA_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def validar_upload(
    nome_original: str | None,
    content_type: str | None,
    tamanho_bytes: int,
    *,
    papel: str,
) -> tuple[str, str]:
    if tamanho_bytes <= 0:
        raise ValueError("Arquivo vazio.")
    if tamanho_bytes > settings.SOLICITACAO_MEDIA_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido (25 MB).")
    mime = _normalizar_mime(content_type)
    nome = sanitizar_nome(nome_original)
    ext = Path(nome).suffix.lower()
    mime_por_ext = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".pdf": "application/pdf",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    }
    if papel == PAPEL_INLINE:
        if mime not in INLINE_MIMES:
            mime = mime_por_ext.get(ext)
        if mime not in INLINE_MIMES:
            raise ValueError("No texto só é possível inserir imagens (PNG, JPEG, WebP ou GIF).")
    else:
        if mime not in ANEXO_MIMES:
            mime = mime_por_ext.get(ext)
        if mime not in ANEXO_MIMES:
            raise ValueError("Anexo permitido: imagem, PDF ou vídeo (MP4/WebM).")
    return nome, mime


_STORAGE_KEY_RE = re.compile(
    r"^[a-fA-F0-9]{32}\.(png|jpg|jpeg|webp|gif|pdf|mp4|webm|mov)$"
)


def validar_storage_key(storage_key: str | None) -> str:
    s = (storage_key or "").strip()
    if not _STORAGE_KEY_RE.match(s):
        raise ValueError("Chave de ficheiro inválida.")
    return s


def gravar_bytes(data: bytes, *, mimetype: str, nome_original: str) -> str:
    if len(data) == 0:
        raise ValueError("Arquivo vazio.")
    if len(data) > settings.SOLICITACAO_MEDIA_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido (25 MB).")
    ext = _MIME_EXT.get(mimetype) or Path(nome_original).suffix.lower() or ".bin"
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_media() / name
    path.write_bytes(data)
    return name


def gravar_com_chave(data: bytes, storage_key: str) -> str:
    """Grava no disco com a chave da instância (markdown continua a resolver)."""
    key = validar_storage_key(storage_key)
    if len(data) == 0:
        raise ValueError("Arquivo vazio.")
    if len(data) > settings.SOLICITACAO_MEDIA_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido (25 MB).")
    path = diretorio_media() / key
    if path.is_file() and path.stat().st_size == len(data):
        return key
    path.write_bytes(data)
    return key


def caminho_absoluto(storage_key: str | None) -> Path | None:
    if not storage_key or not str(storage_key).strip():
        return None
    s = str(storage_key).strip()
    if re.search(r"[\\/]", s):
        return None
    base = diretorio_media()
    p = (base / s).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def media_public_path(storage_key: str) -> str:
    return f"/v1/solicitacoes-melhoria/media/{storage_key}"
