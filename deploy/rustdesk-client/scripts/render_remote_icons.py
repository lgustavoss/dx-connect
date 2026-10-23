#!/usr/bin/env python3
"""Gera icones do cliente Windows a partir da arte oficial DeskRemote.

Fonte: branding/icon-source-final.jpg (master) ou icon-source-official.png (já com alpha).

JPEG em fundo preto (ChatGPT/export) vira PNG RGBA. PNG com alpha nos cantos é reusado.

Todos os tamanhos usam a arte completa (D + atendente + globo + nuvem).
"""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

BRANDING = Path(__file__).resolve().parent.parent / "branding"
KIT_DIR = BRANDING / "kit-1253"
FINAL_JPG = BRANDING / "icon-source-final.jpg"
DEFAULT_SOURCE = FINAL_JPG if FINAL_JPG.is_file() else BRANDING / "icon-source-official.png"


def _corner_luma(im: Image.Image) -> int:
    rgb = im.convert("RGB")
    r, g, b = rgb.getpixel((0, 0))
    return max(r, g, b)


def _knockout_black_background(rgb: Image.Image) -> Image.Image:
    """Fundo preto (arte nova) → alpha, sem comer camisa/cabelo/globo."""
    w, h = rgb.size
    px = rgb.load()
    seed = Image.new("L", (w, h), 0)
    sp = seed.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]  # type: ignore[misc]
            mx, mn = max(r, g, b), min(r, g, b)
            vermelho = r >= 55 and r >= g + 18 and r >= b + 18
            pele = r >= 85 and 45 <= g <= 210 and 30 <= b <= 190 and r > b
            claro = mn >= 130 and mx - mn <= 55
            globo = mx >= 85 and mn >= 35 and mx - mn <= 45
            azul = b >= 50 and b >= r + 10
            if vermelho or pele or claro or globo or azul:
                sp[x, y] = 255  # type: ignore[index]
    # Dilata a semente para cobrir cabelo, camisa e notebook pretos.
    protegido = seed.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.MaxFilter(21))
    gp = protegido.load()

    alpha = [[255] * w for _ in range(h)]
    seen = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def eh_fundo(r: int, g: int, b: int) -> bool:
        mx = max(r, g, b)
        if r >= 48 and r >= g + 14:
            return False
        if b >= 40 and b >= r + 10:
            return False
        return mx <= 38

    def tenta(x: int, y: int) -> None:
        if seen[y][x] or gp[x, y] > 0:  # type: ignore[index]
            return
        r, g, b = px[x, y]  # type: ignore[misc]
        if not eh_fundo(r, g, b):
            return
        seen[y][x] = True
        alpha[y][x] = 0
        q.append((x, y))

    for x in range(w):
        tenta(x, 0)
        tenta(x, h - 1)
    for y in range(h):
        tenta(0, y)
        tenta(w - 1, y)
    while q:
        x, y = q.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                tenta(nx, ny)

    rgba = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out = rgba.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]  # type: ignore[misc]
            out[x, y] = (r, g, b, 255 if alpha[y][x] else 0)  # type: ignore[index]
    return rgba


def _to_rgba_transparent(im: Image.Image) -> Image.Image:
    """Remove fundo branco, xadrez JPEG ou preto; preserva pele e brancos internos."""
    if im.mode == "RGBA":
        # Reusa alpha se ja parece util (cantos transparentes)
        a0 = im.getpixel((0, 0))[3]
        if a0 == 0:
            return im
    if _corner_luma(im) <= 48:
        return _knockout_black_background(im.convert("RGB"))

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


def _drop_small_components(im: Image.Image, min_pixels: int = 400) -> Image.Image:
    """Remove fragmentos soltos (ex.: topo de letras do wordmark)."""
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    keep = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if seen[y][x]:
                continue
            if px[x, y][3] < 10:  # type: ignore[index]
                seen[y][x] = True
                continue
            q: deque[tuple[int, int]] = deque([(x, y)])
            cells: list[tuple[int, int]] = []
            seen[y][x] = True
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < w and 0 <= ny < h) or seen[ny][nx]:
                        continue
                    if px[nx, ny][3] >= 10:  # type: ignore[index]
                        seen[ny][nx] = True
                        q.append((nx, ny))
                    else:
                        seen[ny][nx] = True
            if len(cells) >= min_pixels:
                for cx, cy in cells:
                    keep[cy][cx] = True
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    opx = out.load()
    for y in range(h):
        for x in range(w):
            if keep[y][x]:
                opx[x, y] = px[x, y]  # type: ignore[index]
    return out


def _mark_without_text(im: Image.Image) -> Image.Image:
    left, top, right, bottom = _content_bbox(im)
    height = bottom - top
    # 0.78 evita cortar o topo do wordmark (tracinhos orfaos)
    cut = top + int(height * 0.78)
    crop = im.crop((left, top, right, cut))
    crop = _drop_small_components(crop, min_pixels=400)
    return _crop_pad_square(crop, pad_ratio=0.08)


def _feather_alpha(im: Image.Image, radius: float = 1.15) -> Image.Image:
    """Suaviza o contorno binário do knockout (anti-alias nas bordas)."""
    rgba = im.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    soft = alpha.filter(ImageFilter.GaussianBlur(radius=radius))
    return Image.merge("RGBA", (red, green, blue, soft))


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


def _ui_logo(full: Image.Image, size: int) -> Image.Image:
    """Arte completa com fundo transparente para o painel host (dark e light)."""
    return _fit_square(full, size)


