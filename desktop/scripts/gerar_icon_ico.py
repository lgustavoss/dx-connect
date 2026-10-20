"""Regenera build/icon.ico multi-tamanho a partir de build/icon.png.

Uso (na pasta desktop/): python scripts/gerar_icon_ico.py
Requer Pillow. Grava ICO com PNGs embutidos (Windows Vista+), um frame por tamanho.
"""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
BUILD = RAIZ / "build"
PNG = BUILD / "icon.png"
ICO = BUILD / "icon.ico"
LADOS = (16, 24, 32, 48, 64, 128, 256)


def _png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def escrever_ico(destino: Path, frames: list[Image.Image]) -> None:
    """ICO com imagens PNG embutidas (um diretório + entradas + blobs)."""
    blobs = [_png_bytes(f) for f in frames]
    n = len(frames)
    offset = 6 + 16 * n
    cabeca = struct.pack("<HHH", 0, 1, n)
    entradas = bytearray()
    for img, blob in zip(frames, blobs, strict=True):
        w, h = img.size
        # 0 = 256 no campo de 1 byte do ICO
        wb = 0 if w >= 256 else w
        hb = 0 if h >= 256 else h
        entradas += struct.pack("<BBBBHHII", wb, hb, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    destino.write_bytes(cabeca + bytes(entradas) + b"".join(blobs))


def main() -> None:
    if not PNG.is_file():
        raise SystemExit(f"Falta {PNG} — rode scripts/gerar-icones.py antes.")
    base = Image.open(PNG).convert("RGBA")
    frames = [base.resize((lado, lado), Image.Resampling.LANCZOS) for lado in LADOS]
    escrever_ico(ICO, frames)

    raw = ICO.read_bytes()
    _r, typ, count = struct.unpack_from("<HHH", raw, 0)
    if typ != 1 or count != len(LADOS):
        raise SystemExit(f"ICO inválido: type={typ} count={count}")
    for i in range(count):
        w, h, _c, _res, _pl, _bpp, nbytes, offset = struct.unpack_from("<BBBBHHII", raw, 6 + 16 * i)
        print(f"  frame {i}: {w or 256}x{h or 256} ({nbytes} B @ {offset})")
    print(f"OK {ICO.name}: {count} frames, {ICO.stat().st_size} bytes")


if __name__ == "__main__":
    main()
