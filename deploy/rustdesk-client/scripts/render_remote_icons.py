#!/usr/bin/env python3
"""Gera icones do cliente Windows a partir da arte oficial de Acesso Remoto.

Fonte padrao: branding/icon-source-official.png
- tamanhos grandes: arte completa (com wordmark)
- 16/32/48/tray: recorte do mark (personagem + setas), sem texto
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

BRANDING = Path(__file__).resolve().parent.parent / "branding"
DEFAULT_SOURCE = BRANDING / "icon-source-official.png"


def _to_rgba_transparent(im: Image.Image, white_threshold: int = 248) -> Image.Image:
    """Converte fundo quase branco em transparencia."""
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]  # type: ignore[misc]
            if r >= white_threshold and g >= white_threshold and b >= white_threshold:
                px[x, y] = (r, g, b, 0)  # type: ignore[index]
    return rgba


def _content_bbox(im: Image.Image, alpha_min: int = 8) -> tuple[int, int, int, int]:
    """Bounding box do conteudo opaco."""
    alpha = im.split()[-1]
    bbox = alpha.point(lambda p: 255 if p > alpha_min else 0).getbbox()
    if not bbox:
        return (0, 0, im.width, im.height)
    return bbox


def _crop_pad_square(im: Image.Image, pad_ratio: float = 0.06) -> Image.Image:
    left, top, right, bottom = _content_bbox(im)
    crop = im.crop((left, top, right, bottom))
    side = max(crop.width, crop.height)
    pad = int(round(side * pad_ratio))
    canvas_side = side + 2 * pad
    out = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
    ox = (canvas_side - crop.width) // 2
    oy = (canvas_side - crop.height) // 2
    out.paste(crop, (ox, oy), crop)
    return out


def _mark_without_text(im: Image.Image) -> Image.Image:
    """Recorta a metade superior do conteudo (ilustracao), descartando o wordmark."""
    left, top, right, bottom = _content_bbox(im)
    height = bottom - top
    # wordmark ocupa ~25–35% inferior da arte
    cut = top + int(height * 0.68)
    crop = im.crop((left, top, right, cut))
    return _crop_pad_square(crop, pad_ratio=0.08)


def _fit_square(im: Image.Image, size: int) -> Image.Image:
    fitted = im.copy()
    fitted.thumbnail((size, size), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ox = (size - fitted.width) // 2
    oy = (size - fitted.height) // 2
    out.paste(fitted, (ox, oy), fitted)
    if size <= 48:
        # leve sharpen ajuda leitura em taskbar
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=120, threshold=2))
    return out


def write_branding(out_dir: Path, source: Path = DEFAULT_SOURCE) -> None:
    if not source.is_file():
        raise SystemExit(f"Arte fonte nao encontrada: {source}")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw = Image.open(source)
    rgba = _to_rgba_transparent(raw)
    full = _crop_pad_square(rgba, pad_ratio=0.04)
    mark = _mark_without_text(rgba)

    full.save(out_dir / "icon-source-1024.png")
    # manter copia canonica se veio de outro caminho
    if source.resolve() != (out_dir / "icon-source-official.png").resolve():
        rgba.convert("RGB").save(out_dir / "icon-source-official.png")

    # grandes: arte completa; pequenos: so o mark
    mapping = {
        "deskrudder-16.png": (mark, 16),
        "deskrudder-32.png": (mark, 32),
        "deskrudder-48.png": (mark, 48),
        "deskrudder-64.png": (mark, 64),
        "deskrudder-128.png": (full, 128),
        "deskrudder-256.png": (full, 256),
        # Painel host (Sciter): mark nitido, sem wordmark duplicado
        "ui-logo-256.png": (mark, 256),
        "ui-logo-512.png": (mark, 512),
        "32x32.png": (mark, 32),
        "128x128.png": (full, 128),
        "128x128@2x.png": (full, 128),
        "icon.png": (full, 256),
    }
    rendered: dict[tuple[int, str], Image.Image] = {}
    for name, (base, size) in mapping.items():
        key = (size, "mark" if base is mark else "full")
        if key not in rendered:
            rendered[key] = _fit_square(base, size)
        rendered[key].save(out_dir / name)

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    # ICO: misturar mark nos pequenos e full nos grandes
    frames = []
    for w, h in ico_sizes:
        base = mark if w <= 64 else full
        frames.append(_fit_square(base, w))
    frames[-1].save(
        out_dir / "icon.ico",
        format="ICO",
        sizes=ico_sizes,
        append_images=frames[:-1],
    )
    _fit_square(mark, 32).save(out_dir / "tray-icon.ico", format="ICO", sizes=[(32, 32)])
    print(f">> icones gerados de {source.name} em {out_dir}")


def main() -> int:
    write_branding(BRANDING, DEFAULT_SOURCE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
