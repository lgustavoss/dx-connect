from __future__ import annotations

import io
import uuid
from pathlib import Path

from app.config import settings

_MIME_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

# Quão "branco" um pixel precisa ser para contar como margem (0–255).
_LIMIAR_BRANCO = 248
# Margem mínima mantida após o crop (px).
_PADDING_CROP = 4


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


def aparar_espaco_branco(data: bytes) -> bytes | None:
    """Remove margens brancas/transparentes ao redor da logo. Retorna PNG ou None se falhar."""
    if not data:
        return None
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return None

    rgba = img.convert("RGBA")
    alpha = rgba.split()[3]
    rgb = rgba.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    diff_l = diff.convert("L")
    mask = ImageChops.multiply(
        diff_l.point(lambda p: 255 if p > (255 - _LIMIAR_BRANCO) else 0),
        alpha,
    )
    bbox = mask.getbbox()
    if not bbox:
        bbox = alpha.getbbox()
    if not bbox:
        return None

    left, top, right, bottom = bbox
    pad = _PADDING_CROP
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(rgba.width, right + pad)
    bottom = min(rgba.height, bottom + pad)
    cropped = rgba.crop((left, top, right, bottom))

    if cropped.size == rgba.size:
        return None

    out = io.BytesIO()
    cropped.save(out, format="PNG", optimize=True)
    return out.getvalue()


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

    trimmed = aparar_espaco_branco(data)
    if trimmed and len(trimmed) <= settings.SYSTEM_LOGO_MAX_BYTES:
        data = trimmed
        mt = "image/png"
        ext = ".png"

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
