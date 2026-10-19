#!/usr/bin/env python3
"""Aplica marca DeskRudder + servidor Duplex num clone do rustdesk.

Nao renomeia o crate `rustdesk` no Cargo (evita quebrar scripts de build).
O CI deve renomear o binario para DeskRudder.exe apos o cargo build — o
instalador/is_installed() procura `{APP_NAME}.exe`.

Altera: APP_NAME, icones, RENDEZVOUS_SERVERS, PROD_RENDEZVOUS_SERVER, RS_PUB_KEY.
"""

from __future__ import annotations

import argparse
import base64
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
        "tray-icon.ico": "tray-icon.ico",
        "icon.png": "icon.png",
        "32x32.png": "32x32.png",
        "64x64.png": "64x64.png",
        "128x128.png": "128x128.png",
        "128x128@2x.png": "128x128@2x.png",
    }

    for src_name, dst_name in mapping.items():
        p = brand / src_name
        if p.is_file():
            shutil.copy2(p, res / dst_name)
            print(f"  icon {dst_name}")

    # 64x64: fallback a partir do mark DeskRudder
    if not (res / "64x64.png").is_file():
        for candidate in ("deskrudder-64.png", "128x128.png", "deskrudder-128.png"):
            p = brand / candidate
            if p.is_file():
                shutil.copy2(p, res / "64x64.png")
                print(f"  icon 64x64.png (from {candidate})")
                break

    for size in (16, 32, 48, 64, 128, 256):
        p = brand / f"deskrudder-{size}.png"
        if p.is_file():
            shutil.copy2(p, res / p.name)

    # Fallback: se tray-icon.ico nao veio no branding, copia icon.ico
    tray = res / "tray-icon.ico"
    if not tray.is_file() and (res / "icon.ico").is_file():
        shutil.copy2(res / "icon.ico", tray)
        print("  icon tray-icon.ico (fallback icon.ico)")


def patch_sciter_window_icon(ui_rs: Path, png_128: Path) -> None:
    """Sciter usa get_icon() com PNG em base64 embutido — nao le res/icon.ico."""
    if not ui_rs.is_file():
        raise SystemExit(f"Falta {ui_rs}")
    if not png_128.is_file():
        raise SystemExit(f"Falta {png_128} para patch de get_icon()")

    b64 = base64.b64encode(png_128.read_bytes()).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"
    text = ui_rs.read_text(encoding="utf-8")
    if "pub fn get_icon()" not in text:
        raise SystemExit(f"get_icon() nao encontrado em {ui_rs}")

    text2, n = re.subn(
        r'data:image/png;base64,[A-Za-z0-9+/=]+',
        data_uri,
        text,
    )
    if n < 1:
        raise SystemExit(f"Nenhum data URI PNG encontrado em {ui_rs}")
    ui_rs.write_text(text2, encoding="utf-8")
    print(f"  ui.rs get_icon(): {n} data URI(s) -> DeskRudder", flush=True)


def patch_powered_by(lang_dir: Path) -> None:
    """Troca RustDesk por DeskRudder na chave powered_by_me (rodape da UI)."""
    if not lang_dir.is_dir():
        return
    replacements = 0
    for path in sorted(lang_dir.glob("*.rs")):
        text = path.read_text(encoding="utf-8")

        def _repl(m: re.Match[str]) -> str:
            return f'{m.group(1)}{m.group(2).replace("RustDesk", "DeskRudder")}{m.group(3)}'

        text2, n = re.subn(
            r'(\("powered_by_me",\s*")([^"]*)("\))',
            _repl,
            text,
            count=1,
        )
        if n and text2 != text:
            path.write_text(text2, encoding="utf-8")
            replacements += 1
    if replacements:
        print(f"  lang powered_by_me: {replacements} arquivo(s)", flush=True)


def patch_portable_metadata(cargo_toml: Path) -> None:
    if not cargo_toml.is_file():
        return
    text = cargo_toml.read_text(encoding="utf-8")
    orig = text
    text = re.sub(r'(?m)^ProductName = ".*"$', 'ProductName = "DeskRudder"', text, count=1)
    text = re.sub(
        r'(?m)^FileDescription = ".*"$',
        'FileDescription = "DeskRudder Acesso Remoto"',
        text,
        count=1,
    )
    text = re.sub(
        r'(?m)^description = ".*"$',
        'description = "DeskRudder Acesso Remoto"',
        text,
        count=1,
    )
    if text != orig:
        cargo_toml.write_text(text, encoding="utf-8")
        print("  portable Cargo.toml ProductName/FileDescription -> DeskRudder", flush=True)


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
    # Sem PROD_RENDEZVOUS_SERVER preenchido, using_public_server() fica true e a UI
    # mostra "configure seu proprio servidor" mesmo com RENDEZVOUS_SERVERS customizado.
    text, n_prod = re.subn(
        r'pub static ref PROD_RENDEZVOUS_SERVER:\s*RwLock<String>\s*=\s*'
        r'RwLock::new\(""\.to_owned\(\)\);',
        f'pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = '
        f'RwLock::new("{host}".to_owned());',
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
        raise SystemExit(f"Nenhuma alteracao em {path} — upstream mudou o formato?")
    if n_prod < 1:
        raise SystemExit(
            f"PROD_RENDEZVOUS_SERVER nao foi alterado em {path} — tip de servidor "
            "publico continuaria aparecendo"
        )
    path.write_text(text, encoding="utf-8")
    print(
        f"  config.rs: APP_NAME={n1 + n1b} PROD_RENDEZVOUS={n_prod} "
        f"RENDEZVOUS={n2} RS_PUB_KEY={n3}",
        flush=True,
    )


def patch_cargo_bundle_name(path: Path) -> None:
    """So o nome de exibicao do bundle, se existir — nao muda o crate name."""
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
        print(f"Nao parece um clone rustdesk: {src}", file=sys.stderr)
        return 1

    host, key = load_server(args.config.resolve())
    brand = args.branding.resolve()
    print(f">> Branding DeskRudder em {src}")
    print(f"   host={host}")

    copy_icons(brand, src)
    patch_cargo_bundle_name(src / "Cargo.toml")
    patch_portable_metadata(src / "libs" / "portable" / "Cargo.toml")

    png_128 = brand / "128x128.png"
    if not png_128.is_file():
        png_128 = brand / "deskrudder-128.png"
    patch_sciter_window_icon(src / "src" / "ui.rs", png_128)
    patch_powered_by(src / "src" / "lang")

    cfg_rs = src / "libs" / "hbb_common" / "src" / "config.rs"
    if not cfg_rs.is_file():
        print(f"Falta {cfg_rs} (submodule hbb_common?).", file=sys.stderr)
        return 1
    patch_config_rs(cfg_rs, host, key)

    # Sanity: chave, host e servidor de produto presentes
    body = cfg_rs.read_text(encoding="utf-8")
    if host not in body or key not in body or "DeskRudder" not in body:
        print("Verificacao falhou apos patch.", file=sys.stderr)
        return 1
    if f'RwLock::new("{host}".to_owned())' not in body:
        print("Verificacao falhou: PROD_RENDEZVOUS_SERVER sem host.", file=sys.stderr)
        return 1

    ui_body = (src / "src" / "ui.rs").read_text(encoding="utf-8")
    our_b64 = base64.b64encode(png_128.read_bytes()).decode("ascii")
    if our_b64 not in ui_body:
        print("Verificacao falhou: get_icon() sem PNG DeskRudder.", file=sys.stderr)
        return 1

    print(">> OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
