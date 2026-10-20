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
# Pasta sob Program Files (x86): DeskRudder\Acesso Remoto (outros instaladores irao ao lado).
INSTALL_DIR_RELATIVE = r"DeskRudder\Acesso Remoto"
WEBSITE_URL = "https://deskrudder.com.br/"
# Altura minima da janela host-only com o cartao "Instalar" visivel.
HOST_WINDOW_HEIGHT_UNINSTALLED = 580
HOST_WINDOW_HEIGHT_INSTALLED = 480
HOST_WINDOW_WIDTH = 640

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
    w = HOST_WINDOW_WIDTH
    h_un = HOST_WINDOW_HEIGHT_UNINSTALLED
    h_in = HOST_WINDOW_HEIGHT_INSTALLED

    text2, n = re.subn(
        r"const incoming_only_width = 180;",
        f"const incoming_only_width = {w};\n"
        f"const incoming_only_height_uninstalled = {h_un};\n"
        f"const incoming_only_height_installed = {h_in};",
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
        "  view.windowMinSize = (scaleIt(incoming_only_width), "
        "scaleIt((handler.is_installed() || disable_installation) "
        "? incoming_only_height_installed : incoming_only_height_uninstalled));\n"
        "} else {\n"
        "  view.windowMinSize = (scaleIt(560), scaleIt(300));\n"
        "}"
    )
    if old_min not in text:
        raise SystemExit("windowMinSize incoming_only nao encontrado")
    text = text.replace(old_min, new_min, 1)

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

def patch_system_dark_theme(ui_rs: Path, index_tis: Path) -> None:
    """Tema escuro segue o Windows quando o usuario nao fixou a opcao."""
    if not ui_rs.is_file():
        raise SystemExit(f"Falta {ui_rs}")
    text = ui_rs.read_text(encoding="utf-8")

    method = """
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
"""
    anchor = "    pub fn is_custom_client(&self) -> bool {\n        crate::common::is_custom_client()\n    }"
    if "fn is_system_dark_theme" not in text:
        if anchor not in text:
            raise SystemExit("anchor is_custom_client nao encontrado em ui.rs")
        text = text.replace(anchor, anchor + method, 1)

    dispatch_line = "        fn is_custom_client();\n"
    dispatch_new = "        fn is_custom_client();\n        fn is_system_dark_theme();\n"
    if "fn is_system_dark_theme();" not in text:
        if dispatch_line not in text:
            raise SystemExit("dispatch is_custom_client nao encontrado")
        text = text.replace(dispatch_line, dispatch_new, 1)

    ui_rs.write_text(text, encoding="utf-8")
    print("  ui.rs: is_system_dark_theme() (Windows)", flush=True)

    # updateTheme: Y/N manuais; vazio = seguir sistema
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
    new_theme = """function updateTheme() {
    var root_element = self;
    var opt = handler.get_option("allow-darktheme");
    var dark;
    if (opt == "Y") dark = true;
    else if (opt == "N") dark = false;
    else dark = handler.is_system_dark_theme();
    root_element.attributes.toggleClass("darktheme", dark);
}"""
    if old_theme not in idx:
        raise SystemExit("updateTheme() nao encontrado em index.tis")
    index_tis.write_text(idx.replace(old_theme, new_theme, 1), encoding="utf-8")
    print("  index.tis: tema escuro segue Windows (se opcao vazia)", flush=True)


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
    index_tis = src / "src" / "ui" / "index.tis"
    install_tis = src / "src" / "ui" / "install.tis"
    windows_rs = src / "src" / "platform" / "windows.rs"
    ui_rs = src / "src" / "ui.rs"
    patch_host_only_ui(index_tis)
    patch_shortcut_display_name(windows_rs)
    patch_website_urls(index_tis, install_tis)
    patch_install_path(windows_rs, install_tis)
    patch_system_dark_theme(ui_rs, index_tis)

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

    ui_body = ui_rs.read_text(encoding="utf-8")
    our_b64 = base64.b64encode(png_128.read_bytes()).decode("ascii")
    if our_b64 not in ui_body:
        print("Verificacao falhou: get_icon() sem PNG DeskRudder.", file=sys.stderr)
        return 1
    if "fn is_system_dark_theme" not in ui_body:
        print("Verificacao falhou: is_system_dark_theme ausente.", file=sys.stderr)
        return 1

    index_body = index_tis.read_text(encoding="utf-8")
    if "Acesso Remoto</div>" not in index_body or "handler.get_icon()" not in index_body:
        print("Verificacao falhou: UI host-only sem logo.", file=sys.stderr)
        return 1
    if "incoming_only_height_uninstalled" not in index_body:
        print("Verificacao falhou: altura da janela host nao patchada.", file=sys.stderr)
        return 1
    if "handler.is_system_dark_theme()" not in index_body:
        print("Verificacao falhou: tema do sistema nao ligado.", file=sys.stderr)
        return 1
    if "deskrudder.com.br" not in index_body:
        print("Verificacao falhou: website DeskRudder ausente.", file=sys.stderr)
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
