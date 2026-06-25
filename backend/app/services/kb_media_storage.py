from __future__ import annotations

import uuid
from pathlib import Path

from app.config import settings

_MIME_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def diretorio_kb_media() -> Path:
    p = Path(settings.KB_MEDIA_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def extensao_para_mimetype(mimetype: str | None) -> str | None:
    if not mimetype:
        return None
    m = mimetype.split(";", 1)[0].strip().lower()
    return _MIME_EXT.get(m)


def gravar_imagem_bytes(data: bytes, mimetype: str | None) -> tuple[str, str] | None:
    if len(data) == 0 or len(data) > settings.KB_MEDIA_MAX_BYTES:
        return None
    if not mimetype:
        return None
    mt = mimetype.split(";", 1)[0].strip().lower()
    ext = extensao_para_mimetype(mt)
    if not ext:
        return None
    name = f"{uuid.uuid4().hex}{ext}"
    path = diretorio_kb_media() / name
    try:
        path.write_bytes(data)
    except OSError:
        return None
    return name, mt


def caminho_absoluto_imagem(nome: str | None) -> Path | None:
    if not nome or not str(nome).strip():
        return None
    base = diretorio_kb_media()
    p = (base / str(nome).strip()).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None
