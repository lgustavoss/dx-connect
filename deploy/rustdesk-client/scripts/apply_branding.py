#!/usr/bin/env python3
"""Aplica marca DeskRudder + servidor Duplex num clone do rustdesk.

Não renomeia o crate `rustdesk` (evita quebrar scripts de build).
Altera: APP_NAME na UI, ícones, RENDEZVOUS_SERVERS e RS_PUB_KEY.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def load_server(cfg_path: Path) -> tuple[str, str]:
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    host = str(data["host"]).strip()
    key = str(data["key"]).strip()
    if not host or not key:
        raise SystemExit("server.config.json precisa de host e key")
    return host, key


def copy_icons(brand: Path, src: Path) -> None:
    res = src / "res"
    res.mkdir(parents=True, exist_ok=True)
    mapping = {
        "icon.ico": "icon.ico",
        "32x32.png": "32x32.png",
        "128x128.png": "128x128.png",
        "128x128@2x.png": "128x128@2x.png",
    }
    for src_name, dst_name in mapping.items():
        p = brand / src_name
        if p.is_file():
            shutil.copy2(p, res / dst_name)
            print(f"  icon {dst_name}")
    for size in (16, 32, 48, 64, 128, 256):
        p = brand / f"deskrudder-{size}.png"
        if p.is_file():
            shutil.copy2(p, res / p.name)


def patch_config_rs(path: Path, host: str, key: str) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text

    text, n1 = re.subn(
        r'RwLock::new\("RustDesk"\.to_owned\(\)\)',
        'RwLock::new("DeskRudder".to_owned())',
        text,
        count=1,
    )
    text, n1b = re.subn(
        r'Arc::new\(RwLock::new\("RustDesk"\.to_owned\(\)\)\)',
        'Arc::new(RwLock::new("DeskRudder".to_owned()))',
        text,
        count=1,
    )
    text, n2 = re.subn(
        r'pub const RENDEZVOUS_SERVERS:\s*&\[&str\]\s*=\s*&\[.*?\];',
        f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{host}"];',
        text,
        count=1,
        flags=re.S,
    )
    text, n3 = re.subn(
        r'pub const RS_PUB_KEY:\s*&str\s*=\s*"[^"]*";',
        f'pub const RS_PUB_KEY: &str = "{key}";',
        text,
        count=1,
    )

    if text == orig:
        raise SystemExit(f"Nenhuma alteração em {path} — upstream mudou o formato?")
    path.write_text(text, encoding="utf-8")
    print(
        f"  config.rs: APP_NAME={n1 + n1b} RENDEZVOUS={n2} RS_PUB_KEY={n3}",
        flush=True,
    )


def patch_cargo_bundle_name(path: Path) -> None:
    """Só o nome de exibição do bundle, se existir — não muda o crate name."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text2, n = re.subn(
        r'(?m)^name = "RustDesk"',
        'name = "DeskRudder"',
        text,
        count=1,
    )
    if n:
        path.write_text(text2, encoding="utf-8")
        print("  Cargo.toml bundle name -> DeskRudder", flush=True)


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rustdesk_src", type=Path, help="Clone do rustdesk (com submodules)")
    ap.add_argument(
        "--config",
        type=Path,
        default=here / "server.config.json",
        help="JSON host/key",
    )
    ap.add_argument(
        "--branding",
        type=Path,
        default=here / "branding",
        help="Pasta com icon.ico e PNGs",
    )
    args = ap.parse_args()
    src = args.rustdesk_src.resolve()
    if not (src / ".git").exists() and not (src / "Cargo.toml").is_file():
        print(f"Não parece um clone rustdesk: {src}", file=sys.stderr)
        return 1

    host, key = load_server(args.config.resolve())
    print(f">> Branding DeskRudder em {src}")
    print(f"   host={host}")

    copy_icons(args.branding.resolve(), src)
    patch_cargo_bundle_name(src / "Cargo.toml")

    cfg_rs = src / "libs" / "hbb_common" / "src" / "config.rs"
    if not cfg_rs.is_file():
        print(f"Falta {cfg_rs} (submodule hbb_common?).", file=sys.stderr)
        return 1
    patch_config_rs(cfg_rs, host, key)

    # Sanity: chave e host presentes
    body = cfg_rs.read_text(encoding="utf-8")
    if host not in body or key not in body or "DeskRudder" not in body:
        print("Verificação falhou após patch.", file=sys.stderr)
        return 1
    print(">> OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
