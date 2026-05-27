from __future__ import annotations

import uuid
from pathlib import Path

from app.config import settings

_MIME_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def diretorio_logo() -> Path:
    p = Path(settings.SYSTEM_LOGO_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def extensao_para_mimetype(mimetype: str | None) -> str | None:
    if not mimetype:
        return None
    m = mimetype.split(";", 1)[0].strip().lower()
    return _MIME_EXT.get(m)


def gravar_logo_bytes(data: bytes, mimetype: str | None) -> tuple[str, str] | None:
    """
    Grava o logo no diretório dedicado.
    Retorna (filename, mimetype_normalizado) ou None se inválido.
    """
    if len(data) == 0:
        return None
    if len(data) > settings.SYSTEM_LOGO_MAX_BYTES:
        return None
    if not mimetype:
        return None
    mt = mimetype.split(";", 1)[0].strip().lower()
    ext = extensao_para_mimetype(mt)
    if not ext:
        return None
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_logo() / name
    try:
        path.write_bytes(data)
    except OSError:
        return None
    return name, mt


def caminho_absoluto_logo(nome: str | None) -> Path | None:
    if not nome or not str(nome).strip():
        return None
    base = diretorio_logo()
    p = (base / str(nome).strip()).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def apagar_logo(nome: str | None) -> None:
    p = caminho_absoluto_logo(nome)
    if not p:
        return
    try:
        p.unlink(missing_ok=True)
    except OSError:
        return
