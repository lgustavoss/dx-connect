"""Gravação local de PDFs de boleto/NFS-e do faturamento (#326)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config import settings


def _normalizar_mimetype(mime: str | None) -> str | None:
    if not mime:
        return None
    return mime.split(";")[0].strip().lower() or None


def _sanitizar_nome(name: str | None) -> str:
    raw = (name or "arquivo").strip() or "arquivo"
    safe = "".join(ch for ch in raw if ch.isalnum() or ch in "._- ()[]{}@+")
    safe = safe.strip(" .") or "arquivo"
    return safe[:200]


_PDF_MIME = {"application/pdf"}
_XML_MIME = {"application/xml", "text/xml", "application/xhtml+xml"}


def validar_upload(
    nome_original: str | None,
    content_type: str | None,
    tamanho_bytes: int,
    *,
    tipo: str,
) -> tuple[str, str | None]:
    if tamanho_bytes <= 0:
        raise ValueError("Arquivo vazio.")
    if tamanho_bytes > settings.FATURAMENTO_ANEXOS_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido.")
    nome = _sanitizar_nome(nome_original)
    ext = Path(nome).suffix.lower()
    mime = _normalizar_mimetype(content_type)
    if tipo in ("boleto", "nfse_pdf"):
        if ext and ext != ".pdf":
            raise ValueError("Envie um PDF.")
        if mime and mime not in _PDF_MIME:
            raise ValueError("Envie um PDF.")
        if not mime:
            mime = "application/pdf"
    elif tipo == "nfse_xml":
        if ext and ext not in {".xml", ".txt"}:
            raise ValueError("Envie o XML da nota.")
        if mime and mime not in _XML_MIME:
            raise ValueError("Envie o XML da nota.")
        if not mime:
            mime = "application/xml"
    else:
        raise ValueError("Tipo de documento inválido.")
    return nome, mime


def diretorio_anexos() -> Path:
    p = Path(settings.FATURAMENTO_ANEXOS_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def gravar_bytes_em_disco(data: bytes, *, mimetype: str | None, nome_original: str) -> str:
    if len(data) == 0:
        raise ValueError("Arquivo vazio.")
    if len(data) > settings.FATURAMENTO_ANEXOS_MAX_BYTES:
        raise ValueError("Arquivo excede o tamanho máximo permitido.")
    ext = Path(nome_original).suffix
    if not ext or len(ext) > 10:
        mime = _normalizar_mimetype(mimetype)
        if mime == "application/pdf":
            ext = ".pdf"
        elif mime in _XML_MIME:
            ext = ".xml"
        else:
            ext = ".bin"
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_anexos() / name
    path.write_bytes(data)
    return name


def caminho_absoluto_arquivo(storage_key: str | None) -> Path | None:
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


def apagar_arquivo(storage_key: str | None) -> None:
    p = caminho_absoluto_arquivo(storage_key)
    if p is None:
        return
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass
