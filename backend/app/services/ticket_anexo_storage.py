"""Gravação local de anexos de tickets (UploadFile / bytes)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config import settings


def _normalizar_mimetype(mime: str | None) -> str | None:
    if not mime:
        return None
    return mime.split(";")[0].strip().lower() or None


def _sanitizar_nome_ficheiro(name: str | None) -> str:
    raw = (name or "arquivo").strip() or "arquivo"
    # Mantém só caracteres “seguros” para exibição; não usado no path do disco.
    safe = "".join(ch for ch in raw if ch.isalnum() or ch in "._- ()[]{}@+")
    safe = safe.strip(" .") or "arquivo"
    return safe[:200]


_BLOCK_MIME = {
    "application/x-msdownload",
    "application/x-dosexec",
    "application/x-sh",
    "application/x-bat",
    "application/x-msdos-program",
}

_BLOCK_EXT = {
    ".exe",
    ".dll",
    ".msi",
    ".bat",
    ".cmd",
    ".com",
    ".ps1",
    ".vbs",
    ".js",
    ".jar",
    ".sh",
}


def validar_upload(nome_original: str | None, content_type: str | None, tamanho_bytes: int) -> tuple[str, str | None]:
    """Valida e normaliza metadados. Retorna (nome_original_sanitizado, mimetype_normalizado)."""
    if tamanho_bytes <= 0:
        raise ValueError("Arquivo vazio.")
    if tamanho_bytes > settings.TICKET_ANEXOS_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido.")
    nome = _sanitizar_nome_ficheiro(nome_original)
    ext = Path(nome).suffix.lower()
    mime = _normalizar_mimetype(content_type)
    if ext in _BLOCK_EXT:
        raise ValueError("Tipo de arquivo não permitido.")
    if mime and mime in _BLOCK_MIME:
        raise ValueError("Tipo de arquivo não permitido.")
    return nome, mime


def diretorio_anexos() -> Path:
    p = Path(settings.TICKET_ANEXOS_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def _extensao_para_mimetype(mimetype: str | None, fallback_nome: str) -> str:
    # Preferir a extensão do nome original quando existir (mantém UX em downloads).
    ext = Path(fallback_nome).suffix
    if ext and len(ext) <= 10:
        return ext
    m = _normalizar_mimetype(mimetype)
    if not m:
        return ".bin"
    if m == "application/pdf":
        return ".pdf"
    if m.startswith("image/"):
        return ".img"
    if m.startswith("audio/"):
        return ".audio"
    if m.startswith("video/"):
        return ".video"
    if m.startswith("text/"):
        return ".txt"
    return ".bin"


def gravar_bytes_em_disco(data: bytes, *, mimetype: str | None, nome_original: str) -> str:
    """Grava bytes no diretório de anexos. Devolve basename (storage_key)."""
    if len(data) == 0:
        raise ValueError("Arquivo vazio.")
    if len(data) > settings.TICKET_ANEXOS_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido.")
    ext = _extensao_para_mimetype(mimetype, nome_original)
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_anexos() / name
    path.write_bytes(data)
    return name


def caminho_absoluto_arquivo(storage_key: str | None) -> Path | None:
    if not storage_key or not str(storage_key).strip():
        return None
    base = diretorio_anexos()
    # Evita traversal; só aceita basenames simples.
    s = str(storage_key).strip()
    if re.search(r"[\\/]", s):
        return None
    p = (base / s).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None

