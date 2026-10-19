#!/usr/bin/env python3
"""Aplica marca DeskRudder + servidor Duplex num clone do rustdesk.

Nao renomeia o crate `rustdesk` no Cargo (evita quebrar scripts de build).
O CI deve renomear o binario para DeskRudder.exe apos o cargo build — o
instalador/is_installed() procura `{APP_NAME}.exe`.

Altera: APP_NAME, icones, RENDEZVOUS_SERVERS, PROD_RENDEZVOUS_SERVER, RS_PUB_KEY,
modo incoming-only (so ser acessado), UI host com logo, nome do atalho Windows.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
from pathlib import Path

# Nome do atalho na Area de Trabalho / menu Iniciar (APP_NAME do exe continua DeskRudder).
SHORTCUT_DISPLAY_NAME = "DeskRudder - Acesso Remoto"


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


def patch_incoming_only(config_rs: Path) -> None:
    """Forca modo so-recebe: este PC e acessado, nao controla outros."""
    text = config_rs.read_text(encoding="utf-8")
    # Upstream: le HARD_SETTINGS["conn-type"] == "incoming".
    old = (
        "pub fn is_incoming_only() -> bool {\n"
        "    HARD_SETTINGS\n"
        "        .read()\n"
        "        .unwrap()\n"
        '        .get("conn-type")\n'
        '        .map_or(false, |x| x == ("incoming"))\n'
        "}"
    )
    new = (
        "pub fn is_incoming_only() -> bool {\n"
        "    // DeskRudder Acesso Remoto: build so para ser acessado remotamente.\n"
        "    true\n"
        "}"
    )
    if old not in text:
        raise SystemExit(f"is_incoming_only() nao encontrado em {config_rs}")
    config_rs.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  config.rs: is_incoming_only() -> true (host-only)", flush=True)


def patch_host_only_ui(index_tis: Path) -> None:
    """UI host: painel esquerdo (ID/senha) + status + logo a direita (sem conectar)."""
    if not index_tis.is_file():
        raise SystemExit(f"Falta {index_tis}")
    text = index_tis.read_text(encoding="utf-8")
    orig = text

    text2, n = re.subn(
        r"const incoming_only_width = 180;",
        "const incoming_only_width = 640;",
        text,
        count=1,
    )
    if n < 1:
        raise SystemExit("incoming_only_width nao encontrado em index.tis")
    text = text2

    # Com logo a direita, o painel esquerdo mantem largura fixa (~200px do CSS).
    text2, n = re.subn(
        r'<div \.left-pane style=\{incoming_only \? "width:\*" : ""\}>',
        "<div .left-pane>",
        text,
        count=1,
    )
    if n < 1:
        raise SystemExit("left-pane style incoming_only nao encontrado")
    text = text2

    # Largura do campo ID no painel esquerdo (nao usar a largura total da janela).
    text2, n = re.subn(
        r'var input_width = incoming_only \? \(incoming_only_width - 20\) \+ "px" : "250px";',
        'var input_width = incoming_only ? "180px" : "250px";',
        text,
        count=1,
    )
    if n < 1:
        raise SystemExit("input_width incoming_only nao encontrado")
    text = text2

    old_right = """                    {incoming_only ? <ConnectStatus @{this.connect_status} /> : ""}
                </div>
                {!incoming_only && <div .right-pane>
                    <div .right-content>
                        <div .card-connect>
                            <div .title>{translate('Control Remote Desktop')}</div>
                            <ID @{this.remote_id} />
                            <div .right-buttons>
                                <button .button .outline #file-transfer>{translate('Transfer file')}</button>
                                <button .button #connect>{translate('Connect')}</button>
                            </div>
                        </div>
                        <MultipleSessions @{this.multipleSessions} />
                    </div>
                    {!outgoing_only ? <ConnectStatus @{this.connect_status} /> : ""}
                </div>}"""

    new_right = """                    {incoming_only ? <ConnectStatus @{this.connect_status} /> : ""}
                </div>
                {incoming_only && <div .right-pane>
                    <div .right-content style="flow:vertical;size:*;vertical-align:middle;horizontal-align:center;padding:2em;">
                        <img src={handler.get_icon()} style="width:148px;height:148px;" />
                        <div .title style="margin-top:1.2em;text-align:center;">DeskRudder</div>
                        <div .lighter-text style="text-align:center;margin-top:0.4em;">Acesso Remoto</div>
                    </div>
                </div>}
                {!incoming_only && <div .right-pane>
                    <div .right-content>
                        <div .card-connect>
                            <div .title>{translate('Control Remote Desktop')}</div>
                            <ID @{this.remote_id} />
                            <div .right-buttons>
                                <button .button .outline #file-transfer>{translate('Transfer file')}</button>
                                <button .button #connect>{translate('Connect')}</button>
                            </div>
                        </div>
                        <MultipleSessions @{this.multipleSessions} />
                    </div>
                    {!outgoing_only ? <ConnectStatus @{this.connect_status} /> : ""}
                </div>}"""

    if old_right not in text:
        raise SystemExit(
            "Bloco right-pane de App.render() nao encontrado em index.tis — upstream mudou?"
        )
    text = text.replace(old_right, new_right, 1)

    # Sem campo #remote_id no modo host-only.
    text2, n = re.subn(
        r"if \(!handler\.get_remote_id\(\)\) \{\n"
        r"        view\.focus = \$\(#remote_id\);\n"
        r"    \}",
        "if (!incoming_only && !handler.get_remote_id()) {\n"
        "        var remoteIdEl = $(#remote_id);\n"
        "        if (remoteIdEl) view.focus = remoteIdEl;\n"
        "    }",
        text,
        count=1,
    )
    if n < 1:
        raise SystemExit("focus #remote_id em self.ready() nao encontrado")
    text = text2

    if text == orig:
        raise SystemExit("patch_host_only_ui sem alteracoes")
    index_tis.write_text(text, encoding="utf-8")
    print("  index.tis: UI host-only (ID + status + logo)", flush=True)


def patch_shortcut_display_name(windows_rs: Path) -> None:
    """Atalho da Area de Trabalho / menu Iniciar: DeskRudder - Acesso Remoto."""
    if not windows_rs.is_file():
        raise SystemExit(f"Falta {windows_rs}")
    text = windows_rs.read_text(encoding="utf-8")
    name = SHORTCUT_DISPLAY_NAME

    old_mk = (
        "    let mk_shortcut_commands = embedded_shortcut_commands(\n"
        "        shortcut_bytes(&exe, None, shortcut_icon_location.as_deref())?,\n"
        '        &format!("{app_name}.lnk"),\n'
        '        "mk_shortcut",\n'
        "    );"
    )
    new_mk = (
        f'    let shortcut_link_name = "{name}";\n'
        "    let mk_shortcut_commands = embedded_shortcut_commands(\n"
        "        shortcut_bytes(&exe, None, shortcut_icon_location.as_deref())?,\n"
        '        &format!("{shortcut_link_name}.lnk"),\n'
        '        "mk_shortcut",\n'
        "    );"
    )
    if old_mk not in text:
        raise SystemExit("mk_shortcut_commands nao encontrado em windows.rs")
    text = text.replace(old_mk, new_mk, 1)

    old_desktop = (
        "        shortcuts = format!(\n"
        '            "copy /Y \\"{}\\\\{}.lnk\\" \\"%PUBLIC%\\\\Desktop\\\\\\"",\n'
        "            tmp_path,\n"
        "            crate::get_app_name()\n"
        "        );"
    )
    new_desktop = (
        "        shortcuts = format!(\n"
        '            "copy /Y \\"{}\\\\{}.lnk\\" \\"%PUBLIC%\\\\Desktop\\\\\\"",\n'
        "            tmp_path,\n"
        "            shortcut_link_name\n"
        "        );"
    )
    if old_desktop not in text:
        raise SystemExit("copy Desktop shortcut nao encontrado em windows.rs")
    text = text.replace(old_desktop, new_desktop, 1)

    old_start = (
        'copy /Y \\"{tmp_path}\\\\{app_name}.lnk\\" \\"{start_menu}\\\\\\"'
    )
    new_start = (
        'copy /Y \\"{tmp_path}\\\\{shortcut_link_name}.lnk\\" '
        '\\"{start_menu}\\\\\\"'
    )
    if old_start not in text:
        raise SystemExit("copy Start Menu shortcut nao encontrado")
    text = text.replace(old_start, new_start, 1)

    old_del_tmp = (
        'if exist \\"{tmp_path}\\\\{app_name}.lnk\\" '
        'del /f /q \\"{tmp_path}\\\\{app_name}.lnk\\"'
    )
    new_del_tmp = (
        'if exist \\"{tmp_path}\\\\{shortcut_link_name}.lnk\\" '
        'del /f /q \\"{tmp_path}\\\\{shortcut_link_name}.lnk\\"'
    )
    if old_del_tmp not in text:
        raise SystemExit("del tmp shortcut nao encontrado")
    text = text.replace(old_del_tmp, new_del_tmp, 1)

    old_display = 'reg add {subkey} /f /v DisplayName /t REG_SZ /d \\"{app_name}\\"'
    new_display = f'reg add {{subkey}} /f /v DisplayName /t REG_SZ /d \\"{name}\\"'
    if old_display not in text:
        raise SystemExit("DisplayName reg add nao encontrado")
    text = text.replace(old_display, new_display, 1)

    # Desinstalar: remove atalho novo e o antigo (DeskRudder.lnk) se existir.
    old_uninst = (
        'if exist \\"%PUBLIC%\\\\Desktop\\\\{app_name}.lnk\\" '
        'del /f /q \\"%PUBLIC%\\\\Desktop\\\\{app_name}.lnk\\"'
    )
    new_uninst = (
        f'if exist \\"%PUBLIC%\\\\Desktop\\\\{name}.lnk\\" '
        f'del /f /q \\"%PUBLIC%\\\\Desktop\\\\{name}.lnk\\"\n'
        '    if exist \\"%PUBLIC%\\\\Desktop\\\\{app_name}.lnk\\" '
        'del /f /q \\"%PUBLIC%\\\\Desktop\\\\{app_name}.lnk\\"'
    )
    if old_uninst not in text:
        raise SystemExit("uninstall Desktop shortcut nao encontrado")
    text = text.replace(old_uninst, new_uninst, 1)

    windows_rs.write_text(text, encoding="utf-8")
    print(f"  windows.rs: atalho/DisplayName -> {name}", flush=True)


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
    patch_incoming_only(cfg_rs)
    patch_host_only_ui(src / "src" / "ui" / "index.tis")
    patch_shortcut_display_name(src / "src" / "platform" / "windows.rs")

    # Sanity: chave, host e servidor de produto presentes
    body = cfg_rs.read_text(encoding="utf-8")
    if host not in body or key not in body or "DeskRudder" not in body:
        print("Verificacao falhou apos patch.", file=sys.stderr)
        return 1
    if f'RwLock::new("{host}".to_owned())' not in body:
        print("Verificacao falhou: PROD_RENDEZVOUS_SERVER sem host.", file=sys.stderr)
        return 1
    if "DeskRudder Acesso Remoto: build so para ser acessado" not in body:
        print("Verificacao falhou: is_incoming_only nao patchado.", file=sys.stderr)
        return 1

    ui_body = (src / "src" / "ui.rs").read_text(encoding="utf-8")
    our_b64 = base64.b64encode(png_128.read_bytes()).decode("ascii")
    if our_b64 not in ui_body:
        print("Verificacao falhou: get_icon() sem PNG DeskRudder.", file=sys.stderr)
        return 1

    index_body = (src / "src" / "ui" / "index.tis").read_text(encoding="utf-8")
    if "Acesso Remoto</div>" not in index_body or "handler.get_icon()" not in index_body:
        print("Verificacao falhou: UI host-only sem logo.", file=sys.stderr)
        return 1
    if "Control Remote Desktop" in index_body and "incoming_only && <div .right-pane>" not in index_body:
        print("Verificacao falhou: painel de conexao outgoing ainda ativo sem logo.", file=sys.stderr)
        return 1

    win_body = (src / "src" / "platform" / "windows.rs").read_text(encoding="utf-8")
    if SHORTCUT_DISPLAY_NAME not in win_body:
        print("Verificacao falhou: atalho sem nome DeskRudder - Acesso Remoto.", file=sys.stderr)
        return 1

    print(">> OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
