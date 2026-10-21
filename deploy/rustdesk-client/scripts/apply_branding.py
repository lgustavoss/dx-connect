#!/usr/bin/env python3
"""Aplica marca DeskRudder + servidor Duplex num clone do rustdesk.

Nao renomeia o crate `rustdesk` no Cargo (evita quebrar scripts de build).
O CI deve renomear o binario para DeskRudder.exe apos o cargo build — o
instalador/is_installed() procura `{APP_NAME}.exe`.

Altera: APP_NAME, icones, RENDEZVOUS_SERVERS, PROD_RENDEZVOUS_SERVER, RS_PUB_KEY,
nome do atalho Windows, canal de update (version.json).

Profiles (--profile):
  posto     — incoming-only + UI host (PDV)
  controle  — atendente outgoing-only (controla outros, sem ID na frota)
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
# Pasta sob Program Files (x86): DeskRudder\Acesso Remoto (outros instaladores irao ao lado).
INSTALL_DIR_RELATIVE = r"DeskRudder\Acesso Remoto"
WEBSITE_URL = "https://deskrudder.com.br/"
# Canais de atualizacao (Release GitHub).
RELEASE_TAG_POSTO = "acesso-remoto-windows"
RELEASE_TAG_CONTROLE = "acesso-remoto-controle-windows"
INSTALLER_NAME_POSTO = "DeskRudder-AcessoRemoto.exe"
INSTALLER_NAME_CONTROLE = "DeskRudder-AcessoRemoto-Controle.exe"

# Preenchidos em main() conforme --profile.
UPDATE_VERSION_JSON_URL = (
    f"https://github.com/lgustavoss/dx-connect/releases/download/"
    f"{RELEASE_TAG_POSTO}/version.json"
)
DOWNLOAD_INSTALLER_URL = (
    f"https://github.com/lgustavoss/dx-connect/releases/download/"
    f"{RELEASE_TAG_POSTO}/{INSTALLER_NAME_POSTO}"
)
UPDATE_RELEASE_TAG = RELEASE_TAG_POSTO

# Janela host-only: precisa caber o cartao UAC + botao Instalar no painel esquerdo.
# 580 cortava o botao em DPI 100–125%; 720 deixa folga. Min um pouco abaixo do default.
HOST_WINDOW_WIDTH = 760
HOST_WINDOW_HEIGHT_UNINSTALLED = 720
HOST_WINDOW_HEIGHT_INSTALLED = 560
HOST_WINDOW_MIN_WIDTH = 680
HOST_WINDOW_MIN_HEIGHT_UNINSTALLED = 660
HOST_WINDOW_MIN_HEIGHT_INSTALLED = 480


def configurar_canal_update(profile: str) -> None:
    """Define URLs de version.json / download conforme posto (so-recebe) ou controle."""
    global UPDATE_VERSION_JSON_URL, DOWNLOAD_INSTALLER_URL, UPDATE_RELEASE_TAG
    if profile == "controle":
        tag = RELEASE_TAG_CONTROLE
        nome = INSTALLER_NAME_CONTROLE
    else:
        tag = RELEASE_TAG_POSTO
        nome = INSTALLER_NAME_POSTO
    UPDATE_RELEASE_TAG = tag
    UPDATE_VERSION_JSON_URL = (
        f"https://github.com/lgustavoss/dx-connect/releases/download/{tag}/version.json"
    )
    DOWNLOAD_INSTALLER_URL = (
        f"https://github.com/lgustavoss/dx-connect/releases/download/{tag}/{nome}"
    )


def load_client_version(path: Path) -> str:
    ver = path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        raise SystemExit(f"CLIENT_VERSION invalida em {path}: {ver!r} (use X.Y.Z)")
    return ver

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


def patch_outgoing_only(config_rs: Path) -> None:
    """Forca modo so-controla: este PC inicia sessao e nao se registra no hbbs."""
    text = config_rs.read_text(encoding="utf-8")
    old = (
        "pub fn is_outgoing_only() -> bool {\n"
        "    HARD_SETTINGS\n"
        "        .read()\n"
        "        .unwrap()\n"
        '        .get("conn-type")\n'
        '        .map_or(false, |x| x == ("outgoing"))\n'
        "}"
    )
    new = (
        "pub fn is_outgoing_only() -> bool {\n"
        "    // DeskRudder Acesso Remoto: build so para controlar outros PCs.\n"
        "    true\n"
        "}"
    )
    if old not in text:
        raise SystemExit(f"is_outgoing_only() nao encontrado em {config_rs}")
    config_rs.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  config.rs: is_outgoing_only() -> true (atendente)", flush=True)


def _host_logo_data_uri(branding: Path) -> str:
    """PNG de alta resolucao (mark) para o painel direito — evita upscale do get_icon 128."""
    for name in ("ui-logo-512.png", "ui-logo-256.png", "deskrudder-256.png", "icon.png"):
        p = branding / name
        if p.is_file():
            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            print(f"  host logo: {name}", flush=True)
            return f"data:image/png;base64,{b64}"
    raise SystemExit("Nenhum PNG de logo UI em branding/ (ui-logo-512.png)")


def patch_host_only_ui(index_tis: Path, branding: Path) -> None:
    """UI host: painel esquerdo (ID/senha) + status + logo a direita (sem conectar)."""
    if not index_tis.is_file():
        raise SystemExit(f"Falta {index_tis}")
    text = index_tis.read_text(encoding="utf-8")
    orig = text
    w = HOST_WINDOW_WIDTH
    h_un = HOST_WINDOW_HEIGHT_UNINSTALLED
    h_in = HOST_WINDOW_HEIGHT_INSTALLED
    min_w = HOST_WINDOW_MIN_WIDTH
    min_h_un = HOST_WINDOW_MIN_HEIGHT_UNINSTALLED
    min_h_in = HOST_WINDOW_MIN_HEIGHT_INSTALLED
    logo_uri = _host_logo_data_uri(branding)

    text2, n = re.subn(
        r"const incoming_only_width = 180;",
        f"const incoming_only_width = {w};\n"
        f"const incoming_only_height_uninstalled = {h_un};\n"
        f"const incoming_only_height_installed = {h_in};\n"
        f"const incoming_only_min_width = {min_w};\n"
        f"const incoming_only_min_height_uninstalled = {min_h_un};\n"
        f"const incoming_only_min_height_installed = {min_h_in};\n"
        f'const deskrudder_host_logo = "{logo_uri}";',
        text,
        count=1,
    )
    if n < 1:
        raise SystemExit("incoming_only_width nao encontrado em index.tis")
    text = text2

    # Min size: com cartao Instalar a altura precisa caber o botao.
    old_min = (
        "if (incoming_only) {\n"
        "  view.windowMinSize = (scaleIt(incoming_only_width), "
        "scaleIt((handler.is_installed() || disable_installation) ? 300 : 390));\n"
        "} else {\n"
        "  view.windowMinSize = (scaleIt(560), scaleIt(300));\n"
        "}"
    )
    new_min = (
        "if (incoming_only) {\n"
        "  view.windowMinSize = (scaleIt(incoming_only_min_width), "
        "scaleIt((handler.is_installed() || disable_installation) "
        "? incoming_only_min_height_installed : incoming_only_min_height_uninstalled));\n"
        "} else {\n"
        "  view.windowMinSize = (scaleIt(560), scaleIt(300));\n"
        "}"
    )
    if old_min not in text:
        raise SystemExit("windowMinSize incoming_only nao encontrado")
    text = text.replace(old_min, new_min, 1)

    # Painel esquerdo um pouco mais largo: menos wrap no cartao UAC/Instalar.
    text2, n = re.subn(
        r'<div \.left-pane style=\{incoming_only \? "width:\*" : ""\}>',
        '<div .left-pane style={incoming_only ? "width:248px;min-width:248px;" : ""}>',
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
                    <div .right-content style="flow:vertical;size:*;vertical-align:middle;horizontal-align:center;padding:1.5em;">
                        <img src={deskrudder_host_logo} style="display:block;width:48%;max-width:300px;min-width:140px;height:width(100%);margin:0 *;" />
                        <div .title style="margin-top:1em;text-align:center;">DeskRudder</div>
                        <div .lighter-text style="text-align:center;margin-top:0.35em;">Acesso Remoto</div>
                        <div .lighter-text style="text-align:center;margin-top:0.6em;">Versao {handler.get_version()}</div>
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

    # Tamanho inicial da janela (primeira abertura) — caber botao Instalar.
    old_ready_size = (
        "            view.move(r[0], r[1], incoming_only ? scaleIt(incoming_only_width) : r[2], r[3]);\n"
        "        }\n"
        "    } else {\n"
        "        centerize(scaleIt(incoming_only ? incoming_only_width : 800), "
        "scaleIt(incoming_only ? 390 : 600));\n"
        "    }"
    )
    new_ready_size = (
        "            var hostH = (handler.is_installed() || disable_installation)\n"
        "                ? incoming_only_height_installed : incoming_only_height_uninstalled;\n"
        "            view.move(r[0], r[1], incoming_only ? scaleIt(incoming_only_width) : r[2],\n"
        "                incoming_only ? scaleIt(hostH) : r[3]);\n"
        "        }\n"
        "    } else {\n"
        "        var hostH0 = (handler.is_installed() || disable_installation)\n"
        "            ? incoming_only_height_installed : incoming_only_height_uninstalled;\n"
        "        centerize(scaleIt(incoming_only ? incoming_only_width : 800),\n"
        "            scaleIt(incoming_only ? hostH0 : 600));\n"
        "    }"
    )
    if old_ready_size not in text:
        raise SystemExit("centerize/move host size em self.ready() nao encontrado")
    text = text.replace(old_ready_size, new_ready_size, 1)

    if text == orig:
        raise SystemExit("patch_host_only_ui sem alteracoes")
    index_tis.write_text(text, encoding="utf-8")
    print(
        f"  index.tis: UI host-only (logo) + janela {w}x{h_un}/{h_in}",
        flush=True,
    )

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


def patch_website_urls(index_tis: Path, install_tis: Path) -> None:
    """Link 'Desenvolvido por' e Sobre -> site DeskRudder."""
    url = WEBSITE_URL.rstrip("/")
    replacements = [
        (index_tis, 'handler.open_url("https://rustdesk.com");', f'handler.open_url("{url}/");'),
        (
            index_tis,
            "url='https://rustdesk.com/privacy.html'",
            f"url='{url}/'",
        ),
        (
            index_tis,
            "url='https://rustdesk.com'",
            f"url='{url}/'",
        ),
        (
            install_tis,
            'view.open_url("http://rustdesk.com/privacy");',
            f'view.open_url("{url}/");',
        ),
    ]
    for path, old, new in replacements:
        if not path.is_file():
            raise SystemExit(f"Falta {path}")
        text = path.read_text(encoding="utf-8")
        if old not in text:
            # powered-by e Sobre podem ter sido patchados parcialmente; falhar so se nada mudar
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        print(f"  {path.name}: URL -> {url}", flush=True)

    # Garante o click do powered-by
    idx = index_tis.read_text(encoding="utf-8")
    if f'handler.open_url("{url}/");' not in idx:
        raise SystemExit("powered-by / website nao aponta para deskrudder.com.br")


def patch_install_path(windows_rs: Path, install_tis: Path) -> None:
    """Padrao: C:\\Program Files (x86)\\DeskRudder\\Acesso Remoto."""
    rel = INSTALL_DIR_RELATIVE  # DeskRudder\Acesso Remoto
    text = windows_rs.read_text(encoding="utf-8")
    # Fonte Rust: format!("{}\\{}", pf, crate::get_app_name())
    old = 'format!("{}\\\\{}", pf, crate::get_app_name())'
    # Fonte Rust desejada: format!("{}\\DeskRudder\\Acesso Remoto", pf)
    new = 'format!("{}\\\\DeskRudder\\\\Acesso Remoto", pf)'
    if old not in text:
        raise SystemExit("get_default_install_path format!() nao encontrado")
    windows_rs.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  windows.rs: install path -> …\\{rel}", flush=True)

    it = install_tis.read_text(encoding="utf-8")
    old_append = "          install_path += handler.get_app_name();"
    # Em Tiscript string, backslash simples no path Windows
    new_append = f'          install_path += "{rel}";'
    if old_append not in it:
        raise SystemExit("install.tis append get_app_name nao encontrado")
    install_tis.write_text(it.replace(old_append, new_append, 1), encoding="utf-8")
    print(f"  install.tis: Change Path -> …\\{rel}", flush=True)

def patch_client_version(cargo_toml: Path, portable_cargo: Path, client_version: str) -> None:
    """Versao do produto DeskRudder (independente da tag RustDesk upstream)."""
    text = cargo_toml.read_text(encoding="utf-8")
    text2, n = re.subn(
        r'(?m)^version = "[^"]+"',
        f'version = "{client_version}"',
        text,
        count=1,
    )
    if n < 1:
        raise SystemExit(f"version= nao encontrado em {cargo_toml}")
    cargo_toml.write_text(text2, encoding="utf-8")
    print(f"  Cargo.toml version -> {client_version}", flush=True)

    if portable_cargo.is_file():
        ptext = portable_cargo.read_text(encoding="utf-8")
        ptext2, pn = re.subn(
            r'(?m)^version = "[^"]+"',
            f'version = "{client_version}"',
            ptext,
            count=1,
        )
        if pn:
            portable_cargo.write_text(ptext2, encoding="utf-8")
            print(f"  portable Cargo.toml version -> {client_version}", flush=True)


def patch_update_check(common_rs: Path) -> None:
    """Substitui check do RustDesk (desligado em custom client) pelo version.json nosso."""
    text = common_rs.read_text(encoding="utf-8")
    old = """pub fn check_software_update() {
    if is_custom_client() {
        return;
    }
    let opt = LocalConfig::get_option(keys::OPTION_ENABLE_CHECK_UPDATE);
    if config::option2bool(keys::OPTION_ENABLE_CHECK_UPDATE, &opt) {
        std::thread::spawn(move || allow_err!(do_check_software_update()));
    }
}"""
    new = f"""pub fn check_software_update() {{
    // DeskRudder Acesso Remoto: canal proprio (version.json no Release GitHub).
    std::thread::spawn(move || allow_err!(do_check_deskrudder_update()));
}}