def _write_image(im: Image.Image, path: Path, **kwargs) -> None:
    """Grava com retries: o Explorer/Cursor no Windows trava PNG no meio do lote."""
    tmp = path.with_name(f"{path.stem}.__tmp__{path.suffix}")
    last: OSError | None = None
    for attempt in range(10):
        try:
            im.save(tmp, **kwargs)
            tmp.replace(path)
            return
        except OSError as exc:
            last = exc
            time.sleep(0.15 * (attempt + 1))
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
    raise last or OSError(f"falha ao gravar {path}")


def _save_ico(path: Path, frames: list[Image.Image], sizes: list[tuple[int, int]]) -> None:
    _write_image(
        frames[-1], path, format="ICO", sizes=sizes, append_images=frames[:-1]
    )


def write_kit_1253(kit: Path, icon_for, full: Image.Image) -> None:
    """Pastas da issue #1253 (titlebar, tray, taskbar, ico, ui-logo, flutter)."""
    folders = {
        "01_titlebar": None,
        "02_tray": None,
        "03_taskbar": None,
        "04_app_ico": None,
        "05_ui_logo": None,
        "06_ui_icon": None,
        "07_flutter_res": None,
        "08_flutter_runner": None,
    }
    for name in folders:
        (kit / name).mkdir(parents=True, exist_ok=True)

    _write_image(icon_for(16), kit / "01_titlebar" / "titlebar-16.png")
    _write_image(icon_for(24), kit / "01_titlebar" / "titlebar-24.png")
    _write_image(icon_for(32), kit / "01_titlebar" / "titlebar-32.png")

    _write_image(icon_for(32), kit / "02_tray" / "tray-32.png")
    _write_image(icon_for(32), kit / "02_tray" / "tray.ico", format="ICO", sizes=[(32, 32)])

    _write_image(icon_for(16), kit / "03_taskbar" / "taskbar-16.png")
    _write_image(icon_for(32), kit / "03_taskbar" / "taskbar-32.png")
    _write_image(icon_for(48), kit / "03_taskbar" / "taskbar-48.png")
    _write_image(icon_for(64), kit / "03_taskbar" / "taskbar-64.png")
    _write_image(icon_for(256), kit / "03_taskbar" / "taskbar-256.png")

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    frames = [icon_for(iw) for iw, _ih in ico_sizes]
    _save_ico(kit / "04_app_ico" / "app-icon.ico", frames, ico_sizes)

    _write_image(_ui_logo(full, 256), kit / "05_ui_logo" / "ui-logo-256.png")
    _write_image(_ui_logo(full, 512), kit / "05_ui_logo" / "ui-logo-512.png")

    _write_image(icon_for(128), kit / "06_ui_icon" / "ui-icon-128.png")
    _write_image(icon_for(128), kit / "06_ui_icon" / "ui-icon-128@2x.png")

    _write_image(_ui_logo(full, 1024), kit / "07_flutter_res" / "res-icon-1024.png")
    _write_image(_ui_logo(full, 1024), kit / "07_flutter_res" / "res-mac-icon-1024.png")
    _write_image(icon_for(32), kit / "07_flutter_res" / "res-32.png")
    _write_image(icon_for(64), kit / "07_flutter_res" / "res-64.png")
    _write_image(icon_for(128), kit / "07_flutter_res" / "res-128.png")

    _save_ico(kit / "08_flutter_runner" / "flutter-app-icon.ico", frames, ico_sizes)
    print(f">> kit #1253 em {kit}")


def write_branding(out_dir: Path, source: Path = DEFAULT_SOURCE) -> None:
    if not source.is_file():
        raise SystemExit(f"Arte fonte nao encontrada: {source}")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw = Image.open(source)
    rgba = _to_rgba_transparent(raw)
    full = _feather_alpha(_crop_pad_square(rgba, pad_ratio=0.04))

    _write_image(full, out_dir / "icon-source-1024.png")
    _write_image(rgba, out_dir / "icon-source-official.png")

    full_fit: dict[int, Image.Image] = {}

    def icon_for(size: int) -> Image.Image:
        if size not in full_fit:
            full_fit[size] = _fit_square(full, size)
        return full_fit[size]

    mapping = {
        "deskrudder-16.png": 16,
        "deskrudder-32.png": 32,
        "deskrudder-48.png": 48,
        "deskrudder-64.png": 64,
        "64x64.png": 64,
        "deskrudder-128.png": 128,
        "deskrudder-256.png": 256,
        "32x32.png": 32,
        "128x128.png": 128,
        "128x128@2x.png": 128,
        "icon.png": 256,
    }
    for name, size in mapping.items():
        _write_image(icon_for(size), out_dir / name)

    _write_image(_ui_logo(full, 512), out_dir / "ui-logo-512.png")
    _write_image(_ui_logo(full, 256), out_dir / "ui-logo-256.png")

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    frames = [icon_for(iw) for iw, _ih in ico_sizes]
    _save_ico(out_dir / "icon.ico", frames, ico_sizes)
    _write_image(icon_for(32), out_dir / "tray-icon.ico", format="ICO", sizes=[(32, 32)])
    write_kit_1253(KIT_DIR, icon_for, full)
    print(f">> icones gerados de {source.name} em {out_dir}")


def main() -> int:
    write_branding(BRANDING, DEFAULT_SOURCE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
