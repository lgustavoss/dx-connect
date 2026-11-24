#!/usr/bin/env python3
"""Gera icones do Duplex Suporte a partir da arte oficial DuplexSoft.

Fontes (branding-duplex-suporte/sources/):
  icone-d.png          — marca D (favicon / titlebar / tray)
  logo-duplexsoft.png  — D + DuplexSoft (rodape)

Topo da home (estilo QuickSupport / WebPosto): D em tamanho generoso + texto
«Duplex Suporte» injetado pelo apply_branding. Rodape: logo completa.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent
BRANDING = HERE / "branding-duplex-suporte"
SOURCES = BRANDING / "sources"
ICON_SRC = SOURCES / "icone-d.png"
LOGO_SRC = SOURCES / "logo-duplexsoft.png"


def _knockout_near_black(im: Image.Image, threshold: int = 28) -> Image.Image:
    """Fundo preto/quase preto → alpha (arte em fundo preto)."""
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]  # type: ignore[misc]
            if a == 0:
                continue
            if max(r, g, b) <= threshold:
                px[x, y] = (r, g, b, 0)  # type: ignore[index]
    return rgba


def _content_bbox(im: Image.Image, alpha_min: int = 8) -> tuple[int, int, int, int]:
    a = im.split()[-1]
    return a.getbbox() or (0, 0, im.width, im.height)


def _crop_pad_square(im: Image.Image, pad_ratio: float = 0.08) -> Image.Image:
    box = _content_bbox(im)
    cropped = im.crop(box)
    w, h = cropped.size
    side = max(w, h)
    pad = int(side * pad_ratio)
    side = side + 2 * pad
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(cropped, ((side - w) // 2, (side - h) // 2), cropped)
    return out


def _fit(im: Image.Image, size: int) -> Image.Image:
    return im.resize((size, size), Image.Resampling.LANCZOS)


def _fit_width(im: Image.Image, width: int) -> Image.Image:
    w, h = im.size
    if w <= 0:
        return im
    nh = max(1, int(round(h * (width / w))))
    return im.resize((width, nh), Image.Resampling.LANCZOS)


def _png_bytes(im: Image.Image) -> bytes:
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _save_png_ico(path: Path, frames: list[Image.Image]) -> None:
    """ICO com PNG embutido (Windows le 16/24/32/48)."""
    images = []
    offset = 6 + 16 * len(frames)
    for im in frames:
        data = _png_bytes(im)
        w, h = im.size
        images.append((w if w < 256 else 0, h if h < 256 else 0, data, offset))
        offset += len(data)
    buf = BytesIO()
    buf.write(struct.pack("<HHH", 0, 1, len(frames)))
    for w, h, data, off in images:
        buf.write(struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), off))
    for _, _, data, _ in images:
        buf.write(data)
    path.write_bytes(buf.getvalue())


def _write(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG")
    print(f"  {path.relative_to(BRANDING)}")


def main() -> int:
    if not ICON_SRC.is_file() or not LOGO_SRC.is_file():
        print(f"Faltam fontes em {SOURCES}", flush=True)
        return 1

    mark = _crop_pad_square(_knockout_near_black(Image.open(ICON_SRC)))
    logo = _knockout_near_black(Image.open(LOGO_SRC))
    # Aperta o logo horizontal (remove padding preto restante).
    box = _content_bbox(logo)
    logo = logo.crop(box)

    BRANDING.mkdir(parents=True, exist_ok=True)

    # Favicon / titlebar / tray / res
    for size, name in (
        (16, "deskrudder-16.png"),  # nomes legados que copy_icons ja procura
        (32, "deskrudder-32.png"),
        (32, "32x32.png"),
        (48, "deskrudder-48.png"),
        (64, "deskrudder-64.png"),
        (64, "64x64.png"),
        (128, "deskrudder-128.png"),
        (128, "128x128.png"),
        (128, "128x128@2x.png"),
        (256, "deskrudder-256.png"),
        (256, "icon.png"),
    ):
        _write(_fit(mark, size), BRANDING / name)

    # ICO app + tray
    ico_frames = [_fit(mark, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    _save_png_ico(BRANDING / "icon.ico", ico_frames)
    print("  icon.ico")
    _save_png_ico(BRANDING / "tray-icon.ico", [_fit(mark, 32)])
    print("  tray-icon.ico")

    # Topo da home (loadLogo): D + DuplexSoft (lockup), estilo QuickSupport simples.
    top512 = _fit_width(logo, 512)
    # ui-logo e quadrado no Flutter; centraliza o lockup num canvas transparente.
    def _square_pad(im: Image.Image, size: int) -> Image.Image:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        im2 = im if im.width <= size else _fit_width(im, size)
        if im2.height > size:
            ratio = size / im2.height
            im2 = im2.resize(
                (max(1, int(im2.width * ratio)), size), Image.Resampling.LANCZOS
            )
        canvas.paste(im2, ((size - im2.width) // 2, (size - im2.height) // 2), im2)
        return canvas

    _write(_square_pad(logo, 512), BRANDING / "ui-logo-512.png")
    _write(_square_pad(logo, 256), BRANDING / "ui-logo-256.png")
    _write(top512, BRANDING / "ui-logo-wide-512.png")

    # Arte do lockup (caso queira no rodape depois); topo ja usa o mesmo.
    _write(_fit_width(logo, 512), BRANDING / "powered-duplexsoft-512.png")
    _write(_fit_width(logo, 256), BRANDING / "powered-duplexsoft-256.png")

    # Master 1024 (Flutter res/icon.png)
    _write(_fit(mark, 1024), BRANDING / "icon-source-1024.png")

    # Kit minimo para copy_flutter_icons (titlebar + runner)
    kit = BRANDING / "kit-1253"
    _write(_fit(mark, 32), kit / "01_titlebar" / "titlebar-32.png")
    _write(_fit(mark, 128), kit / "06_ui_icon" / "ui-icon-128.png")
    # Topo da UI = lockup DuplexSoft (nao so o D).
    _write(_square_pad(logo, 512), kit / "05_ui_logo" / "ui-logo-512.png")
    _write(_fit(mark, 1024), kit / "07_flutter_res" / "res-icon-1024.png")
    _write(_fit(mark, 32), kit / "07_flutter_res" / "res-32.png")
    _write(_fit(mark, 64), kit / "07_flutter_res" / "res-64.png")
    _write(_fit(mark, 128), kit / "07_flutter_res" / "res-128.png")
    runner_ico = kit / "08_flutter_runner" / "flutter-app-icon.ico"
    runner_ico.parent.mkdir(parents=True, exist_ok=True)
    _save_png_ico(runner_ico, ico_frames)
    print("  kit-1253/08_flutter_runner/flutter-app-icon.ico")

    readme = BRANDING / "README.md"
    readme.write_text(
        "# Branding — Duplex Suporte\n\n"
        "- `sources/icone-d.png` — favicon / titlebar / tray (marca D)\n"
        "- `sources/logo-duplexsoft.png` — rodape (D + DuplexSoft)\n"
        "- Gerar de novo: `python scripts/render_duplex_suporte_icons.py`\n",
        encoding="utf-8",
    )
    print(f">> Branding gerado em {BRANDING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