#[tokio::main(flavor = "current_thread")]
async fn do_check_deskrudder_update() -> hbb_common::ResultType<()> {{
    const URL: &str = "{UPDATE_VERSION_JSON_URL}";
    let proxy_conf = Config::get_socks();
    let tls_url = get_url_for_tls(URL, &proxy_conf);
    let tls_type = get_cached_tls_type(tls_url).unwrap_or(TlsType::Rustls);
    let client = create_http_client_async(tls_type, false);
    let resp = match client.get(URL).send().await {{
        Ok(r) => r,
        Err(err) => {{
            log::warn!("DeskRudder update check failed: {{}}", err);
            return Ok(());
        }}
    }};
    if !resp.status().is_success() {{
        log::warn!("DeskRudder update check HTTP {{}}", resp.status());
        return Ok(());
    }}
    let bytes = resp.bytes().await?;
    let v: serde_json::Value = serde_json::from_slice(&bytes)?;
    let latest = v.get("version").and_then(|x| x.as_str()).unwrap_or("").trim();
    if latest.is_empty() {{
        return Ok(());
    }}
    if get_version_number(latest) > get_version_number(crate::VERSION) {{
        // Ultimo segmento = versao (usado por get_new_version()).
        *SOFTWARE_UPDATE_URL.lock().unwrap() = format!(
            "https://github.com/lgustavoss/dx-connect/releases/download/{UPDATE_RELEASE_TAG}/{{}}",
            latest
        );
    }} else {{
        *SOFTWARE_UPDATE_URL.lock().unwrap() = "".to_string();
    }}
    Ok(())
}}"""
    if old not in text:
        raise SystemExit("check_software_update() nao encontrado em common.rs")
    common_rs.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  common.rs: check update -> version.json ({UPDATE_RELEASE_TAG})", flush=True)


def patch_update_banner(index_tis: Path) -> None:
    """Banner: baixa o .exe, roda --update (UAC) e reabre o app."""
    text = index_tis.read_text(encoding="utf-8")
    old = (
        "class UpdateMe: Reactor.Component {\n"
        "    function render() {\n"
        '        var update_or_download = "download"; // !is_win ? "download" : "update";\n'
        "        return <div .install-me>\n"
        "            <div>{translate('Status')}</div>\n"
        "            <div>There is a newer version of {handler.get_app_name()} "
        "({handler.get_new_version()}) available.</div>\n"
        "            {is_custom_client\n"
        '                ? <div style="font-size: 1em; font-weight: normal; '
        'text-align: left; padding-top: 1em;">{translate(\'Enable \\"Auto update\\" '
        "or contact your administrator for the latest version.')}</div>\n"
        "                : <div #install-me.link>{translate('Click to ' + "
        "update_or_download)}</div>}\n"
        '            <div #download-percent style="display:hidden; padding-top: 1em;" />\n'
        "        </div>;\n"
        "    }\n"
        "\n"
        "    event click $(#install-me) {\n"
        '        handler.open_url("https://rustdesk.com/download");\n'
        "        return;\n"
        "        if (!is_win) {\n"
        '            handler.open_url("https://rustdesk.com");\n'
        "            return;\n"
        "        }\n"
        "        var url = software_update_url + '.' + handler.get_software_ext();\n"
        "        var path = handler.get_software_store_path();\n"
        "        var onsuccess = function(md5) {\n"
        '            $(#download-percent).content(translate("Installing ..."));\n'
        "            handler.update_me(path);\n"
        "        };\n"
        "        var onerror = function(err) {\n"
        '            msgbox("custom-error", "Download Error", "Failed to download"); \n'
        "        };\n"
        "        var onprogress = function(loaded, total) {\n"
        "            if (!total) total = 5 * 1024 * 1024;\n"
        "            var el = $(#download-percent);\n"
        '            el.style.set{display: "block"};\n'
        '            el.content("Downloading %" + (loaded * 100 / total));\n'
        "        };\n"
        '        stdout.println("Downloading " + url + " to " + path);\n'
        "        download(\n"
        "            url,\n"
        "            self.url(path),\n"
        "            onsuccess, onerror, onprogress);\n"
        "    }\n"
        "}\n"
    )
    new = (
        "class UpdateMe: Reactor.Component {\n"
        "    function render() {\n"
        "        return <div .install-me>\n"
        "            <div>Atualização disponível</div>\n"
        "            <div>Há uma versão mais nova do DeskRudder Acesso Remoto "
        "({handler.get_new_version()}). A sua é {handler.get_version()}.</div>\n"
        "            <div #install-me.link>Atualizar agora</div>\n"
        '            <div #download-percent style="display:none; padding-top: 1em;" />\n'
        "        </div>;\n"
        "    }\n"
        "\n"
        "    event click $(#install-me) {\n"
        f'        var url = "{DOWNLOAD_INSTALLER_URL}";\n'
        "        var path = handler.get_software_store_path();\n"
        "        var onsuccess = function(md5) {\n"
        '            $(#download-percent).content("Instalando...");\n'
        "            handler.update_me(path);\n"
        "        };\n"
        "        var onerror = function(err) {\n"
        '            msgbox("custom-error", "Erro no download", '
        '"Não foi possível baixar a atualização. Tente de novo ou baixe pelo painel.");\n'
        "        };\n"
        "        var onprogress = function(loaded, total) {\n"
        "            if (!total) total = 5 * 1024 * 1024;\n"
        "            var el = $(#download-percent);\n"
        '            el.style.set{display: "block"};\n'
        '            el.content("Baixando %" + (loaded * 100 / total));\n'
        "        };\n"
        '        $(#download-percent).style.set{display: "block"};\n'
        '        $(#download-percent).content("Baixando...");\n'
        "        download(url, self.url(path), onsuccess, onerror, onprogress);\n"
        "    }\n"
        "}\n"
    )
    if old not in text:
        raise SystemExit("UpdateMe class nao encontrada em index.tis (upstream mudou?)")
    index_tis.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  index.tis: update in-app (download + instalar)", flush=True)


def patch_update_me_handler(ui_interface_rs: Path) -> None:
    """Sciter update_me: com caminho do .exe baixado, chama update_to (--update + UAC)."""
    text = ui_interface_rs.read_text(encoding="utf-8")
    old = (
        "pub fn update_me(_path: String) {\n"
        "    goto_install();\n"
        "}"
    )
    new = (
        "pub fn update_me(_path: String) {\n"
        "    #[cfg(windows)]\n"
        "    {\n"
        "        if !_path.is_empty() {\n"
        "            std::thread::spawn(move || {\n"
        "                match crate::platform::windows::update_to(&_path) {\n"
        "                    Ok(_) => {\n"
        "                        // --update troca os arquivos e reabre a janela/tray.\n"
        "                        std::process::exit(0);\n"
        "                    }\n"
        "                    Err(e) => {\n"
        "                        log::error!(\"DeskRudder update_to failed: {}\", e);\n"
        "                        let _ = std::fs::remove_file(&_path);\n"
        "                    }\n"
        "                }\n"
        "            });\n"
        "            return;\n"
        "        }\n"
        "    }\n"
        "    goto_install();\n"
        "}"
    )
    if old not in text:
        raise SystemExit("update_me() nao encontrado em ui_interface.rs")
    ui_interface_rs.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  ui_interface.rs: update_me -> update_to (--update)", flush=True)


def patch_install_version_label(install_tis: Path) -> None:
    """Mostra a versao na tela de instalacao."""
    text = install_tis.read_text(encoding="utf-8")
    old = '<div style="font-size: 2em;">{translate(\'Installation\')}</div>'
    new = (
        '<div style="font-size: 2em;">{translate(\'Installation\')}</div>\n'
        '            <div .lighter-text style="margin-top: 0.4em;">'
        "Versao {handler.get_version()}</div>"
    )
    if old not in text:
        raise SystemExit("titulo Installation nao encontrado em install.tis")
    install_tis.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  install.tis: label Versao", flush=True)


def patch_system_dark_theme(ui_rs: Path, index_tis: Path) -> None:
    """Tema escuro segue o Windows + barra de titulo imersiva (DWM)."""
    if not ui_rs.is_file():
        raise SystemExit(f"Falta {ui_rs}")
    text = ui_rs.read_text(encoding="utf-8")

    # HWND da janela principal para DwmSetWindowAttribute
    if "DESKRUDDER_MAIN_HWND" not in text:
        hwnd_store = """
