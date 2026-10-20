#!/usr/bin/env python3
"""Gera / decodifica a string de importação do RustDesk (Settings → Network).

Formato: base64(JSON) invertido — o mesmo que o cliente usa em «Export Server Config».
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def encode(cfg: dict) -> str:
    raw = json.dumps(cfg, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")[::-1]


def decode(blob: str) -> dict:
    raw = base64.b64decode(blob[::-1])
    return json.loads(raw.decode("utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--json",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "server.config.json",
        help="Caminho do JSON (host/relay/key/api)",
    )
    p.add_argument("--decode", metavar="STRING", help="Decodifica uma string colada no cliente")
    args = p.parse_args()

    if args.decode:
        cfg = decode(args.decode.strip())
        json.dump(cfg, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    data = json.loads(args.json.read_text(encoding="utf-8"))
    cfg = {
        "host": data["host"],
        "relay": data.get("relay") or data["host"],
        "key": data["key"],
        "api": data.get("api") or "",
    }
    print(encode(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
