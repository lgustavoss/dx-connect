#!/usr/bin/env python3
"""Gera icones do cliente Windows de acesso remoto (duas setas opostas).

Paleta alinhada a frontend/src/brand (teal -> sky). Distinto do mark do app
do painel (D + atendente).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

TEAL_LIGHT = (20, 184, 166, 255)  # #14B8A6
TEAL = (13, 148, 136, 255)  # #0D9488
SKY = (2, 132, 199, 255)  # #0284C7
SHADOW = (11, 45, 74, 110)  # navy translucido
WHITE = (248, 250, 252, 255)  # #F8FAFC


def _lerp(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def _gradient_tile(size: int, radius: float) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    r = max(1.0, radius)
    for y in range(size):
        ty = y / max(1, size - 1)
        for x in range(size):
            cx = min(x, size - 1 - x)
            cy = min(y, size - 1 - y)
            if cx < r and cy < r:
                dx = r - cx
                dy = r - cy
                if dx * dx + dy * dy > r * r:
                    continue
            # gradiente horizontal teal -> sky (como o conceito)
            t = x / max(1, size - 1)
            # leve inclinacao
            t = min(1.0, max(0.0, t * 0.85 + ty * 0.15))
            if t < 0.45:
                color = _lerp(TEAL_LIGHT, TEAL, t / 0.45)
            else:
                color = _lerp(TEAL, SKY, (t - 0.45) / 0.55)
            px[x, y] = color  # type: ignore[index]
    return img


def _arrow_polygon(
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    pointing_right: bool,
) -> list[tuple[float, float]]:
    """Seta com entalhe leve na cauda (leitura boa em 16–32px)."""
    body_h = height * 0.42
    cy = top + height / 2
    body_top = cy - body_h / 2
    body_bot = cy + body_h / 2
    head_w = width * 0.34
    notch = height * 0.12

    if pointing_right:
        tip_x = left + width
        head_base = tip_x - head_w
        tail_x = left
        return [
            (tail_x + notch, body_top),
            (head_base, body_top),
            (head_base, top),
            (tip_x, cy),
            (head_base, top + height),
            (head_base, body_bot),
            (tail_x, body_bot),
            (tail_x + notch, body_top + body_h * 0.35),
        ]
    tip_x = left
    head_base = tip_x + head_w
    tail_x = left + width
    return [
        (tail_x - notch, body_bot),
        (head_base, body_bot),
        (head_base, top + height),
        (tip_x, cy),
        (head_base, top),
        (head_base, body_top),
        (tail_x, body_top),
        (tail_x - notch, body_bot - body_h * 0.35),
    ]


def draw_remote_mark(size: int) -> Image.Image:
    """Tile arredondado + duas setas horizontais opostas."""
    pad = size * 0.04
    tile = int(round(size - 2 * pad))
    radius = tile * 0.22
    base = _gradient_tile(tile, radius)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ox = oy = int(round(pad))
    canvas.paste(base, (ox, oy), base)

    # camada das setas (com sombra) dentro do tile
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    margin_x = size * 0.18
    arrow_w = size - 2 * margin_x
    arrow_h = size * 0.28
    gap = size * 0.06
    top_y = size / 2 - gap / 2 - arrow_h
    bot_y = size / 2 + gap / 2

    top_pts = _arrow_polygon(margin_x, top_y, arrow_w, arrow_h, pointing_right=True)
    bot_pts = _arrow_polygon(margin_x, bot_y, arrow_w, arrow_h, pointing_right=False)

    # sombra
    shadow_shift = max(1.0, size * 0.02)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.polygon([(x + shadow_shift, y + shadow_shift) for x, y in top_pts], fill=SHADOW)
    sdraw.polygon([(x + shadow_shift, y + shadow_shift) for x, y in bot_pts], fill=SHADOW)
    if size >= 48:
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(1, size // 64)))
    layer = Image.alpha_composite(layer, shadow)

    draw = ImageDraw.Draw(layer)
    draw.polygon(top_pts, fill=WHITE)
    draw.polygon(bot_pts, fill=WHITE)

    return Image.alpha_composite(canvas, layer)


def write_branding(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    draw_remote_mark(1024).save(out_dir / "icon-source-1024.png")

    sizes = {
        "deskrudder-16.png": 16,
        "deskrudder-32.png": 32,
        "deskrudder-48.png": 48,
        "deskrudder-64.png": 64,
        "deskrudder-128.png": 128,
        "deskrudder-256.png": 256,
        "32x32.png": 32,
        "128x128.png": 128,
        "128x128@2x.png": 128,
        "icon.png": 256,
    }
    cache: dict[int, Image.Image] = {}
    for name, s in sizes.items():
        if s not in cache:
            cache[s] = draw_remote_mark(s)
        cache[s].save(out_dir / name)

    # ICO: Pillow grava melhor a partir do maior + sizes
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    biggest = draw_remote_mark(256)
    biggest.save(out_dir / "icon.ico", format="ICO", sizes=ico_sizes)

    tray = draw_remote_mark(32)
    tray.save(out_dir / "tray-icon.ico", format="ICO", sizes=[(32, 32)])
    print(f">> icones escritos em {out_dir}")


def main() -> int:
    here = Path(__file__).resolve().parent.parent / "branding"
    write_branding(here)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