lazy_static::lazy_static! {
    static ref DESKRUDDER_MAIN_HWND: Mutex<isize> = Mutex::new(0);
}

#[cfg(windows)]
fn deskrudder_set_titlebar_dark(hwnd: isize, dark: bool) {
    if hwnd == 0 {
        return;
    }
    #[link(name = "dwmapi")]
    extern "system" {
        fn DwmSetWindowAttribute(
            hwnd: isize,
            dwAttribute: u32,
            pvAttribute: *const core::ffi::c_void,
            cbAttribute: u32,
        ) -> i32;
    }
    // 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 20H1+); 19 = valor anterior
    let mut use_dark: i32 = if dark { 1 } else { 0 };
    unsafe {
        let _ = DwmSetWindowAttribute(
            hwnd,
            20,
            &use_dark as *const i32 as *const core::ffi::c_void,
            4,
        );
        let _ = DwmSetWindowAttribute(
            hwnd,
            19,
            &use_dark as *const i32 as *const core::ffi::c_void,
            4,
        );
    }
}
"""
        # inserir apos lazy_static CUR_SESSION block ou STUPID_VALUES
        anchor_ls = "lazy_static::lazy_static! {\n    // stupid workaround"
        if anchor_ls not in text:
            raise SystemExit("lazy_static STUPID_VALUES nao encontrado em ui.rs")
        text = text.replace(anchor_ls, hwnd_store + "\nlazy_static::lazy_static! {\n    // stupid workaround", 1)

    # Guardar HWND apos create
    old_hwnd = (
        "    #[cfg(windows)]\n"
        "    crate::platform::try_set_window_foreground(frame.get_hwnd() as _);"
    )
    new_hwnd = (
        "    #[cfg(windows)]\n"
        "    {\n"
        "        let hwnd = frame.get_hwnd() as isize;\n"
        "        *DESKRUDDER_MAIN_HWND.lock().unwrap() = hwnd;\n"
        "        crate::platform::try_set_window_foreground(hwnd as _);\n"
        "    }"
    )
    if old_hwnd in text and "DESKRUDDER_MAIN_HWND.lock()" not in text:
        text = text.replace(old_hwnd, new_hwnd, 1)

    methods = """
    fn is_system_dark_theme(&self) -> bool {
        #[cfg(windows)]
        {
            use winreg::enums::*;
            use winreg::RegKey;
            let hkcu = RegKey::predef(HKEY_CURRENT_USER);
            if let Ok(key) = hkcu.open_subkey(
                r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            ) {
                let light: u32 = key.get_value("AppsUseLightTheme").unwrap_or(1);
                return light == 0;
            }
            false
        }
        #[cfg(not(windows))]
        {
            false
        }
    }

    fn set_titlebar_dark(&self, dark: bool) {
        #[cfg(windows)]
        {
            let hwnd = *DESKRUDDER_MAIN_HWND.lock().unwrap();
            deskrudder_set_titlebar_dark(hwnd, dark);
        }
    }
