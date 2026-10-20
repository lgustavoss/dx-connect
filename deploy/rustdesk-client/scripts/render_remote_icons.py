#!/usr/bin/env python3
"""Gera icones do cliente Windows a partir da arte oficial de Acesso Remoto.

Fonte padrao: branding/icon-source-official.png

Preferivel: PNG com alpha real (export do Figma/Photoshop).
JPEG com xadrez de “transparencia” achatado e suportado de forma best-effort.

- tamanhos grandes: arte completa (com wordmark)
- 16/32/48/tray + ui-logo: mark (personagem + setas), sem texto
- ui-logo: placa opaca na cor do tema escuro do painel host
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

BRANDING = Path(__file__).resolve().parent.parent / "branding"
DEFAULT_SOURCE = BRANDING / "icon-source-official.png"
UI_DARK = (30, 30, 36)


def _to_rgba_transparent(im: Image.Image) -> Image.Image:
    """Remove fundo branco ou xadrez JPEG; preserva pele e brancos internos."""
    if im.mode == "RGBA":
        # Reusa alpha se ja parece util (cantos transparentes)
        a0 = im.getpixel((0, 0))[3]
        if a0 == 0:
            return im

    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()

    def chroma_warm_mn(x: int, y: int) -> tuple[int, int, int, int, int, int]:
        r, g, b = px[x, y]  # type: ignore[misc]
        mx, mn = max(r, g, b), min(r, g, b)
        return r, g, b, mx - mn, r - b, mn

    grey_chk = [[False] * w for _ in range(h)]
    bright = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            _r, _g, _b, ch, warm, mn = chroma_warm_mn(x, y)
            if ch <= 16 and warm <= 8 and 175 <= mn <= 235:
                grey_chk[y][x] = True
            if ch <= 16 and mn >= 240:
                bright[y][x] = True

    # Celula branca do xadrez: bright vizinha de cinza
    was_chk = [row[:] for row in grey_chk]
    for y in range(h):
        for x in range(w):
            if not bright[y][x]:
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and grey_chk[ny][nx]:
                    was_chk[y][x] = True
                    break

    # Protege blobs brancos internos (cursor / DELL)
    seen = [[False] * w for _ in range(h)]
    protect = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if seen[y][x] or not bright[y][x]:
                continue
            q: deque[tuple[int, int]] = deque([(x, y)])
            cells: list[tuple[int, int]] = []
            seen[y][x] = True
            touches = False
            chk_n = 0
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                if cx in (0, w - 1) or cy in (0, h - 1):
                    touches = True
                if was_chk[cy][cx]:
                    chk_n += 1
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and bright[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            if touches:
                continue
            if 300 <= len(cells) <= 8000 and chk_n / len(cells) < 0.25:
                for cx, cy in cells:
                    protect[cy][cx] = True

    border = [[False] * w for _ in range(h)]
    q = deque()

    def push(x: int, y: int) -> None:
        if border[y][x] or protect[y][x]:
            return
        _r, _g, _b, ch, warm, mn = chroma_warm_mn(x, y)
        if not (ch <= 18 and warm <= 10 and mn >= 175):
            return
        border[y][x] = True
        q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)
    while q:
        x, y = q.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                push(nx, ny)

    rgba = Image.new("RGBA", (w, h))
    out = rgba.load()
    alpha = [[255] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if (was_chk[y][x] and not protect[y][x]) or border[y][x]:
                alpha[y][x] = 0
            if protect[y][x]:
                alpha[y][x] = 255

    # Maior componente
    seen = [[False] * w for _ in range(h)]
    best: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if seen[y][x] or alpha[y][x] == 0:
                seen[y][x] = True
                continue
            q = deque([(x, y)])
            cells: list[tuple[int, int]] = []
            seen[y][x] = True
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx]:
                        if alpha[ny][nx] > 0:
                            seen[ny][nx] = True
                            q.append((nx, ny))
                        else:
                            seen[ny][nx] = True
            if len(cells) > len(best):
                best = cells
    keep = [[False] * w for _ in range(h)]
    for cx, cy in best:
        keep[cy][cx] = True
    for y in range(h):
        for x in range(w):
            if protect[y][x]:
                keep[y][x] = True

    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]  # type: ignore[misc]
            if keep[y][x] and alpha[y][x]:
                out[x, y] = (r, g, b, 255)  # type: ignore[index]
            else:
                out[x, y] = (0, 0, 0, 0)  # type: ignore[index]
    return rgba


def _content_bbox(im: Image.Image, alpha_min: int = 8) -> tuple[int, int, int, int]:
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
    left, top, right, bottom = _content_bbox(im)
    height = bottom - top
    cut = top + int(height * 0.82)
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
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=120, threshold=2))
    return out


def _opaque_ui_logo(mark: Image.Image, size: int) -> Image.Image:
    fitted = mark.copy()
    fitted.thumbnail((size, size), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (size, size), (*UI_DARK, 255))
    ox = (size - fitted.width) // 2
    oy = (size - fitted.height) // 2
    layer.paste(fitted, (ox, oy), fitted)
    rgb = layer.convert("RGB")
    px = rgb.load()
    for y in range(size):
        for x in range(size):
            r, g, b = px[x, y]  # type: ignore[misc]
            mx, mn = max(r, g, b), min(r, g, b)
            if mx - mn <= 16 and r - b <= 8 and 175 <= mn <= 235:
                px[x, y] = UI_DARK  # type: ignore[index]
    return rgb


def write_branding(out_dir: Path, source: Path = DEFAULT_SOURCE) -> None:
    if not source.is_file():
        raise SystemExit(f"Arte fonte nao encontrada: {source}")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw = Image.open(source)
    rgba = _to_rgba_transparent(raw)
    full = _crop_pad_square(rgba, pad_ratio=0.04)
    mark = _mark_without_text(rgba)

    full.save(out_dir / "icon-source-1024.png")
    rgba.save(out_dir / "icon-source-official.png")

    mapping = {
        "deskrudder-16.png": (mark, 16),
        "deskrudder-32.png": (mark, 32),
        "deskrudder-48.png": (mark, 48),
        "deskrudder-64.png": (mark, 64),
        "deskrudder-128.png": (full, 128),
        "deskrudder-256.png": (full, 256),
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

    _opaque_ui_logo(mark, 512).save(out_dir / "ui-logo-512.png")
    _opaque_ui_logo(mark, 256).save(out_dir / "ui-logo-256.png")

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    frames = []
    for iw, ih in ico_sizes:
        base = mark if iw <= 64 else full
        frames.append(_fit_square(base, iw))
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