"""
    anchor = "    pub fn is_custom_client(&self) -> bool {\n        crate::common::is_custom_client()\n    }"
    if "fn is_system_dark_theme" not in text:
        if anchor not in text:
            raise SystemExit("anchor is_custom_client nao encontrado em ui.rs")
        text = text.replace(anchor, anchor + methods, 1)
    elif "fn set_titlebar_dark" not in text:
        # ja tem is_system_dark_theme de build anterior — acrescentar set_titlebar_dark
        insert_after = "    fn is_system_dark_theme(&self) -> bool {\n"
        # find end of is_system_dark_theme function — fragile; prefer replace block
        old_sys = """    fn is_system_dark_theme(&self) -> bool {
        #[cfg(windows)]
        {
            use winreg::enums::*;
            use winreg::RegKey;
            let hkcu = RegKey::predef(HKEY_CURRENT_USER);
            if let Ok(key) = hkcu.open_subkey(
                r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            ) {
                let light: u32 = key.get_value("AppsUseLightTheme").unwrap_or(1);
                return light == 0;
            }
            false
        }
        #[cfg(not(windows))]
        {
            false
        }
    }
"""
        if old_sys in text:
            text = text.replace(old_sys, methods, 1)
        else:
            raise SystemExit("is_system_dark_theme presente mas formato inesperado")

    dispatch_line = "        fn is_custom_client();\n"
    dispatch_new = (
        "        fn is_custom_client();\n"
        "        fn is_system_dark_theme();\n"
        "        fn set_titlebar_dark(bool);\n"
    )
    if "fn set_titlebar_dark(bool);" not in text:
        if "fn is_system_dark_theme();" in text and "fn set_titlebar_dark" not in text:
            text = text.replace(
                "        fn is_system_dark_theme();\n",
                "        fn is_system_dark_theme();\n        fn set_titlebar_dark(bool);\n",
                1,
            )
        elif dispatch_line in text:
            text = text.replace(dispatch_line, dispatch_new, 1)
        else:
            raise SystemExit("dispatch is_custom_client nao encontrado")

    ui_rs.write_text(text, encoding="utf-8")
    print("  ui.rs: tema sistema + titlebar dark (DWM)", flush=True)

    # updateTheme: Y/N manuais; vazio = seguir sistema; sincroniza barra de titulo
    idx = index_tis.read_text(encoding="utf-8")
    old_theme = """function updateTheme() {
    var root_element = self;
    if (handler.get_option("allow-darktheme") == "Y") {
        // enable dark theme
        root_element.attributes.toggleClass("darktheme", true);
    } else {
        // disable dark theme
        root_element.attributes.toggleClass("darktheme", false);
    }
}"""
    # tambem aceitar versao ja patchada sem titlebar
    old_theme_partial = """function updateTheme() {
    var root_element = self;
    var opt = handler.get_option("allow-darktheme");
    var dark;
    if (opt == "Y") dark = true;
    else if (opt == "N") dark = false;
    else dark = handler.is_system_dark_theme();
    root_element.attributes.toggleClass("darktheme", dark);
}"""
    new_theme = """function updateTheme() {
    var root_element = self;
    var opt = handler.get_option("allow-darktheme");
    var dark;
    if (opt == "Y") dark = true;
    else if (opt == "N") dark = false;
    else dark = handler.is_system_dark_theme();
    root_element.attributes.toggleClass("darktheme", dark);
    try { handler.set_titlebar_dark(dark); } catch(e) {}
}"""
    if old_theme in idx:
        idx = idx.replace(old_theme, new_theme, 1)
    elif old_theme_partial in idx:
        idx = idx.replace(old_theme_partial, new_theme, 1)
    elif "set_titlebar_dark" in idx:
        pass
    else:
        raise SystemExit("updateTheme() nao encontrado em index.tis")
    index_tis.write_text(idx, encoding="utf-8")
    print("  index.tis: tema escuro + titlebar DWM", flush=True)


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
    ap.add_argument(
        "--client-version",
        type=Path,
        default=here / "CLIENT_VERSION",
        help="Arquivo com versao DeskRudder X.Y.Z",
    )
    ap.add_argument(
        "--profile",
        choices=("posto", "controle"),
        default="posto",
        help="posto=so-recebe (PDV); controle=atendente (pode iniciar sessao)",
    )
    args = ap.parse_args()
    src = args.rustdesk_src.resolve()
    if not (src / ".git").exists() and not (src / "Cargo.toml").is_file():
        print(f"Nao parece um clone rustdesk: {src}", file=sys.stderr)
        return 1

    profile: str = args.profile
    configurar_canal_update(profile)

    host, key = load_server(args.config.resolve())
    brand = args.branding.resolve()
    client_version = load_client_version(args.client_version.resolve())
    print(f">> Branding DeskRudder em {src}")
    print(f"   profile={profile}")
    print(f"   host={host}")
    print(f"   client_version={client_version}")
    print(f"   update={UPDATE_VERSION_JSON_URL}")

    copy_icons(brand, src)
    patch_cargo_bundle_name(src / "Cargo.toml")
    patch_client_version(
        src / "Cargo.toml",
        src / "libs" / "portable" / "Cargo.toml",
        client_version,
    )
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
    if profile == "posto":
        patch_incoming_only(cfg_rs)
    elif profile == "controle":
        patch_outgoing_only(cfg_rs)
    index_tis = src / "src" / "ui" / "index.tis"
    install_tis = src / "src" / "ui" / "install.tis"
    windows_rs = src / "src" / "platform" / "windows.rs"
    ui_rs = src / "src" / "ui.rs"
    common_rs = src / "src" / "common.rs"
    if profile == "posto":
        patch_host_only_ui(index_tis, brand)
    patch_shortcut_display_name(windows_rs)
    # UpdateMe antes do patch de URLs (ele ainda contem rustdesk.com no upstream).
    patch_update_check(common_rs)
    patch_update_banner(index_tis)
    patch_update_me_handler(src / "src" / "ui_interface.rs")
    patch_website_urls(index_tis, install_tis)
    patch_install_path(windows_rs, install_tis)
    patch_system_dark_theme(ui_rs, index_tis)
    patch_install_version_label(install_tis)

    # Sanity: chave, host e servidor de produto presentes
    body = cfg_rs.read_text(encoding="utf-8")
    if host not in body or key not in body or "DeskRudder" not in body:
        print("Verificacao falhou apos patch.", file=sys.stderr)
        return 1
    if f'RwLock::new("{host}".to_owned())' not in body:
        print("Verificacao falhou: PROD_RENDEZVOUS_SERVER sem host.", file=sys.stderr)
        return 1
    if profile == "posto":
        if "DeskRudder Acesso Remoto: build so para ser acessado" not in body:
            print("Verificacao falhou: is_incoming_only nao patchado.", file=sys.stderr)
            return 1
        if "DeskRudder Acesso Remoto: build so para controlar" in body:
            print("Verificacao falhou: profile posto nao deve forcar outgoing_only.", file=sys.stderr)
            return 1
    elif profile == "controle":
        if "DeskRudder Acesso Remoto: build so para controlar" not in body:
            print("Verificacao falhou: is_outgoing_only nao patchado.", file=sys.stderr)
            return 1
        if "DeskRudder Acesso Remoto: build so para ser acessado" in body:
            print("Verificacao falhou: profile controle nao deve forcar incoming_only.", file=sys.stderr)
            return 1
    else:
        print(f"Verificacao falhou: profile desconhecido {profile!r}.", file=sys.stderr)
        return 1

    ui_body = ui_rs.read_text(encoding="utf-8")
    our_b64 = base64.b64encode(png_128.read_bytes()).decode("ascii")
    if our_b64 not in ui_body:
        print("Verificacao falhou: get_icon() sem PNG DeskRudder.", file=sys.stderr)
        return 1
    if "fn is_system_dark_theme" not in ui_body or "set_titlebar_dark" not in ui_body:
        print("Verificacao falhou: tema/titlebar ausente em ui.rs.", file=sys.stderr)
        return 1
    if "DwmSetWindowAttribute" not in ui_body:
        print("Verificacao falhou: DWM titlebar ausente.", file=sys.stderr)
        return 1

    index_body = index_tis.read_text(encoding="utf-8")
    if profile == "posto":
        if "Acesso Remoto</div>" not in index_body or "deskrudder_host_logo" not in index_body:
            print("Verificacao falhou: UI host-only sem logo.", file=sys.stderr)
            return 1
        if "data:image/png;base64," not in index_body:
            print("Verificacao falhou: logo host sem data URI.", file=sys.stderr)
            return 1
        if "incoming_only_height_uninstalled" not in index_body:
            print("Verificacao falhou: altura da janela host nao patchada.", file=sys.stderr)
            return 1
        if "incoming_only_min_height_uninstalled" not in index_body:
            print("Verificacao falhou: altura minima da janela host nao patchada.", file=sys.stderr)
            return 1
        if "height:width(100%)" not in index_body:
            print("Verificacao falhou: logo host nao e responsiva.", file=sys.stderr)
            return 1
        if "Versao {handler.get_version()}" not in index_body:
            print("Verificacao falhou: versao nao aparece na UI.", file=sys.stderr)
            return 1
    if "handler.is_system_dark_theme()" not in index_body:
        print("Verificacao falhou: tema do sistema nao ligado.", file=sys.stderr)
        return 1
    if "set_titlebar_dark" not in index_body:
        print("Verificacao falhou: titlebar dark nao ligado na UI.", file=sys.stderr)
        return 1
    if "deskrudder.com.br" not in index_body:
        print("Verificacao falhou: website DeskRudder ausente.", file=sys.stderr)
        return 1
    if "Atualização disponível" not in index_body:
        print("Verificacao falhou: banner de atualizacao ausente.", file=sys.stderr)
        return 1
    if "Atualizar agora" not in index_body or "Instalando..." not in index_body:
        print("Verificacao falhou: fluxo in-app de update incompleto.", file=sys.stderr)
        return 1
    if DOWNLOAD_INSTALLER_URL not in index_body:
        print("Verificacao falhou: URL de download do profile ausente no banner.", file=sys.stderr)
        return 1

    ui_iface = (src / "src" / "ui_interface.rs").read_text(encoding="utf-8")
    if "update_to(&_path)" not in ui_iface:
        print("Verificacao falhou: update_me sem update_to.", file=sys.stderr)
        return 1

    cargo_body = (src / "Cargo.toml").read_text(encoding="utf-8")
    if not re.search(rf'(?m)^version = "{re.escape(client_version)}"$', cargo_body):
        print("Verificacao falhou: Cargo.toml sem CLIENT_VERSION.", file=sys.stderr)
        return 1

    common_body = common_rs.read_text(encoding="utf-8")
    if "do_check_deskrudder_update" not in common_body:
        print("Verificacao falhou: check de update DeskRudder ausente.", file=sys.stderr)
        return 1

    install_body = install_tis.read_text(encoding="utf-8")
    if "Versao {handler.get_version()}" not in install_body:
        print("Verificacao falhou: versao ausente na tela de instalacao.", file=sys.stderr)
        return 1

    win_body = windows_rs.read_text(encoding="utf-8")
    if SHORTCUT_DISPLAY_NAME not in win_body:
        print("Verificacao falhou: atalho sem nome DeskRudder - Acesso Remoto.", file=sys.stderr)
        return 1
    if r"DeskRudder\\Acesso Remoto" not in win_body and "DeskRudder\\\\Acesso Remoto" not in win_body:
        # Fonte: "{}\\DeskRudder\\Acesso Remoto" -> Python ve "{}\\DeskRudder\\Acesso Remoto"
        if "DeskRudder\\Acesso Remoto" not in win_body:
            print("Verificacao falhou: pasta de instalacao Acesso Remoto ausente.", file=sys.stderr)
            return 1

    print(">> OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
