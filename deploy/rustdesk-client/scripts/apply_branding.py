#!/usr/bin/env python3
"""Aplica marca DeskRudder + servidor (Sciter/Duplex; Flutter puxa da instância) num clone do rustdesk.

Nao renomeia o crate `rustdesk` no Cargo (evita quebrar scripts de build).
O CI deve renomear o binario para DeskRudder.exe apos o cargo build — o
instalador/is_installed() procura `{APP_NAME}.exe`.

Altera: APP_NAME, icones, RENDEZVOUS_SERVERS, PROD_RENDEZVOUS_SERVER, RS_PUB_KEY,
nome do atalho Windows, canal de update (version.json).

Profiles (--profile):
  posto     — incoming-only + UI host (PDV)
  controle  — atendente outgoing-only (controla outros, sem ID na frota)

UI (--ui):
  sciter    — producao 1.x.x (CLIENT_VERSION)
  flutter   — 2.x.x (atendente: CLIENT_VERSION_FLUTTER; cliente: CLIENT_VERSION_FLUTTER_CLIENTE)
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
from pathlib import Path

# Nome do produto na UI / atalho (APP_NAME do exe continua DeskRudder para nao quebrar instalacao).
PRODUCT_DISPLAY_NAME = "DeskRemote"
SHORTCUT_DISPLAY_NAME = PRODUCT_DISPLAY_NAME
# Pasta sob Program Files (x86): DeskRudder\Acesso Remoto (outros instaladores irao ao lado).
# Mantida por compatibilidade com is_installed() / update dos PCs ja implantados.
INSTALL_DIR_RELATIVE = r"DeskRudder\Acesso Remoto"
WEBSITE_URL = "https://deskrudder.com.br/"
COPYRIGHT_LINE = "Copyright © 2026 DeskRudder"
# Canais de atualizacao (Release GitHub).
RELEASE_TAG_POSTO = "acesso-remoto-windows"
RELEASE_TAG_CONTROLE = "acesso-remoto-controle-windows"
RELEASE_TAG_CONTROLE_FLUTTER = "acesso-remoto-controle-flutter-windows"
RELEASE_TAG_POSTO_FLUTTER = "acesso-remoto-windows-flutter"
INSTALLER_NAME_POSTO = "DeskRudder-AcessoRemoto.exe"
INSTALLER_NAME_CONTROLE = "DeskRudder-AcessoRemoto-Controle.exe"
INSTALLER_NAME_CONTROLE_FLUTTER = "DeskRudder-AcessoRemoto-Controle-Flutter.exe"
INSTALLER_NAME_POSTO_FLUTTER = "DeskRudder-AcessoRemoto-Flutter.exe"
# Flutter (cliente e atendente): sem hbbs da Duplex no binário. O app puxa
# o servidor da instância (token no cliente; login no atendente).
HOST_FLUTTER_CLIENTE_PENDENTE = "deskremote.invalid"
KEY_FLUTTER_CLIENTE_PENDENTE = "pendente-token"

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

# Textos visíveis injetados em .tis (posto e controle).
# O Sciter Windows lê index.tis / install.tis como Latin-1: UTF-8 literal vira
# mojibake (Atualização → AtualizaÃ§Ã£o). Markup usa entidades HTML; strings
# TIS usam \uXXXX. O Python-fonte pode (e deve) ter acentos em UTF-8.
COPY_BANNER_TITULO = "Atualização disponível"
COPY_BANNER_CORPO_ANTES = f"Há uma versão mais nova do {PRODUCT_DISPLAY_NAME} "
COPY_BANNER_CORPO_SUA = "A sua é "
COPY_BANNER_CTA = "Atualizar agora"
COPY_BANNER_INSTALANDO = "Aplicando atualização (a sessão remota pode cair)..."
COPY_BANNER_ERRO_TITULO = "Erro no download"
COPY_BANNER_ERRO_CORPO = (
    "Não foi possível baixar a atualização. Tente de novo ou baixe pelo painel."
)
COPY_BANNER_BAIXANDO = "Baixando..."
COPY_BANNER_BAIXANDO_PCT = "Baixando %"
COPY_HOST_VERSAO = "Versão"


def sciter_html(texto: str) -> str:
    """Texto visível em markup TIS (ASCII + entidades numéricas)."""
    return texto.encode("ascii", "xmlcharrefreplace").decode("ascii")


def sciter_tis_str(texto: str) -> str:
    """Conteúdo de string TIS entre aspas. Não-ASCII vira \\uXXXX."""
    partes: list[str] = []
    for ch in texto:
        code = ord(ch)
        if code > 127:
            partes.append(f"\\u{code:04X}")
        elif ch == "\\":
            partes.append("\\\\")
        elif ch == '"':
            partes.append('\\"')
        else:
            partes.append(ch)
    return "".join(partes)


def _selftest_sciter_copy() -> None:
    titulo = sciter_html(COPY_BANNER_TITULO)
    if titulo != "Atualiza&#231;&#227;o dispon&#237;vel":
        raise SystemExit(f"selftest sciter_html falhou: {titulo!r}")
    if sciter_html(COPY_HOST_VERSAO) != "Vers&#227;o":
        raise SystemExit("selftest Versão falhou")
    nao = sciter_tis_str("Não")
    if nao != "N\\u00E3o":
        raise SystemExit(f"selftest sciter_tis_str falhou: {nao!r}")
    if any(ord(ch) > 127 for ch in sciter_html(COPY_BANNER_ERRO_CORPO)):
        raise SystemExit("selftest: HTML do erro ainda tem UTF-8 literal")
    if any(ord(ch) > 127 for ch in sciter_tis_str(COPY_BANNER_ERRO_CORPO)):
        raise SystemExit("selftest: string TIS do erro ainda tem UTF-8 literal")


def configurar_canal_update(profile: str, ui: str = "sciter") -> None:
    """Define URLs de version.json / download conforme posto, controle Sciter ou Flutter."""
    global UPDATE_VERSION_JSON_URL, DOWNLOAD_INSTALLER_URL, UPDATE_RELEASE_TAG
    if ui == "flutter" and profile == "posto":
        tag = RELEASE_TAG_POSTO_FLUTTER
        nome = INSTALLER_NAME_POSTO_FLUTTER
    elif ui == "flutter":
        tag = RELEASE_TAG_CONTROLE_FLUTTER
        nome = INSTALLER_NAME_CONTROLE_FLUTTER
    elif profile == "controle":
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


def load_client_version(path: Path, ui: str = "sciter") -> str:
    ver = path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        raise SystemExit(f"CLIENT_VERSION invalida em {path}: {ver!r} (use X.Y.Z)")
    major = int(ver.split(".", 1)[0])
    if ui == "flutter" and major < 2:
        raise SystemExit(
            f"Flutter deve usar versao 2.x.x (arquivo {path.name}={ver!r}); "
            "1.x.x fica no Sciter de producao"
        )
    if ui == "sciter" and major >= 2:
        raise SystemExit(
            f"Sciter deve usar versao 1.x.x (arquivo {path.name}={ver!r}); "
            "2.x.x e do Flutter"
        )
    return ver


def _selftest_client_version_linhas() -> None:
    """Sciter = 1.x.x; Flutter = 2.x.x — canais separados."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        sciter = d / "CLIENT_VERSION"
        flutter = d / "CLIENT_VERSION_FLUTTER"
        sciter.write_text("1.0.14\n", encoding="utf-8")
        flutter.write_text("2.0.0\n", encoding="utf-8")
        if load_client_version(sciter, "sciter") != "1.0.14":
            raise SystemExit("selftest: Sciter 1.0.14")
        if load_client_version(flutter, "flutter") != "2.0.0":
            raise SystemExit("selftest: Flutter 2.0.0")
        try:
            load_client_version(sciter, "flutter")
        except SystemExit:
            pass
        else:
            raise SystemExit("selftest: Flutter nao deve aceitar 1.x.x")
        try:
            load_client_version(flutter, "sciter")
        except SystemExit:
            pass
        else:
            raise SystemExit("selftest: Sciter nao deve aceitar 2.x.x")
    configurar_canal_update("controle", "flutter")
    if UPDATE_RELEASE_TAG != RELEASE_TAG_CONTROLE_FLUTTER:
        raise SystemExit("selftest: canal Flutter nao aponta para tag paralela")
    if INSTALLER_NAME_CONTROLE_FLUTTER not in DOWNLOAD_INSTALLER_URL:
        raise SystemExit("selftest: download Flutter com nome errado")
    configurar_canal_update("posto", "flutter")
    if UPDATE_RELEASE_TAG != RELEASE_TAG_POSTO_FLUTTER:
        raise SystemExit("selftest: canal Flutter cliente nao aponta para tag paralela")
    if INSTALLER_NAME_POSTO_FLUTTER not in DOWNLOAD_INSTALLER_URL:
        raise SystemExit("selftest: download Flutter cliente com nome errado")
    configurar_canal_update("controle", "sciter")
    if UPDATE_RELEASE_TAG != RELEASE_TAG_CONTROLE:
        raise SystemExit("selftest: canal Sciter controle invertido")

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

    copy_flutter_icons(brand, src)


def copy_flutter_icons(brand: Path, src: Path) -> None:
    """Ícones do kit #1253 no Flutter (res/ 1024 + runner Windows)."""
    kit = brand / "kit-1253"
    res = src / "res"
    res.mkdir(parents=True, exist_ok=True)

    src_1024 = kit / "07_flutter_res" / "res-icon-1024.png"
    if not src_1024.is_file():
        src_1024 = brand / "icon-source-1024.png"
    if src_1024.is_file():
        shutil.copy2(src_1024, res / "icon.png")
        print("  flutter res/icon.png (1024)")
    mac = kit / "07_flutter_res" / "res-mac-icon-1024.png"
    if mac.is_file():
        shutil.copy2(mac, res / "mac-icon.png")
        print("  flutter res/mac-icon.png (1024)")

    for kit_name, dst_name in (
        ("res-32.png", "32x32.png"),
        ("res-64.png", "64x64.png"),
        ("res-128.png", "128x128.png"),
    ):
        p = kit / "07_flutter_res" / kit_name
        if p.is_file():
            shutil.copy2(p, res / dst_name)
            print(f"  flutter res/{dst_name}")

    assets = src / "flutter" / "assets"
    if assets.is_dir():
        # Painel esquerdo: 512 LANCZOS (1024 no Flutter 96px virava quadradinho).
        logo = kit / "05_ui_logo" / "ui-logo-512.png"
        if not logo.is_file():
            logo = brand / "ui-logo-512.png"
        if not logo.is_file():
            logo = kit / "07_flutter_res" / "res-icon-1024.png"
        if logo.is_file():
            for name in ("logo.png", "logo_dark.png", "logo_light.png"):
                shutil.copy2(logo, assets / name)
            print(f"  flutter assets/logo.png ({logo.name})", flush=True)

        # Barra de título: ico com borda branca (128 → loadIcon(24) com FilterQuality.high).
        mark = kit / "06_ui_icon" / "ui-icon-128.png"
        if not mark.is_file():
            mark = kit / "01_titlebar" / "titlebar-32.png"
        if not mark.is_file():
            mark = brand / "deskrudder-32.png"
        if mark.is_file():
            shutil.copy2(mark, assets / "icon.png")
            print(f"  flutter assets/icon.png ({mark.name})", flush=True)
        svg = assets / "icon.svg"
        if svg.is_file():
            svg.unlink()
            print("  flutter assets/icon.svg removido (era RustDesk)", flush=True)

    runner = src / "flutter" / "windows" / "runner" / "resources"
    if not runner.is_dir():
        return
    ico = kit / "08_flutter_runner" / "flutter-app-icon.ico"
    if not ico.is_file():
        ico = brand / "icon.ico"
    if ico.is_file():
        shutil.copy2(ico, runner / "app_icon.ico")
        print("  flutter runner app_icon.ico")


# Painel esquerdo Flutter 1.5.0 (desktop_home_page.dart): marca no topo.
_FLUTTER_HOME_POWERED_TOP = """      if (bind.isCustomClient())
        Align(
          alignment: Alignment.center,
          child: loadPowered(context),
        ),
"""

# Engrenagem do modo so-controla, colada no canto inferior.
_FLUTTER_HOME_SETTINGS = """            if (isOutgoingOnly)
              Positioned(
                bottom: 6,
                left: 12,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: InkWell(
                    child: Obx(
                      () => Icon(
                        Icons.settings,
                        color: _editHover.value
                            ? textColor
                            : Colors.grey.withOpacity(0.5),
                        size: 22,
                      ),
                    ),
                    onTap: () => {
                      if (DesktopSettingPage.tabKeys.isNotEmpty)
                        {
                          DesktopSettingPage.switch2page(
                              DesktopSettingPage.tabKeys[0])
                        }
                    },
                    onHover: (value) => _editHover.value = value,
                  ),
                ),
              )
"""

_FLUTTER_HOME_FOOTER_MARKER = "// DeskRemote: marca e versao no rodape do painel esquerdo."
_FLUTTER_INCOMING_STATUS_MARKER = "// DeskRemote: marca acima do status da rede."

# loadPowered no rodape + versao (get_version / CLIENT_VERSION) + engrenagem.
# Só no atendente (outgoing): no cliente o status da rede fica no fluxo do painel.
_FLUTTER_HOME_FOOTER = """            """ + _FLUTTER_HOME_FOOTER_MARKER + """
            if (isOutgoingOnly)
            Positioned(
              left: 8,
              right: 8,
              bottom: 8,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (bind.isCustomClient())
                    Align(
                      alignment: Alignment.center,
                      child: loadPowered(context),
                    ),
                  FutureBuilder<String>(
                    future: bind.mainGetVersion(),
                    builder: (context, snap) {
                      final v = (snap.data ?? '').trim();
                      if (v.isEmpty) {
                        return const SizedBox.shrink();
                      }
                      return Opacity(
                        opacity: 0.5,
                        child: Text(
                          '${translate("Version")} $v',
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(fontSize: 10),
                        ),
                      ).marginOnly(top: 2, bottom: 4);
                    },
                  ),
                  if (isOutgoingOnly)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: InkWell(
                        child: Obx(
                          () => Icon(
                            Icons.settings,
                            color: _editHover.value
                                ? textColor
                                : Colors.grey.withOpacity(0.5),
                            size: 22,
                          ),
                        ),
                        onTap: () => {
                          if (DesktopSettingPage.tabKeys.isNotEmpty)
                            {
                              DesktopSettingPage.switch2page(
                                  DesktopSettingPage.tabKeys[0])
                            }
                        },
                        onHover: (value) => _editHover.value = value,
                      ),
                    ),
                ],
              ),
            )
"""

_FLUTTER_HOME_SCROLL = """                SingleChildScrollView(
                  controller: _leftPaneScrollController,
                  child: Column(
"""

_FLUTTER_HOME_SCROLL_PADDED = """                SingleChildScrollView(
                  controller: _leftPaneScrollController,
                  padding: const EdgeInsets.only(bottom: 64),
                  child: Column(
"""

# Trecho literal do rustdesk 1.5.0 (flutter/lib/desktop/pages/desktop_home_page.dart).
_FLUTTER_INCOMING_STATUS_OLD = """        OnlineStatusWidget(
          onSvcStatusChanged: () {
            if (isInHomePage()) {
              Future.delayed(Duration(milliseconds: 300), () {
                _updateWindowSize();
              });
            }
          },
        ).marginOnly(bottom: 6, right: 6)"""

_FLUTTER_INCOMING_STATUS_RE = re.compile(
    r"(?P<indent>[ \t]*)OnlineStatusWidget\(\s*"
    r"onSvcStatusChanged:\s*\(\)\s*\{\s*"
    r"if\s*\(isInHomePage\(\)\)\s*\{\s*"
    r"Future\.delayed\(Duration\(milliseconds:\s*300\),\s*\(\)\s*\{\s*"
    r"_updateWindowSize\(\);\s*"
    r"\}\);\s*"
    r"\}\s*"
    r"\},\s*"
    r"\)\.marginOnly\(bottom:\s*6,\s*right:\s*6\)",
    re.DOTALL,
)

_FLUTTER_INCOMING_STATUS_NEW = (
    "        "
    + _FLUTTER_INCOMING_STATUS_MARKER
    + """
        if (bind.isCustomClient())
          Align(
            alignment: Alignment.center,
            child: loadPowered(context),
          ),
        FutureBuilder<String>(
          future: bind.mainGetVersion(),
          builder: (context, snap) {
            final v = (snap.data ?? '').trim();
            if (v.isEmpty) {
              return const SizedBox.shrink();
            }
            return Opacity(
              opacity: 0.5,
              child: Text(
                '${translate("Version")} $v',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(fontSize: 10),
              ),
            ).marginOnly(top: 2, bottom: 8);
          },
        ),
        OnlineStatusWidget(
          onSvcStatusChanged: () {
            if (isInHomePage()) {
              Future.delayed(Duration(milliseconds: 300), () {
                _updateWindowSize();
              });
            }
          },
        ).marginOnly(bottom: 6, right: 6, top: 4)"""
)


def apply_flutter_home_footer_text(text: str) -> str:
    """Move 'Desenvolvido por' para o rodape e deixa o status da rede abaixo."""
    if _FLUTTER_HOME_FOOTER_MARKER in text and _FLUTTER_INCOMING_STATUS_MARKER in text:
        return text
    if _FLUTTER_HOME_FOOTER_MARKER not in text:
        if _FLUTTER_HOME_POWERED_TOP not in text:
            raise SystemExit(
                "flutter desktop_home_page: bloco loadPowered no topo nao encontrado"
            )
        if _FLUTTER_HOME_SETTINGS not in text:
            raise SystemExit(
                "flutter desktop_home_page: engrenagem outgoing-only nao encontrada"
            )
        text = text.replace(_FLUTTER_HOME_POWERED_TOP, "", 1)
        text = text.replace(_FLUTTER_HOME_SETTINGS, _FLUTTER_HOME_FOOTER, 1)
        if _FLUTTER_HOME_SCROLL in text:
            text = text.replace(_FLUTTER_HOME_SCROLL, _FLUTTER_HOME_SCROLL_PADDED, 1)
    if _FLUTTER_INCOMING_STATUS_MARKER not in text:
        text = _aplicar_status_incoming(text)
    return text


def _aplicar_status_incoming(text: str) -> str:
    if _FLUTTER_INCOMING_STATUS_OLD in text:
        return text.replace(_FLUTTER_INCOMING_STATUS_OLD, _FLUTTER_INCOMING_STATUS_NEW, 1)
    achado = _FLUTTER_INCOMING_STATUS_RE.search(text)
    if not achado:
        raise SystemExit(
            "flutter desktop_home_page: OnlineStatusWidget do cliente nao encontrado"
        )
    indent = achado.group("indent")
    linhas = _FLUTTER_INCOMING_STATUS_NEW.strip("\n").splitlines()
    base = min((len(ln) - len(ln.lstrip(" ")) for ln in linhas if ln.strip()), default=8)
    rel = [ln[base:] if ln.startswith(" " * base) else ln.lstrip() for ln in linhas]
    novo = "\n".join((indent + ln) if ln else ln for ln in rel)
    return text[: achado.start()] + novo + text[achado.end() :]


def patch_flutter_home_footer(home_dart: Path) -> None:
    """Flutter: marca no rodape do painel esquerdo + versao atual."""
    if not home_dart.is_file():
        return
    text = home_dart.read_text(encoding="utf-8")
    text2 = apply_flutter_home_footer_text(text)
    if text2 == text:
        print("  flutter home: rodape ja patchado", flush=True)
        return
    home_dart.write_text(text2, encoding="utf-8")
    print("  flutter home: Desenvolvido por + versao no rodape", flush=True)


def patch_flutter_powered_url(common_dart: Path) -> None:
    """Link do 'Desenvolvido por' no Flutter -> site DeskRudder."""
    if not common_dart.is_file():
        return
    text = common_dart.read_text(encoding="utf-8")
    old = "launchUrl(Uri.parse('https://rustdesk.com'));"
    url = WEBSITE_URL.rstrip("/")
    new = f"launchUrl(Uri.parse('{url}'));"
    if new in text:
        print("  flutter loadPowered URL ja patchado", flush=True)
        return
    if old not in text:
        raise SystemExit(f"flutter loadPowered URL nao encontrado em {common_dart}")
    common_dart.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  flutter loadPowered URL -> {url}", flush=True)


def _selftest_flutter_home_footer() -> None:
    # Recorte do rustdesk 1.5.0 (desktop_home_page.dart, incoming-only).
    trecho_150 = (
        "    if (isIncomingOnly) {\n"
        "      children.addAll([\n"
        "        Divider(),\n"
        + _FLUTTER_INCOMING_STATUS_OLD
        + "\n      ]);\n"
        "    }\n"
    )
    sample = (
        "      buildTip(context),\n"
        + _FLUTTER_HOME_POWERED_TOP
        + "      Align(child: loadLogo()),\n"
        + _FLUTTER_HOME_SCROLL
        + "                    key: _childKey,\n"
        + _FLUTTER_HOME_SETTINGS
        + "          ],\n"
        + trecho_150
    )
    out = apply_flutter_home_footer_text(sample)
    if _FLUTTER_HOME_FOOTER_MARKER not in out:
        raise SystemExit("selftest flutter: marcador do rodape ausente")
    if _FLUTTER_INCOMING_STATUS_MARKER not in out:
        raise SystemExit("selftest flutter: marca acima do status da rede ausente")
    if "if (isOutgoingOnly)" not in out:
        raise SystemExit("selftest flutter: rodape overlay deve ser so do atendente")
    if "mainGetVersion()" not in out:
        raise SystemExit("selftest flutter: versao ausente no rodape")
    if _FLUTTER_HOME_POWERED_TOP in out:
        raise SystemExit("selftest flutter: Desenvolvido por ainda no topo")
    if out.count("loadPowered(context)") != 2:
        raise SystemExit("selftest flutter: loadPowered no atendente e no cliente")
    if _FLUTTER_INCOMING_STATUS_MARKER not in out or "OnlineStatusWidget(" not in out:
        raise SystemExit("selftest flutter: status da rede deve ficar abaixo da marca")
    if out.find(_FLUTTER_INCOMING_STATUS_MARKER) > out.find("OnlineStatusWidget("):
        raise SystemExit("selftest flutter: Desenvolvido por deve vir antes de Conectando")
    if "EdgeInsets.only(bottom: 64)" not in out:
        raise SystemExit("selftest flutter: padding do scroll ausente")
    out2 = apply_flutter_home_footer_text(out)
    if out2 != out:
        raise SystemExit("selftest flutter: patch do rodape nao e idempotente")
    _selftest_flutter_update_card()
    _selftest_uninstall_completo()
    # Indentação diferente da 1.5.0: cai no regex, não no replace literal.
    variante = "\n".join(("  " + ln) if ln else ln for ln in _FLUTTER_INCOMING_STATUS_OLD.splitlines())
    if _FLUTTER_INCOMING_STATUS_OLD in variante:
        raise SystemExit("selftest flutter: variante deveria divergir do literal 1.5.0")
    if not _FLUTTER_INCOMING_STATUS_RE.search(variante):
        raise SystemExit("selftest flutter: regex nao reconhece OnlineStatusWidget com outro indent")
    via_re = _aplicar_status_incoming(variante)
    if _FLUTTER_INCOMING_STATUS_MARKER not in via_re:
        raise SystemExit("selftest flutter: fallback regex nao inseriu a marca acima do status")
    _selftest_flutter_recent_ui()


def _selftest_flutter_update_card() -> None:
    configurar_canal_update("posto", "flutter")
    sample = (
        _FLUTTER_UPDATE_CARD_OLD
        + "\n      final isToUpdate = (isWindows || isMacOS) && bind.mainIsInstalled();\n"
        "      String btnText = isToUpdate ? 'Update' : 'Download';\n"
        "      GestureTapCallback onPressed = () async {\n"
        "        final Uri url = Uri.parse('https://rustdesk.com/download');\n"
        "        await launchUrl(url);\n"
        "      };\n"
        "      if (isToUpdate) {\n"
        "        onPressed = () {\n"
        "          handleUpdate(updateUrl);\n"
        "        };\n"
        "      }\n"
        "class DesktopHomePage extends StatefulWidget {\n"
    )
    out = apply_flutter_update_card_text(sample)
    if "DeskRemote: canal proprio (version.json)" not in out:
        raise SystemExit("selftest flutter: banner de update nao aparece no custom client")
    if "handleUpdate(updateUrl)" in out:
        raise SystemExit("selftest flutter: banner ainda usa handleUpdate do rustdesk.com")
    if "_deskRemoteBaixarAtualizacao" not in out:
        raise SystemExit("selftest flutter: helper de download do Release ausente")
    if INSTALLER_NAME_POSTO_FLUTTER not in out:
        raise SystemExit("selftest flutter: URL do .exe Flutter cliente ausente no banner")
    if COPY_BANNER_CTA not in out:
        raise SystemExit("selftest flutter: CTA Atualizar agora ausente")
    if apply_flutter_update_card_text(out) != out:
        raise SystemExit("selftest flutter: banner de update nao e idempotente")


def _selftest_uninstall_completo() -> None:
    import tempfile

    sample = (
        '    if exist \\"{path}\\" rd /s /q \\"{path}\\"\n'
        '    if exist \\"{start_menu}\\" rd /s /q \\"{start_menu}\\"\n'
    )
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "windows.rs"
        p.write_text(sample, encoding="utf-8")
        patch_uninstall_completo(p)
        out = p.read_text(encoding="utf-8")
        if "deskremote-dispositivo.json" not in out:
            raise SystemExit("selftest uninstall: json do dispositivo nao e removido")
        if "*.toml" not in out:
            raise SystemExit("selftest uninstall: configs toml nao sao removidas")
        if "%PROGRAMDATA%\\\\DeskRudder" not in out:
            raise SystemExit("selftest uninstall: ProgramData nao e removido")
        if "%PUBLIC%\\\\DeskRudder" not in out:
            raise SystemExit("selftest uninstall: Public nao e removido")
        if "%LOCALAPPDATA%" in out:
            raise SystemExit(
                "selftest uninstall: nao pode apagar LocalAppData — o Instalar faz XCOPY de la"
            )
        patch_uninstall_completo(p)
        if p.read_text(encoding="utf-8") != out:
            raise SystemExit("selftest uninstall: patch nao e idempotente")


_FLUTTER_TABS_ENABLED = """  List<bool> isEnabled = List.from([
    true,
    true,
    !isWeb && bind.mainGetLocalOption(key: "disable-discovery-panel") != "Y",
    !(bind.isDisableAb() || bind.isDisableAccount()),
    !(bind.isDisableGroupPanel() || bind.isDisableAccount()),
  ]);
"""

_FLUTTER_TABS_RECENT_ONLY = """  List<bool> isEnabled = List.from([
    true, // DeskRemote: so Sessoes recentes
    false,
    false,
    false,
    false,
  ]);
"""

_FLUTTER_TABS_RECENT_AND_VINC = """  List<bool> isEnabled = List.from([
    true, // DeskRemote: Recentes e Vinculados
    true, // DeskRemote: aba Vinculados (frota)
    false,
    false,
    false,
  ]);
"""

_FLUTTER_PEERS_LIMIT = """            var peers = snapshot.data!;
            if (peers.length > 1000) peers = peers.sublist(0, 1000);
"""

_FLUTTER_PEERS_LIMIT_10 = """            var peers = snapshot.data!;
            // DeskRemote: 10 ultimas sessoes recentes.
            final maxPeers =
                widget.peers.loadEvent == LoadEvent.recent ? 10 : 1000;
            if (peers.length > maxPeers) peers = peers.sublist(0, maxPeers);
"""

_FLUTTER_PEER_NAME = """    final name = hideUsernameOnCard == true
        ? peer.hostname
        : '${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}';
"""

_FLUTTER_PEER_NAME_ALIAS = """    final name = hideUsernameOnCard == true
        ? peer.hostname
        : '${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}';
    // DeskRemote: nome do vinculo (alias) no lugar do ID.
    final displayName = peer.alias.isNotEmpty ? peer.alias : name;
    final displaySub = peer.alias.isNotEmpty ? name : '';
"""

_FLUTTER_YOUR_DESKTOP_IF = """              if (!isOutgoingOnly)
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    translate("Your Desktop"),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
"""

_FLUTTER_YOUR_DESKTOP_ALWAYS = """              Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    translate("Your Desktop"),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
"""

_FLUTTER_PANE_WIDTH = """        width: isIncomingOnly ? 280.0 : 200.0,
"""

_FLUTTER_PANE_WIDTH_NEW = """        width: isIncomingOnly ? 280.0 : 224.0, // DeskRemote: logo 160 + nome
"""

_FLUTTER_TABBAR_H = "const double kDesktopRemoteTabBarHeight = 28.0;"

_FLUTTER_TABBAR_H_NEW = (
    "const double kDesktopRemoteTabBarHeight = 36.0; "
    "// DeskRemote: ico 24px + nome na barra"
)


def apply_flutter_pane_width_text(text: str) -> str:
    if "DeskRemote: logo 160 + nome" in text:
        return text
    if _FLUTTER_PANE_WIDTH not in text:
        raise SystemExit("flutter desktop_home_page: largura do painel 200 nao encontrada")
    return text.replace(_FLUTTER_PANE_WIDTH, _FLUTTER_PANE_WIDTH_NEW, 1)


def apply_flutter_tabbar_height_text(text: str) -> str:
    if "DeskRemote: ico 24px + nome na barra" in text:
        return text
    if _FLUTTER_TABBAR_H not in text:
        raise SystemExit("flutter consts.dart: kDesktopRemoteTabBarHeight nao encontrado")
    return text.replace(_FLUTTER_TABBAR_H, _FLUTTER_TABBAR_H_NEW, 1)


_FLUTTER_LOAD_LOGO_ALIGN = """      Align(
        alignment: Alignment.center,
        child: loadLogo(),
      ),
"""

_FLUTTER_LOAD_LOGO_NAMED = """      Align(
        alignment: Alignment.center,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            loadLogo(),
            // DeskRemote: nome do app abaixo da logo.
            Padding(
              padding: const EdgeInsets.only(top: 6, bottom: 2),
              child: Text(
                'DeskRemote',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.2,
                    ),
              ),
            ),
          ],
        ),
      ),
"""


def apply_flutter_logo_app_name_text(text: str) -> str:
    if "DeskRemote: nome do app abaixo da logo" in text:
        return text
    if _FLUTTER_LOAD_LOGO_ALIGN not in text:
        raise SystemExit("flutter desktop_home_page: Align loadLogo nao encontrado")
    return text.replace(_FLUTTER_LOAD_LOGO_ALIGN, _FLUTTER_LOAD_LOGO_NAMED, 1)


def apply_flutter_recent_tabs_text(text: str) -> str:
    if "DeskRemote: Recentes e Vinculados" in text:
        return text
    if "DeskRemote: so Sessoes recentes" in text:
        if _FLUTTER_TABS_RECENT_ONLY not in text:
            raise SystemExit("flutter peer_tab_model: patch antigo Recentes nao encontrado")
        return text.replace(_FLUTTER_TABS_RECENT_ONLY, _FLUTTER_TABS_RECENT_AND_VINC, 1)
    if _FLUTTER_TABS_ENABLED not in text:
        raise SystemExit("flutter peer_tab_model: isEnabled nao encontrado")
    return text.replace(_FLUTTER_TABS_ENABLED, _FLUTTER_TABS_RECENT_AND_VINC, 1)


_FLUTTER_TAB_NAMES = """  static const List<String> tabNames = [
    'Recent sessions',
    'Favorites',
    'Discovered',
    'Address book',
    'Accessible devices',
  ];
"""

_FLUTTER_TAB_NAMES_NEW = """  static const List<String> tabNames = [
    'Sessões recentes',
    'Vinculados', // DeskRemote: frota do sistema
    'Discovered',
    'Address book',
    'Accessible devices',
  ];
"""

_FLUTTER_TAB_ICONS = """  static const List<IconData> icons = [
    Icons.access_time_filled,
    Icons.star,
    Icons.explore,
    IconFont.addressBook,
    IconFont.deviceGroupFill,
  ];
"""

_FLUTTER_TAB_ICONS_NEW = """  static const List<IconData> icons = [
    Icons.access_time_filled,
    Icons.link, // DeskRemote: Vinculados
    Icons.explore,
    IconFont.addressBook,
    IconFont.deviceGroupFill,
  ];
"""

_FLUTTER_PEER_TAB_IMPORT = "import 'package:flutter_hbb/common/widgets/peers_view.dart';\n"

_FLUTTER_PEER_TAB_IMPORT_NEW = (
    _FLUTTER_PEER_TAB_IMPORT + "import 'package:flutter_hbb/deskremote/vinculados.dart';\n"
)

_FLUTTER_FAV_VIEW = """    _TabEntry(FavoritePeersView(
      menuPadding: _menuPadding(),
    )),
"""

_FLUTTER_FAV_VIEW_NEW = (
    "    _TabEntry(const DeskRemoteVinculadosView()), "
    "// DeskRemote: aba Vinculados (frota)\n"
)

_FLUTTER_SEARCH_LAND = "      const PeerSearchBar().marginOnly(right: 13),\n"

_FLUTTER_SEARCH_LAND_NEW = """      Offstage(
        // DeskRemote: busca do RustDesk nao filtra Vinculados.
        offstage: model.currentTab == PeerTabIndex.fav.index,
        child: const PeerSearchBar().marginOnly(right: 13),
      ),
"""

_FLUTTER_SEARCH_PORT = """    List<Widget> actions = [
      const PeerSearchBar(),
"""

_FLUTTER_SEARCH_PORT_NEW = """    List<Widget> actions = [
      if (model.currentTab != PeerTabIndex.fav.index) const PeerSearchBar(),
"""

_FLUTTER_VIEW_SWITCH = "      _createPeerViewTypeSwitch(context),\n"

_FLUTTER_VIEW_SWITCH_NEW = """      Offstage(
        offstage: model.currentTab == PeerTabIndex.fav.index, // DeskRemote: Vinculados
        child: _createPeerViewTypeSwitch(context),
      ),
"""

_FLUTTER_SORT_OFF = """      Offstage(
        offstage: model.currentTab == PeerTabIndex.recent.index,
        child: PeerSortDropdown(),
      ),
"""

_FLUTTER_SORT_OFF_NEW = """      Offstage(
        offstage: model.currentTab == PeerTabIndex.recent.index ||
            model.currentTab == PeerTabIndex.fav.index, // DeskRemote: Vinculados
        child: PeerSortDropdown(),
      ),
"""

_FLUTTER_SORT_PORT = (
    "      if (model.currentTab != PeerTabIndex.recent.index) PeerSortDropdown(),\n"
)

_FLUTTER_SORT_PORT_NEW = """      if (model.currentTab != PeerTabIndex.recent.index &&
          model.currentTab != PeerTabIndex.fav.index)
        PeerSortDropdown(),
"""


def apply_flutter_tab_names_text(text: str) -> str:
    if "DeskRemote: frota do sistema" in text:
        return text
    if _FLUTTER_TAB_NAMES not in text:
        raise SystemExit("flutter peer_tab_model: tabNames nao encontrado")
    return text.replace(_FLUTTER_TAB_NAMES, _FLUTTER_TAB_NAMES_NEW, 1)


def apply_flutter_tab_icons_text(text: str) -> str:
    if "DeskRemote: Vinculados" in text and "Icons.link" in text:
        return text
    if _FLUTTER_TAB_ICONS not in text:
        raise SystemExit("flutter peer_tab_model: icons da aba nao encontrado")
    return text.replace(_FLUTTER_TAB_ICONS, _FLUTTER_TAB_ICONS_NEW, 1)


def apply_flutter_vinculados_tab_page_text(text: str) -> str:
    if "DeskRemoteVinculadosView" not in text:
        if _FLUTTER_PEER_TAB_IMPORT_NEW not in text:
            if _FLUTTER_PEER_TAB_IMPORT not in text:
                raise SystemExit("flutter peer_tab_page: import peers_view nao encontrado")
            text = text.replace(_FLUTTER_PEER_TAB_IMPORT, _FLUTTER_PEER_TAB_IMPORT_NEW, 1)
        if _FLUTTER_FAV_VIEW not in text:
            raise SystemExit("flutter peer_tab_page: FavoritePeersView nao encontrado")
        text = text.replace(_FLUTTER_FAV_VIEW, _FLUTTER_FAV_VIEW_NEW, 1)
    if "DeskRemote: busca do RustDesk nao filtra Vinculados" in text:
        return text
    if _FLUTTER_SEARCH_LAND not in text:
        raise SystemExit("flutter peer_tab_page: PeerSearchBar landscape nao encontrado")
    text = text.replace(_FLUTTER_SEARCH_LAND, _FLUTTER_SEARCH_LAND_NEW, 1)
    if _FLUTTER_SEARCH_PORT not in text:
        raise SystemExit("flutter peer_tab_page: PeerSearchBar portrait nao encontrado")
    text = text.replace(_FLUTTER_SEARCH_PORT, _FLUTTER_SEARCH_PORT_NEW, 1)
    if _FLUTTER_VIEW_SWITCH in text:
        text = text.replace(_FLUTTER_VIEW_SWITCH, _FLUTTER_VIEW_SWITCH_NEW, 1)
    if _FLUTTER_SORT_OFF in text:
        text = text.replace(_FLUTTER_SORT_OFF, _FLUTTER_SORT_OFF_NEW, 1)
    if _FLUTTER_SORT_PORT in text:
        text = text.replace(_FLUTTER_SORT_PORT, _FLUTTER_SORT_PORT_NEW, 1)
    return text


def apply_flutter_recent_limit_text(text: str) -> str:
    if "DeskRemote: 10 ultimas sessoes recentes" in text:
        return text
    if _FLUTTER_PEERS_LIMIT not in text:
        raise SystemExit("flutter peers_view: limite 1000 nao encontrado")
    return text.replace(_FLUTTER_PEERS_LIMIT, _FLUTTER_PEERS_LIMIT_10, 1)


_FLUTTER_PEER_ID_LABEL = "peer.alias.isEmpty ? formatID(peer.id) : peer.alias"

# Titulo do tile (lista): so este contexto vira displayName.
_FLUTTER_PEER_TILE_ID = (
    "                        Expanded(\n"
    "                            child: Text(\n"
    f"                          {_FLUTTER_PEER_ID_LABEL},\n"
    "                          overflow: TextOverflow.ellipsis,\n"
    "                          style: Theme.of(context).textTheme.titleSmall,\n"
    "                        )),\n"
    "                      ]).marginOnly(top: isPortrait ? 0 : 2),"
)

_FLUTTER_PEER_TILE_NAME = """                        Expanded(
                            child: Text(
                          displayName,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleSmall,
                        )),
                      ]).marginOnly(top: isPortrait ? 0 : 2),"""

# Barra inferior do cartao (grid): vinculo no topo, maquina aqui; nunca o ID.
_FLUTTER_PEER_CARD_ID = (
    "                            child: Text(\n"
    f"                          {_FLUTTER_PEER_ID_LABEL},\n"
    "                          overflow: TextOverflow.ellipsis,\n"
    "                          style: Theme.of(context).textTheme.titleSmall,\n"
    "                        )),\n"
    "                      ]).paddingSymmetric(vertical: 8)),"
)

_FLUTTER_PEER_CARD_SUB = """                            child: Text(
                          displaySub,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleSmall,
                        )),
                      ]).paddingSymmetric(vertical: 8)),"""


def apply_flutter_peer_card_text(text: str) -> str:
    if "DeskRemote: nome do vinculo" in text:
        return text
    n = text.count(_FLUTTER_PEER_NAME)
    if n < 2:
        raise SystemExit(
            f"flutter peer_card: bloco username@hostname encontrado {n}x (esperado 2)"
        )
    text = text.replace(_FLUTTER_PEER_NAME, _FLUTTER_PEER_NAME_ALIAS)
    if _FLUTTER_PEER_TILE_ID not in text:
        raise SystemExit("flutter peer_card: titulo do tile (ID/alias) nao encontrado")
    text = text.replace(_FLUTTER_PEER_TILE_ID, _FLUTTER_PEER_TILE_NAME, 1)
    if _FLUTTER_PEER_CARD_ID not in text:
        raise SystemExit("flutter peer_card: barra inferior do cartao nao encontrada")
    text = text.replace(_FLUTTER_PEER_CARD_ID, _FLUTTER_PEER_CARD_SUB, 1)
    old_top = """                                      child: Text(
                                        name,
                                        style: const TextStyle(
                                            color: Colors.white70,
                                            fontSize: 12),"""
    new_top = """                                      child: Text(
                                        displayName,
                                        style: const TextStyle(
                                            color: Colors.white70,
                                            fontSize: 12),"""
    if old_top not in text:
        raise SystemExit("flutter peer_card: titulo branco do cartao nao encontrado")
    text = text.replace(old_top, new_top, 1)
    old_sub = """                                child: Text(
                                  name,
                                  style: isPortrait ? null : greyStyle,"""
    new_sub = """                                child: Text(
                                  displaySub.isNotEmpty ? displaySub : '',
                                  style: isPortrait ? null : greyStyle,"""
    if old_sub not in text:
        raise SystemExit("flutter peer_card: subtitulo do tile nao encontrado")
    text = text.replace(old_sub, new_sub, 1)
    # Menus (Excluir etc.) continuam com formatID — displayName nao existe na classe.
    return text


_FLUTTER_LOGO_IMAGE = """          final image = Image.asset(
            asset,
            fit: BoxFit.contain,
            errorBuilder: (ctx, error, stackTrace) {
              return Container();
            },
          );"""

_FLUTTER_LOGO_IMAGE_HQ = """          final image = Image.asset(
            // DeskRemote: nitidez ao reduzir a arte (cache 2x o tamanho na tela).
            asset,
            fit: BoxFit.contain,
            filterQuality: FilterQuality.high,
            isAntiAlias: true,
            cacheWidth: 320,
            gaplessPlayback: true,
            errorBuilder: (ctx, error, stackTrace) {
              return Container();
            },
          );"""


_FLUTTER_LOAD_ICON = """Widget loadIcon(double size) {
  return Image.asset('assets/icon.png',
      width: size,
      height: size,
      errorBuilder: (ctx, error, stackTrace) => SvgPicture.asset(
            'assets/icon.svg',
            width: size,
            height: size,
          ));
}
"""

_FLUTTER_LOAD_ICON_NEW = """Widget loadIcon(double size) {
  return Image.asset('assets/icon.png',
      // DeskRemote: ico com borda branca nítida na barra de título.
      width: size,
      height: size,
      filterQuality: FilterQuality.high,
      isAntiAlias: true,
      errorBuilder: (ctx, error, stackTrace) => SvgPicture.asset(
            'assets/icon.svg',
            width: size,
            height: size,
          ));
}
"""

_FLUTTER_TITLEBAR_ICON_16 = """                          child: loadIcon(16),
"""

_FLUTTER_TITLEBAR_ICON_24 = """                          child: loadIcon(24), // DeskRemote: ico com borda na barra
"""


def apply_flutter_load_icon_hq_text(text: str) -> str:
    if "DeskRemote: ico com borda branca nítida na barra de título" in text:
        return text
    if _FLUTTER_LOAD_ICON not in text:
        raise SystemExit("flutter common.dart: loadIcon nao encontrado")
    return text.replace(_FLUTTER_LOAD_ICON, _FLUTTER_LOAD_ICON_NEW, 1)


def apply_flutter_titlebar_icon_size_text(text: str) -> str:
    if "DeskRemote: ico com borda na barra" in text:
        return text
    if _FLUTTER_TITLEBAR_ICON_16 not in text:
        raise SystemExit("flutter tabbar_widget: loadIcon(16) nao encontrado")
    return text.replace(_FLUTTER_TITLEBAR_ICON_16, _FLUTTER_TITLEBAR_ICON_24, 1)


def apply_flutter_logo_size_text(text: str) -> str:
    if "DeskRemote: logo do painel" not in text:
        old = """          return Container(
            constraints: BoxConstraints(maxWidth: 300, maxHeight: 60),
            child: image,
          ).marginOnly(left: 12, right: 12, top: 12);"""
        new = """          return Container(
            // DeskRemote: logo do painel esquerdo.
            constraints: BoxConstraints(maxWidth: 160, maxHeight: 160),
            child: image,
          ).marginOnly(left: 16, right: 16, top: 16);"""
        if old not in text:
            raise SystemExit("flutter common.dart: tamanho do loadLogo nao encontrado")
        text = text.replace(old, new, 1)
    if "DeskRemote: nitidez" in text:
        return text
    if _FLUTTER_LOGO_IMAGE not in text:
        raise SystemExit("flutter common.dart: Image.asset do loadLogo nao encontrado")
    return text.replace(_FLUTTER_LOGO_IMAGE, _FLUTTER_LOGO_IMAGE_HQ, 1)


_FLUTTER_TABBAR_TITLE = """                            child: const Text(
                              "RustDesk",
                              style: TextStyle(fontSize: 13),
                            ).marginOnly(left: 2))"""

_FLUTTER_TABBAR_TITLE_NEW = """                            child: Text(
                              // DeskRemote: titulo da barra customizada.
                              "DeskRemote",
                              style: TextStyle(
                                fontSize: 13,
                                color: Theme.of(context).colorScheme.onSurface,
                              ),
                            ).marginOnly(left: 2))"""


def apply_flutter_tabbar_text(text: str) -> str:
    if "DeskRemote: titulo da barra customizada" in text:
        return text
    if _FLUTTER_TABBAR_TITLE not in text:
        raise SystemExit("flutter tabbar_widget: titulo RustDesk nao encontrado")
    return text.replace(_FLUTTER_TABBAR_TITLE, _FLUTTER_TABBAR_TITLE_NEW, 1)


_FLUTTER_SERVER_FROM = """  /// from local options
  ServerConfig.fromOptions(Map<String, dynamic> options)
      : idServer = options['custom-rendezvous-server'] ?? "",
        relayServer = options['relay-server'] ?? "",
        apiServer = options['api-server'] ?? "",
        key = options['key'] ?? "";
"""


def apply_flutter_server_defaults_text(text: str, host: str, key: str) -> str:
    """Campos vazios do dialog ID/Relay mostram o Duplex compilado."""
    if "DeskRemote: servidor Duplex" in text:
        return text
    if "class ServerConfig" not in text:
        raise SystemExit("flutter common.dart: class ServerConfig nao encontrada")
    helper = (
        "String _deskremoteOpt(dynamic value, String fallback) {\n"
        "  // DeskRemote: servidor Duplex compilado quando o custom esta vazio.\n"
        "  final s = (value ?? '').toString().trim();\n"
        "  return s.isEmpty ? fallback : s;\n"
        "}\n\n"
    )
    text = text.replace("class ServerConfig", helper + "class ServerConfig", 1)
    if _FLUTTER_SERVER_FROM not in text:
        raise SystemExit("flutter common.dart: ServerConfig.fromOptions nao encontrado")
    new_from = (
        "  /// from local options\n"
        "  ServerConfig.fromOptions(Map<String, dynamic> options)\n"
        f'      : idServer = _deskremoteOpt(options[\'custom-rendezvous-server\'], "{host}"),\n'
        f'        relayServer = _deskremoteOpt(options[\'relay-server\'], "{host}"),\n'
        "        apiServer = options['api-server'] ?? \"\",\n"
        f'        key = _deskremoteOpt(options[\'key\'], "{key}");\n'
    )
    return text.replace(_FLUTTER_SERVER_FROM, new_from, 1)


_FLUTTER_LISTTILE_SIG = """    Widget listTile({
      required IconData icon,
      required String title,
      VoidCallback? onTap,
      Widget? trailing,
      bool showTooltip = false,
      String tooltipMessage = '',
    }) {"""

_FLUTTER_LISTTILE_SIG_NEW = """    Widget listTile({
      required IconData icon,
      required String title,
      VoidCallback? onTap,
      Widget? trailing,
      bool showTooltip = false,
      String tooltipMessage = '',
      String? subtitle,
    }) {"""

_FLUTTER_LISTTILE_RETURN = """      return ListTile(
        leading: Icon(icon, color: _accentColor),
        title: titleWidget,
        enabled: !locked,"""

_FLUTTER_LISTTILE_RETURN_NEW = """      return ListTile(
        leading: Icon(icon, color: _accentColor),
        title: titleWidget,
        subtitle: (subtitle == null || subtitle.isEmpty)
            ? null
            : Text(
                subtitle,
                style: TextStyle(fontSize: 12),
              ),
        enabled: !locked,"""

_FLUTTER_ID_RELAY_TILE = """                listTile(
                  icon: Icons.dns_outlined,
                  title: 'ID/Relay Server',
                  onTap: () => showServerSettings(gFFI.dialogManager, setState),
                ),"""


def apply_flutter_network_text(text: str, host: str) -> str:
    if "DeskRemote: host Duplex na Rede" in text:
        return text
    if _FLUTTER_LISTTILE_SIG not in text:
        raise SystemExit("flutter settings: assinatura listTile nao encontrada")
    text = text.replace(_FLUTTER_LISTTILE_SIG, _FLUTTER_LISTTILE_SIG_NEW, 1)
    if _FLUTTER_LISTTILE_RETURN not in text:
        raise SystemExit("flutter settings: ListTile da Rede nao encontrado")
    text = text.replace(_FLUTTER_LISTTILE_RETURN, _FLUTTER_LISTTILE_RETURN_NEW, 1)
    if _FLUTTER_ID_RELAY_TILE not in text:
        raise SystemExit("flutter settings: tile ID/Relay Server nao encontrado")
    new_tile = (
        "                listTile(\n"
        "                  icon: Icons.dns_outlined,\n"
        "                  title: 'ID/Relay Server',\n"
        "                  // DeskRemote: host Duplex na Rede\n"
        f"                  subtitle: '{host}',\n"
        "                  onTap: () => showServerSettings(gFFI.dialogManager, setState),\n"
        "                ),"
    )
    return text.replace(_FLUTTER_ID_RELAY_TILE, new_tile, 1)


_FLUTTER_ABOUT_TITLE = "        child: _Card(title: translate('About RustDesk'), children: ["
_FLUTTER_ABOUT_TITLE_NEW = (
    "        child: _Card(title: 'Sobre o DeskRemote', children: ["
)
_FLUTTER_ABOUT_VERSION = """              SelectionArea(
                  child: Text('${translate('Version')}: $version')
                      .marginSymmetric(vertical: 4.0)),"""
_FLUTTER_ABOUT_VERSION_NEW = """              SelectionArea(
                  child: Text('${translate('Version')}: $version')
                      .marginSymmetric(vertical: 4.0)),
              SelectionArea(
                  child: const Text('Desenvolvido pela DeskRudder')
                      .marginSymmetric(vertical: 4.0)),"""
_FLUTTER_ABOUT_PRIVACY = """              InkWell(
                  onTap: () {
                    launchUrlString('https://rustdesk.com/privacy.html');
                  },
                  child: Text(
                    translate('Privacy Statement'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
"""
_FLUTTER_ABOUT_SITE = "                    launchUrlString('https://rustdesk.com');"
_FLUTTER_ABOUT_COPYRIGHT = (
    "'Copyright © ${DateTime.now().toString().substring(0, 4)} "
    "Purslane Tech Pte. Ltd.\\n$license'"
)
_FLUTTER_ABOUT_COPYRIGHT_NEW = (
    "'Copyright © ${DateTime.now().toString().substring(0, 4)} DeskRudder\\n$license'"
)


def apply_flutter_about_text(text: str) -> str:
    if "Desenvolvido pela DeskRudder" in text and "Sobre o DeskRemote" in text:
        if "rustdesk.com/privacy" not in text and "Purslane" not in text:
            return text
    if _FLUTTER_ABOUT_TITLE not in text:
        raise SystemExit("flutter settings: titulo About RustDesk nao encontrado")
    text = text.replace(_FLUTTER_ABOUT_TITLE, _FLUTTER_ABOUT_TITLE_NEW, 1)
    if _FLUTTER_ABOUT_VERSION not in text:
        raise SystemExit("flutter settings: linha de versao do Sobre nao encontrada")
    text = text.replace(_FLUTTER_ABOUT_VERSION, _FLUTTER_ABOUT_VERSION_NEW, 1)
    if _FLUTTER_ABOUT_PRIVACY not in text:
        raise SystemExit("flutter settings: Declaracao de privacidade nao encontrada")
    text = text.replace(_FLUTTER_ABOUT_PRIVACY, "", 1)
    if _FLUTTER_ABOUT_SITE not in text:
        raise SystemExit("flutter settings: link Website rustdesk.com nao encontrado")
    url = WEBSITE_URL.rstrip("/")
    text = text.replace(_FLUTTER_ABOUT_SITE, f"                    launchUrlString('{url}');", 1)
    if _FLUTTER_ABOUT_COPYRIGHT not in text:
        raise SystemExit("flutter settings: copyright Purslane nao encontrado")
    return text.replace(_FLUTTER_ABOUT_COPYRIGHT, _FLUTTER_ABOUT_COPYRIGHT_NEW, 1)


def patch_flutter_runner_rc(path: Path) -> None:
    """Metadados Win32 do exe Flutter (Sobre do Windows / propriedades)."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    orig = text
    text = text.replace(
        '"CompanyName", "Purslane Tech Pte. Ltd."',
        '"CompanyName", "DeskRudder"',
    )
    text = text.replace(
        '"FileDescription", "RustDesk Remote Desktop"',
        f'"FileDescription", "{PRODUCT_DISPLAY_NAME}"',
    )
    text = text.replace('"InternalName", "rustdesk"', '"InternalName", "DeskRudder"')
    text = text.replace(
        '"OriginalFilename", "rustdesk.exe"',
        '"OriginalFilename", "DeskRudder.exe"',
    )
    text = text.replace(
        '"ProductName", "RustDesk"',
        f'"ProductName", "{PRODUCT_DISPLAY_NAME}"',
    )
    text, n = re.subn(
        r'"LegalCopyright", "Copyright[^"]*"',
        f'"LegalCopyright", "{COPYRIGHT_LINE}"',
        text,
        count=1,
    )
    if text == orig:
        print("  flutter Runner.rc ja patchado", flush=True)
        return
    if n < 1:
        raise SystemExit(f"LegalCopyright nao encontrado em {path}")
    path.write_text(text, encoding="utf-8")
    print("  flutter Runner.rc: produto/copyright DeskRudder", flush=True)


def apply_flutter_common_vinculo_import_text(text: str) -> str:
    if "package:flutter_hbb/deskremote/sessao.dart" in text:
        return text
    old = "import 'package:flutter_hbb/utils/multi_window_manager.dart';\n"
    if old not in text:
        raise SystemExit("flutter common.dart: import multi_window_manager nao encontrado")
    return text.replace(
        old,
        old + "import 'package:flutter_hbb/deskremote/sessao.dart';\n",
        1,
    )


_FLUTTER_INAPP_ALIAS_UPSTREAM = """    await rustDeskWinManager.newRemoteDesktop(id,
        password: password,
        isSharedPassword: isSharedPassword,
        forceRelay: forceRelay);
"""

_FLUTTER_INAPP_ALIAS_OLD = """    // DeskRemote: reusa alias do vinculo (painel) ao conectar pelo ID/cartao.
    final alias = bind.mainGetPeerOptionSync(id: id, key: 'alias').trim();
    await rustDeskWinManager.newRemoteDesktop(id,
        password: password,
        isSharedPassword: isSharedPassword,
        forceRelay: forceRelay,
        title: alias.isEmpty ? null : alias);
"""

_FLUTTER_INAPP_ALIAS_NEW = """    // DeskRemote: busca vinculo na API no Conectar (Recentes/ID).
    var alias = bind.mainGetPeerOptionSync(id: id, key: 'alias').trim();
    if (alias.isEmpty) {
      alias = (await buscarRotuloVinculoDeskRemote(id))?.trim() ?? '';
      if (alias.isNotEmpty) {
        await bind.mainSetPeerAlias(id: id, alias: alias);
      }
    }
    await rustDeskWinManager.newRemoteDesktop(id,
        password: password,
        isSharedPassword: isSharedPassword,
        forceRelay: forceRelay,
        title: alias.isEmpty ? null : alias);
"""


def _rotulo_sessao_vinculo(vinculo: dict) -> str:
    """Espelho de rotuloSessaoVinculo (Dart + acessoRemotoUrl.mjs)."""
    rotulo = str(vinculo.get("rotulo_nome") or "").strip() or "Equipamento"
    codigo = str(vinculo.get("pdv_codigo") or "").strip()
    base = f"{rotulo} {codigo}" if codigo else rotulo
    empresa = str(vinculo.get("empresa_nome") or "").strip()
    if not empresa:
        empresa = str(vinculo.get("rede_nome") or "").strip()
    return f"{empresa} · {base}" if empresa else base


_FLUTTER_ROTULO_SESSAO_FN = """String rotuloSessaoVinculo(Map<String, dynamic> vinculo) {
  final rotulo = (vinculo['rotulo_nome'] ?? '').toString().trim();
  final nome = rotulo.isEmpty ? 'Equipamento' : rotulo;
  final codigo = (vinculo['pdv_codigo'] ?? '').toString().trim();
  final base = codigo.isEmpty ? nome : '$nome $codigo';
  var empresa = (vinculo['empresa_nome'] ?? '').toString().trim();
  if (empresa.isEmpty) {
    empresa = (vinculo['rede_nome'] ?? '').toString().trim();
  }
  return empresa.isEmpty ? base : '$empresa · $base';
}"""


_FLUTTER_INAPP_SERVIDOR = (
    "    // DeskRemote: aplica o servidor da instancia no Conectar.\n"
    "    await aplicarServidorDaContaDeskRemote(silencioso: true);\n"
)

_FLUTTER_INAPP_ALIAS_COM_SERVIDOR = (
    _FLUTTER_INAPP_SERVIDOR + _FLUTTER_INAPP_ALIAS_NEW
)


def apply_flutter_inapp_alias_text(text: str) -> str:
    if "DeskRemote: aplica o servidor da instancia no Conectar" in text:
        return text
    if "DeskRemote: busca vinculo na API no Conectar" in text:
        return text.replace(
            "    // DeskRemote: busca vinculo na API no Conectar (Recentes/ID).\n",
            _FLUTTER_INAPP_SERVIDOR
            + "    // DeskRemote: busca vinculo na API no Conectar (Recentes/ID).\n",
            1,
        )
    if _FLUTTER_INAPP_ALIAS_OLD in text:
        return text.replace(_FLUTTER_INAPP_ALIAS_OLD, _FLUTTER_INAPP_ALIAS_COM_SERVIDOR, 1)
    if _FLUTTER_INAPP_ALIAS_UPSTREAM not in text:
        raise SystemExit("flutter common.dart: connectMainDesktop newRemoteDesktop nao encontrado")
    return text.replace(_FLUTTER_INAPP_ALIAS_UPSTREAM, _FLUTTER_INAPP_ALIAS_COM_SERVIDOR, 1)


_FLUTTER_HANDLE_URI_VARS = """  String? password;
  String? switchUuid;
  bool? forceRelay;
"""

_FLUTTER_HANDLE_URI_VARS_TITLE = """  String? password;
  String? switchUuid;
  bool? forceRelay;
  String? title;
"""

_FLUTTER_HANDLE_URI_PW = """      case '--password':
        password = args[i + 1];
        i++;
        break;
      case '--switch_uuid':
"""

_FLUTTER_HANDLE_URI_PW_TITLE = """      case '--password':
        password = args[i + 1];
        i++;
        break;
      case '--title':
        title = args[i + 1];
        i++;
        break;
      case '--switch_uuid':
"""


def apply_flutter_connect_title_text(text: str) -> str:
    if "DeskRemote: aplica o servidor da instancia antes de conectar" in text:
        return text
    if "DeskRemote: busca vinculo na API se o painel nao mandou name=" in text:
        text = text.replace(
            "          // DeskRemote: busca vinculo na API se o painel nao mandou name=.\n",
            "          // DeskRemote: aplica o servidor da instancia antes de conectar.\n"
            "          await aplicarServidorDaContaDeskRemote(silencioso: true);\n"
            "          // DeskRemote: busca vinculo na API se o painel nao mandou name=.\n",
            1,
        )
        if 'param["name"]' in text:
            return text
    # Só o bloco do handleUriLink — um String? title; solto no arquivo não conta.
    if _FLUTTER_HANDLE_URI_VARS_TITLE not in text:
        if _FLUTTER_HANDLE_URI_VARS not in text:
            raise SystemExit("flutter common.dart: variaveis do handleUriLink nao encontradas")
        text = text.replace(_FLUTTER_HANDLE_URI_VARS, _FLUTTER_HANDLE_URI_VARS_TITLE, 1)
    if _FLUTTER_HANDLE_URI_PW_TITLE not in text:
        if _FLUTTER_HANDLE_URI_PW not in text:
            raise SystemExit("flutter common.dart: --password do handleUriLink nao encontrado")
        text = text.replace(_FLUTTER_HANDLE_URI_PW, _FLUTTER_HANDLE_URI_PW_TITLE, 1)
    old_call = """      case UriLinkType.remoteDesktop:
        Future.delayed(Duration.zero, () {
          rustDeskWinManager.newRemoteDesktop(id!,
              password: password,
              switchUuid: switchUuid,
              forceRelay: forceRelay);
        });
"""
    old_call_alias = """      case UriLinkType.remoteDesktop:
        Future.delayed(Duration.zero, () async {
          // DeskRemote: alias do vinculo (name= do deskrudder://).
          if (title != null && title.isNotEmpty) {
            await bind.mainSetPeerAlias(id: id!, alias: title);
          }
          rustDeskWinManager.newRemoteDesktop(id!,
              password: password,
              switchUuid: switchUuid,
              forceRelay: forceRelay,
              title: title);
        });
"""
    new_call = """      case UriLinkType.remoteDesktop:
        Future.delayed(Duration.zero, () async {
          // DeskRemote: aplica o servidor da instancia antes de conectar.
          await aplicarServidorDaContaDeskRemote(silencioso: true);
          // DeskRemote: busca vinculo na API se o painel nao mandou name=.
          // Espera até 5s: a aba é outro engine e o título só entra nos params.
          var tituloSessao = title?.trim();
          if (tituloSessao == null || tituloSessao.isEmpty) {
            tituloSessao = await buscarRotuloVinculoDeskRemote(id!);
          }
          if (tituloSessao != null && tituloSessao.isNotEmpty) {
            await bind.mainSetPeerAlias(id: id!, alias: tituloSessao);
          }
          rustDeskWinManager.newRemoteDesktop(id!,
              password: password,
              switchUuid: switchUuid,
              forceRelay: forceRelay,
              title: tituloSessao);
        });
"""
    if "DeskRemote: aplica o servidor da instancia antes de conectar" not in text:
        if old_call_alias in text:
            text = text.replace(old_call_alias, new_call, 1)
        elif old_call in text:
            text = text.replace(old_call, new_call, 1)
        else:
            raise SystemExit("flutter common.dart: newRemoteDesktop nao encontrado")
    if 'param["name"]' in text:
        return text
    old_q = """    if (password != null) args.addAll(['--password', password]);
    String? switch_uuid = param["switch_uuid"];
"""
    new_q = """    if (password != null) args.addAll(['--password', password]);
    String? titleName = param["name"];
    if (titleName != null && titleName.isNotEmpty) {
      args.addAll(['--title', titleName]);
    }
    String? switch_uuid = param["switch_uuid"];
"""
    if old_q not in text:
        raise SystemExit("flutter common.dart: query password->args nao encontrado")
    return text.replace(old_q, new_q, 1)


def apply_flutter_core_main_title_text(text: str) -> str:
    if "DeskRemote: --title vira name=" in text:
        return text
    old = """            "--password" => {
                if let Some(password) = args.next() {
                    param_array.push(format!("password={password}"));
                }
            }
            "--relay" => {
                param_array.push(format!("relay=true"));
            }
"""
    new = """            "--password" => {
                if let Some(password) = args.next() {
                    param_array.push(format!("password={password}"));
                }
            }
            "--title" => {
                // DeskRemote: --title vira name= no uni-link (alias do vinculo).
                if let Some(title) = args.next() {
                    if let Some(ref peer_id) = id {
                        let mut cfg = hbb_common::config::PeerConfig::load(peer_id);
                        cfg.options.insert("alias".to_owned(), title.clone());
                        cfg.store(peer_id);
                    }
                    let encoded = {
                        let mut out = String::new();
                        for b in title.as_bytes() {
                            match b {
                                b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9'
                                | b'-' | b'_' | b'.' | b'~' => out.push(*b as char),
                                _ => out.push_str(&format!("%{:02X}", b)),
                            }
                        }
                        out
                    };
                    param_array.push(format!("name={encoded}"));
                }
            }
            "--relay" => {
                param_array.push(format!("relay=true"));
            }
"""
    if old not in text:
        raise SystemExit("core_main.rs: --password do invoke_new_connection nao encontrado")
    return text.replace(old, new, 1)


_FLUTTER_TAB_LABEL = """String getDesktopTabLabel(String peerId, String alias) {
  String label = alias.isEmpty ? peerId : alias;
  try {
    String peer = bind.mainGetPeerSync(id: peerId);
    Map<String, dynamic> config = jsonDecode(peer);
    if (config['info']['hostname'] is String) {
      String hostname = config['info']['hostname'];
      if (hostname.isNotEmpty &&
          !label.toLowerCase().contains(hostname.toLowerCase())) {
        label += "@$hostname";
      }
    }
  } catch (e) {
    debugPrint("Failed to get hostname:$e");
  }
  return label;
}
"""

_FLUTTER_TAB_LABEL_NEW = """String getDesktopTabLabel(String peerId, String alias) {
  // DeskRemote: vinculo (alias) ou usuario@host na aba; nunca o ID.
  final aliasTrim = alias.trim();
  if (aliasTrim.isNotEmpty) {
    return aliasTrim;
  }
  try {
    String peer = bind.mainGetPeerSync(id: peerId);
    Map<String, dynamic> config = jsonDecode(peer);
    final info = config['info'];
    if (info is Map) {
      final username =
          info['username'] is String ? (info['username'] as String).trim() : '';
      final hostname =
          info['hostname'] is String ? (info['hostname'] as String).trim() : '';
      if (username.isNotEmpty && hostname.isNotEmpty) {
        return '$username@$hostname';
      }
      if (hostname.isNotEmpty) {
        return hostname;
      }
      if (username.isNotEmpty) {
        return username;
      }
    }
  } catch (e) {
    debugPrint("Failed to get hostname:$e");
  }
  return peerId;
}
"""


def apply_flutter_session_tab_label_text(text: str) -> str:
    if "DeskRemote: vinculo (alias) ou usuario@host na aba" in text:
        return text
    if _FLUTTER_TAB_LABEL not in text:
        raise SystemExit("flutter common.dart: getDesktopTabLabel nao encontrado")
    return text.replace(_FLUTTER_TAB_LABEL, _FLUTTER_TAB_LABEL_NEW, 1)


_FLUTTER_TAB_GETTER = """  static RxString tablabelGetter(String peerId) {
    final alias = bind.mainGetPeerOptionSync(id: peerId, key: 'alias');
    return RxString(getDesktopTabLabel(peerId, alias));
  }
"""

_FLUTTER_TAB_GETTER_NEW = """  static RxString tablabelGetter(String peerId) {
    // DeskRemote: aba reage a alias e a usuario@host apos o peer_info.
    final alias = bind.mainGetPeerOptionSync(id: peerId, key: 'alias');
    final label = getDesktopTabLabel(peerId, alias);
    final tag = PeerStringOption.tag(peerId, 'tabLabel');
    if (!Get.isRegistered<RxString>(tag: tag)) {
      PeerStringOption.init(peerId, 'tabLabel', () => label);
    } else if (alias.trim().isNotEmpty) {
      PeerStringOption.find(peerId, 'tabLabel').value = label;
    }
    return PeerStringOption.find(peerId, 'tabLabel');
  }
"""

_FLUTTER_TABBAR_SHARED_IMPORT = "import 'package:flutter_hbb/common.dart';\n"
_FLUTTER_TABBAR_SHARED_IMPORT_NEW = (
    "import 'package:flutter_hbb/common.dart';\n"
    "import 'package:flutter_hbb/common/shared_state.dart';\n"
)


def apply_flutter_session_tab_getter_text(text: str) -> str:
    if "DeskRemote: aba reage a alias" in text:
        return text
    if _FLUTTER_TABBAR_SHARED_IMPORT_NEW not in text:
        if _FLUTTER_TABBAR_SHARED_IMPORT not in text:
            raise SystemExit("flutter tabbar_widget: import common.dart nao encontrado")
        text = text.replace(
            _FLUTTER_TABBAR_SHARED_IMPORT, _FLUTTER_TABBAR_SHARED_IMPORT_NEW, 1
        )
    n = text.count(_FLUTTER_TAB_GETTER)
    if n < 1:
        raise SystemExit("flutter tabbar_widget: tablabelGetter nao encontrado")
    return text.replace(_FLUTTER_TAB_GETTER, _FLUTTER_TAB_GETTER_NEW)


_FLUTTER_PEER_INFO_HOST = """    _pi.username = evt['username'];
    _pi.hostname = evt['hostname'];
"""

_FLUTTER_PEER_INFO_HOST_NEW = """    _pi.username = evt['username'];
    _pi.hostname = evt['hostname'];
    // DeskRemote: atualiza a aba quando chega usuario/host.
    try {
      final alias = bind.mainGetPeerOptionSync(id: peerId, key: 'alias');
      final tabName = getDesktopTabLabel(peerId, alias);
      final rxTabLabel = PeerStringOption.find(peerId, 'tabLabel');
      final current = rxTabLabel.value.trim();
      final looksLikeId = current.isEmpty ||
          current == peerId ||
          current.startsWith('$peerId@');
      if (alias.trim().isNotEmpty || looksLikeId) {
        if (rxTabLabel.value != tabName) {
          rxTabLabel.value = tabName;
        }
      }
    } catch (_) {}
"""


def apply_flutter_peer_info_tab_text(text: str) -> str:
    if "DeskRemote: atualiza a aba quando chega usuario/host" in text:
        return text
    if _FLUTTER_PEER_INFO_HOST not in text:
        raise SystemExit("flutter model.dart: username/hostname do peer_info nao encontrados")
    return text.replace(_FLUTTER_PEER_INFO_HOST, _FLUTTER_PEER_INFO_HOST_NEW, 1)


_FLUTTER_CORE_POS_PASSWORD = """            _ => {}
        }
    }
    let mut uni_links = Default::default();
"""

_FLUTTER_CORE_POS_PASSWORD_NEW = """            _ => {
                // DeskRemote: senha posicional (`--connect ID SENHA --title ...`).
                if !arg.starts_with('-')
                    && !param_array.iter().any(|p| p.starts_with("password="))
                {
                    param_array.push(format!("password={arg}"));
                }
            }
        }
    }
    let mut uni_links = Default::default();
"""


def apply_flutter_core_main_password_text(text: str) -> str:
    if "DeskRemote: senha posicional" in text:
        return text
    if _FLUTTER_CORE_POS_PASSWORD not in text:
        raise SystemExit("core_main.rs: fallback _ => {} do invoke_new_connection nao encontrado")
    return text.replace(_FLUTTER_CORE_POS_PASSWORD, _FLUTTER_CORE_POS_PASSWORD_NEW, 1)


_FLUTTER_SHOW_TITLE_FALSE = """    this.showLogo = true,
    this.showTitle = false,
"""

_FLUTTER_SHOW_TITLE_TRUE = """    this.showLogo = true,
    this.showTitle = true, // DeskRemote: nome do app na barra (claro e escuro).
"""

_FLUTTER_MAIN_TAB = """            body: DesktopTab(
              controller: tabController,
"""

_FLUTTER_MAIN_TAB_NEW = """            body: DesktopTab(
              controller: tabController,
              showTitle: true,
"""

_FLUTTER_COLD_START = (
    "        return if res { None } else { Some(Vec::new()) };"
)

_FLUTTER_COLD_START_NEW = """        // DeskRemote: no frio, entrega o uni-link ao Flutter (name= do vinculo).
        return if res { None } else { Some(vec![uni_links]) };
"""


def apply_flutter_show_title_text(text: str) -> str:
    if "DeskRemote: nome do app na barra" in text:
        return text
    if _FLUTTER_SHOW_TITLE_FALSE not in text:
        raise SystemExit("flutter tabbar_widget: showTitle default nao encontrado")
    return text.replace(_FLUTTER_SHOW_TITLE_FALSE, _FLUTTER_SHOW_TITLE_TRUE, 1)


def apply_flutter_main_show_title_text(text: str) -> str:
    if "showTitle: true" in text:
        return text
    if _FLUTTER_MAIN_TAB not in text:
        raise SystemExit("flutter desktop_tab_page: DesktopTab da home nao encontrado")
    return text.replace(_FLUTTER_MAIN_TAB, _FLUTTER_MAIN_TAB_NEW, 1)


_FLUTTER_AUTH_IMPORT = "import 'package:flutter_hbb/desktop/pages/desktop_home_page.dart';\n"
_FLUTTER_AUTH_IMPORT_NEW = (
    "import 'package:flutter_hbb/desktop/pages/desktop_home_page.dart';\n"
    "import 'package:flutter_hbb/deskremote/auth_gate.dart';\n"
)

_FLUTTER_HOME_PAGE_CHILD = """        page: DesktopHomePage(
          key: const ValueKey(kTabLabelHomePage),
        )));
"""

_FLUTTER_HOME_PAGE_GATED = """        page: DeskRemoteAuthGate(
          // DeskRemote: Recentes/Conectar exigem login DeskRudder.
          child: DesktopHomePage(
            key: const ValueKey(kTabLabelHomePage),
          ),
        )));
"""

_FLUTTER_ENROLL_IMPORT_NEW = (
    "import 'package:flutter_hbb/desktop/pages/desktop_home_page.dart';\n"
    "import 'package:flutter_hbb/deskremote/enroll_gate.dart';\n"
)

_FLUTTER_HOME_PAGE_ENROLLED = """        page: DeskRemoteEnrollGate(
          // DeskRemote: cliente so abre depois do token de instalacao.
          child: DesktopHomePage(
            key: const ValueKey(kTabLabelHomePage),
          ),
        )));
"""

_FLUTTER_OVERLAY_DIR = Path(__file__).resolve().parent.parent / "flutter-overlay"


def copy_flutter_auth_overlay(src: Path) -> None:
    origin = _FLUTTER_OVERLAY_DIR / "lib" / "deskremote"
    dest = src / "flutter" / "lib" / "deskremote"
    if not origin.is_dir():
        raise SystemExit(f"overlay deskremote ausente: {origin}")
    dest.mkdir(parents=True, exist_ok=True)
    copiados = 0
    for f in sorted(origin.glob("*.dart")):
        shutil.copy2(f, dest / f.name)
        copiados += 1
        print(f"  flutter overlay {f.name}", flush=True)
    nomes = {p.name for p in origin.glob("*.dart")}
    if not {
        "sessao.dart",
        "auth_gate.dart",
        "vinculados.dart",
        "enroll.dart",
        "enroll_gate.dart",
    } <= nomes:
        raise SystemExit("overlay deskremote incompleto (login + enroll)")
    if copiados < 5:
        raise SystemExit("overlay deskremote incompleto (esperados 5 dart)")


def apply_flutter_auth_gate_text(text: str) -> str:
    if "DeskRemote: Recentes/Conectar exigem login DeskRudder" in text:
        return text
    if _FLUTTER_AUTH_IMPORT_NEW not in text:
        if _FLUTTER_AUTH_IMPORT not in text:
            raise SystemExit("flutter desktop_tab_page: import home nao encontrado")
        text = text.replace(_FLUTTER_AUTH_IMPORT, _FLUTTER_AUTH_IMPORT_NEW, 1)
    if _FLUTTER_HOME_PAGE_CHILD not in text:
        raise SystemExit("flutter desktop_tab_page: DesktopHomePage da home nao encontrado")
    return text.replace(_FLUTTER_HOME_PAGE_CHILD, _FLUTTER_HOME_PAGE_GATED, 1)


def apply_flutter_lock_password_text(text: str) -> str:
    """Cliente posto: senha permanente so muda no painel (#1283)."""
    if "DeskRemote: senha permanente so muda no painel" in text:
        return text
    old = "bool isChangePermanentPasswordDisabled() =>"
    if old not in text:
        raise SystemExit("flutter common.dart: isChangePermanentPasswordDisabled nao encontrado")
    return text.replace(
        old,
        "bool isChangePermanentPasswordDisabled() =>\n"
        "    // DeskRemote: senha permanente so muda no painel.\n"
        "    true ||",
        1,
    )


def apply_flutter_hide_password_edit_text(text: str) -> str:
    """Remove o lapis de senha na home do cliente."""
    if "DeskRemote: senha permanente so no painel" in text:
        return text
    new_text, n = re.subn(
        r"if \(!bind\.isDisableSettings\(\)\)(\s+InkWell\(\s+child: Tooltip\(\s+message: translate\('Change Password'\),)",
        r"if (!bind.isDisableSettings() && false /* DeskRemote: senha permanente so no painel */)\1",
        text,
        count=1,
    )
    if n < 1:
        raise SystemExit("flutter home: lapis Change Password nao encontrado")
    return new_text


_FLUTTER_UPDATE_CARD_OLD = """    if (!bind.isCustomClient() &&
        updateUrl.isNotEmpty &&
        !isCardClosed &&
        bind.mainUriPrefixSync().contains('rustdesk')) {"""

_FLUTTER_UPDATE_HELPER_MARKER = "// DeskRemote: baixa o .exe do Release e aplica --update."


def apply_flutter_update_card_text(text: str) -> str:
    """Mostra o banner de atualizacao no Flutter (o upstream esconde em custom client)."""
    if "DeskRemote: canal proprio (version.json)" in text:
        return text
    if _FLUTTER_UPDATE_CARD_OLD not in text:
        raise SystemExit("flutter home: condicao do banner de update nao encontrada")
    text = text.replace(
        _FLUTTER_UPDATE_CARD_OLD,
        "    // DeskRemote: canal proprio (version.json), mesmo sendo custom client.\n"
        "    if (updateUrl.isNotEmpty && !isCardClosed) {",
        1,
    )
    old_press = """        onPressed = () {
          handleUpdate(updateUrl);
        };"""
    new_press = """        onPressed = () {
          // DeskRemote: URL do .exe no Release (nao rustdesk.com / tag).
          _deskRemoteBaixarAtualizacao();
        };"""
    if old_press not in text:
        raise SystemExit("flutter home: handleUpdate do banner nao encontrado")
    text = text.replace(old_press, new_press, 1)
    old_to_update = (
        "      final isToUpdate = (isWindows || isMacOS) && bind.mainIsInstalled();\n"
        "      String btnText = isToUpdate ? 'Update' : 'Download';"
    )
    new_to_update = (
        "      final isToUpdate = true;\n"
        f"      String btnText = '{COPY_BANNER_CTA}';"
    )
    if old_to_update not in text:
        raise SystemExit("flutter home: isToUpdate do banner nao encontrado")
    text = text.replace(old_to_update, new_to_update, 1)
    if _FLUTTER_UPDATE_HELPER_MARKER not in text:
        helper = (
            f"{_FLUTTER_UPDATE_HELPER_MARKER}\n"
            "void _deskRemoteBaixarAtualizacao() {\n"
            f"  const exeUrl = '{DOWNLOAD_INSTALLER_URL}';\n"
            "  final downloadId = SimpleWrapper('');\n"
            "  final onCanceled = SimpleWrapper(() {});\n"
            "  gFFI.dialogManager.dismissAll();\n"
            "  gFFI.dialogManager.show((setState, close, context) {\n"
            "    return CustomAlertDialog(\n"
            f"      title: Text('{COPY_BANNER_BAIXANDO}'),\n"
            "      content: UpdateProgress(exeUrl, exeUrl, downloadId, onCanceled)\n"
            "          .marginSymmetric(horizontal: 8)\n"
            "          .paddingOnly(top: 12),\n"
            "      actions: [\n"
            "        dialogButton(translate('Cancel'), onPressed: () async {\n"
            "          onCanceled.value();\n"
            "          await bind.mainSetCommon(\n"
            "              key: 'cancel-downloader', value: downloadId.value);\n"
            "          close();\n"
            "        }, isOutline: true),\n"
            "      ],\n"
            "    );\n"
            "  });\n"
            "}\n\n"
        )
        anchor = "class DesktopHomePage extends StatefulWidget {"
        if anchor not in text:
            raise SystemExit("flutter home: class DesktopHomePage nao encontrada para o helper de update")
        text = text.replace(anchor, helper + anchor, 1)
    return text


def apply_flutter_enroll_gate_text(text: str) -> str:
    if "DeskRemote: cliente so abre depois do token de instalacao" in text:
        return text
    if _FLUTTER_ENROLL_IMPORT_NEW not in text:
        if _FLUTTER_AUTH_IMPORT not in text:
            raise SystemExit("flutter desktop_tab_page: import home nao encontrado")
        text = text.replace(_FLUTTER_AUTH_IMPORT, _FLUTTER_ENROLL_IMPORT_NEW, 1)
    if _FLUTTER_HOME_PAGE_CHILD not in text:
        raise SystemExit("flutter desktop_tab_page: DesktopHomePage da home nao encontrado")
    return text.replace(_FLUTTER_HOME_PAGE_CHILD, _FLUTTER_HOME_PAGE_ENROLLED, 1)


def apply_flutter_core_main_cold_start_text(text: str) -> str:
    if "DeskRemote: no frio, entrega o uni-link" in text:
        return text
    if _FLUTTER_COLD_START not in text:
        raise SystemExit("core_main.rs: retorno vazio do invoke_new_connection nao encontrado")
    return text.replace(_FLUTTER_COLD_START, _FLUTTER_COLD_START_NEW, 1)


def apply_flutter_session_window_title_text(text: str) -> str:
    if "DeskRemote: title na janela da sessao" in text:
        return text
    old_rd = """  Future<MultiWindowCallResult> newRemoteDesktop(
    String remoteId, {
    String? password,
    bool? isSharedPassword,
    String? switchUuid,
    bool? forceRelay,
  }) async {
    return await newSession(
      WindowType.RemoteDesktop,
      kWindowEventNewRemoteDesktop,
      remoteId,
      _remoteDesktopWindows,
      password: password,
      forceRelay: forceRelay,
      switchUuid: switchUuid,
      isSharedPassword: isSharedPassword,
    );
  }
"""
    new_rd = """  Future<MultiWindowCallResult> newRemoteDesktop(
    String remoteId, {
    String? password,
    bool? isSharedPassword,
    String? switchUuid,
    bool? forceRelay,
    String? title,
  }) async {
    return await newSession(
      WindowType.RemoteDesktop,
      kWindowEventNewRemoteDesktop,
      remoteId,
      _remoteDesktopWindows,
      password: password,
      forceRelay: forceRelay,
      switchUuid: switchUuid,
      isSharedPassword: isSharedPassword,
      title: title,
    );
  }
"""
    if old_rd not in text:
        raise SystemExit("flutter multi_window_manager: newRemoteDesktop nao encontrado")
    text = text.replace(old_rd, new_rd, 1)
    old_sess = """    bool? isRDP,
    bool? isSharedPassword,
    String? connToken,
  }) async {
    var params = {
      "type": type.index,
      "id": remoteId,
      "password": password,
      "forceRelay": forceRelay
    };
"""
    new_sess = """    bool? isRDP,
    bool? isSharedPassword,
    String? connToken,
    String? title,
  }) async {
    var params = {
      "type": type.index,
      "id": remoteId,
      "password": password,
      "forceRelay": forceRelay
    };
"""
    if old_sess not in text:
        raise SystemExit("flutter multi_window_manager: newSession signature nao encontrada")
    text = text.replace(old_sess, new_sess, 1)
    old_tok = """    if (connToken != null) {
      params['connToken'] = connToken;
    }
    final msg = jsonEncode(params);
"""
    new_tok = """    if (connToken != null) {
      params['connToken'] = connToken;
    }
    // DeskRemote: title na janela da sessao (vinculo do painel).
    if (title != null && title.isNotEmpty) {
      params['title'] = title;
    }
    final msg = jsonEncode(params);
"""
    if old_tok not in text:
        raise SystemExit("flutter multi_window_manager: connToken params nao encontrado")
    return text.replace(old_tok, new_tok, 1)


def apply_flutter_remote_tab_title_text(text: str) -> str:
    if "DeskRemote: titulo do vinculo na aba" in text:
        return text
    old_ctor = """    if (peerId != null) {
      ConnectionTypeState.init(peerId!);
      tabController.onSelected = (id) {
"""
    new_ctor = """    if (peerId != null) {
      // DeskRemote: titulo do vinculo na aba (params da janela).
      final rawTitle = params['title'];
      final sessionTitle = rawTitle is String ? rawTitle.trim() : '';
      if (sessionTitle.isNotEmpty) {
        bind.mainSetPeerAlias(id: peerId!, alias: sessionTitle);
        PeerStringOption.init(peerId!, 'tabLabel', () => sessionTitle);
      }
      ConnectionTypeState.init(peerId!);
      tabController.onSelected = (id) {
"""
    if old_ctor not in text:
        raise SystemExit("flutter remote_tab_page: init peerId nao encontrado")
    text = text.replace(old_ctor, new_ctor, 1)
    old_h = """      ConnectionTypeState.init(id);
      tabController.add(TabInfo(
        key: id,
        label: id,
"""
    new_h = """      ConnectionTypeState.init(id);
      final handlerTitle = args['title'];
      final handlerSessionTitle =
          handlerTitle is String ? handlerTitle.trim() : '';
      if (handlerSessionTitle.isNotEmpty) {
        bind.mainSetPeerAlias(id: id, alias: handlerSessionTitle);
        PeerStringOption.init(id, 'tabLabel', () => handlerSessionTitle);
      }
      tabController.add(TabInfo(
        key: id,
        label: id,
"""
    if old_h not in text:
        raise SystemExit("flutter remote_tab_page: handler NewRemoteDesktop nao encontrado")
    return text.replace(old_h, new_h, 1)


def patch_flutter_deskremote_ui(
    src: Path, host: str = "", key: str = "", profile: str = "controle"
) -> None:
    """Logo, Recentes + Vinculados (atendente) ou token de instalacao (cliente)."""
    home = src / "flutter" / "lib" / "desktop" / "pages" / "desktop_home_page.dart"
    common = src / "flutter" / "lib" / "common.dart"
    tabs = src / "flutter" / "lib" / "models" / "peer_tab_model.dart"
    peers = src / "flutter" / "lib" / "common" / "widgets" / "peers_view.dart"
    card = src / "flutter" / "lib" / "common" / "widgets" / "peer_card.dart"
    tabbar = src / "flutter" / "lib" / "desktop" / "widgets" / "tabbar_widget.dart"
    settings = src / "flutter" / "lib" / "desktop" / "pages" / "desktop_setting_page.dart"
    main_tab = src / "flutter" / "lib" / "desktop" / "pages" / "desktop_tab_page.dart"
    remote_tab = src / "flutter" / "lib" / "desktop" / "pages" / "remote_tab_page.dart"
    multi_win = src / "flutter" / "lib" / "utils" / "multi_window_manager.dart"
    core_main = src / "src" / "core_main.rs"
    if not common.is_file():
        return
    copy_flutter_auth_overlay(src)

    def _apply(path: Path, fn, label: str) -> None:
        text = path.read_text(encoding="utf-8")
        text2 = fn(text)
        if text2 != text:
            path.write_text(text2, encoding="utf-8")
            print(f"  flutter {label}", flush=True)
        else:
            print(f"  flutter {label} (ja patchado)", flush=True)

    model_dart = src / "flutter" / "lib" / "models" / "model.dart"
    _apply(common, apply_flutter_logo_size_text, "logo maior no painel")
    if profile == "posto":
        _apply(common, apply_flutter_lock_password_text, "senha permanente so no painel")
    _apply(common, apply_flutter_load_icon_hq_text, "ico nitido na barra de titulo")
    if profile != "posto":
        _apply(common, apply_flutter_common_vinculo_import_text, "import busca vinculo")
        _apply(common, apply_flutter_connect_title_text, "name=/--title -> alias")
        _apply(common, apply_flutter_inapp_alias_text, "alias no Conectar do Flutter")
        _apply(common, apply_flutter_session_tab_label_text, "aba da sessao sem ID")
    if home.is_file():
        def _home(t: str) -> str:
            if _FLUTTER_YOUR_DESKTOP_IF in t:
                return t.replace(
                    _FLUTTER_YOUR_DESKTOP_IF, _FLUTTER_YOUR_DESKTOP_ALWAYS, 1
                )
            if 'translate("Your Desktop")' in t:
                return t
            raise SystemExit("flutter home: titulo Seu Computador nao encontrado")

        _apply(home, _home, "Seu Computador abaixo da logo")
        _apply(home, apply_flutter_logo_app_name_text, "DeskRemote abaixo da logo")
        _apply(home, apply_flutter_pane_width_text, "painel esquerdo 224px")
        _apply(home, apply_flutter_update_card_text, "banner de atualizacao")
        if profile == "posto":
            _apply(home, apply_flutter_hide_password_edit_text, "sem editar senha permanente")
    if profile != "posto":
        if tabs.is_file():
            _apply(tabs, apply_flutter_recent_tabs_text, "abas Recentes e Vinculados")
            _apply(tabs, apply_flutter_tab_names_text, "rotulo aba Vinculados")
            _apply(tabs, apply_flutter_tab_icons_text, "icone aba Vinculados")
        peer_tab_page = src / "flutter" / "lib" / "common" / "widgets" / "peer_tab_page.dart"
        if peer_tab_page.is_file():
            _apply(peer_tab_page, apply_flutter_vinculados_tab_page_text, "view aba Vinculados")
        if peers.is_file():
            _apply(peers, apply_flutter_recent_limit_text, "10 ultimas sessoes")
        if card.is_file():
            _apply(card, apply_flutter_peer_card_text, "cartao pelo nome do vinculo")
    consts_dart = src / "flutter" / "lib" / "consts.dart"
    if tabbar.is_file():
        _apply(tabbar, apply_flutter_tabbar_text, "titulo DeskRemote na barra")
        _apply(tabbar, apply_flutter_show_title_text, "exibe nome na barra")
        _apply(tabbar, apply_flutter_titlebar_icon_size_text, "ico 24px na barra")
        if profile != "posto":
            _apply(tabbar, apply_flutter_session_tab_getter_text, "aba reativa ao vinculo")
    if consts_dart.is_file():
        _apply(consts_dart, apply_flutter_tabbar_height_text, "barra 36px para o ico")
    if main_tab.is_file():
        _apply(main_tab, apply_flutter_main_show_title_text, "home com nome na barra")
        if profile == "posto":
            _apply(main_tab, apply_flutter_enroll_gate_text, "token de instalacao na home")
        else:
            _apply(main_tab, apply_flutter_auth_gate_text, "login DeskRudder na home")
    if profile != "posto":
        if multi_win.is_file():
            _apply(multi_win, apply_flutter_session_window_title_text, "title na janela da sessao")
        if remote_tab.is_file():
            _apply(remote_tab, apply_flutter_remote_tab_title_text, "aba da sessao com vinculo")
        if model_dart.is_file():
            _apply(model_dart, apply_flutter_peer_info_tab_text, "peer_info atualiza aba")
    if settings.is_file():
        _apply(settings, apply_flutter_about_text, "tela Sobre")
    if profile != "posto" and core_main.is_file():
        _apply(core_main, apply_flutter_core_main_title_text, "core_main --title")
        _apply(core_main, apply_flutter_core_main_password_text, "core_main senha posicional")
        _apply(core_main, apply_flutter_core_main_cold_start_text, "core_main uni-link no frio")
    patch_flutter_runner_rc(src / "flutter" / "windows" / "runner" / "Runner.rc")


def _selftest_flutter_recent_ui() -> None:
    tabs = apply_flutter_recent_tabs_text(_FLUTTER_TABS_ENABLED)
    if "Recentes e Vinculados" not in tabs or tabs.count("false") != 3:
        raise SystemExit("selftest flutter: Recentes+Vinculados nao aplicados")
    if apply_flutter_recent_tabs_text(tabs) != tabs:
        raise SystemExit("selftest flutter: abas nao e idempotente")
    tabs_old = apply_flutter_recent_tabs_text(_FLUTTER_TABS_RECENT_ONLY)
    if "Recentes e Vinculados" not in tabs_old:
        raise SystemExit("selftest flutter: upgrade Recentes-only falhou")
    names = apply_flutter_tab_names_text(_FLUTTER_TAB_NAMES)
    if "Vinculados" not in names:
        raise SystemExit("selftest flutter: nome Vinculados ausente")
    icons = apply_flutter_tab_icons_text(_FLUTTER_TAB_ICONS)
    if "Icons.link" not in icons:
        raise SystemExit("selftest flutter: icone Vinculados ausente")
    page = apply_flutter_vinculados_tab_page_text(
        _FLUTTER_PEER_TAB_IMPORT
        + _FLUTTER_FAV_VIEW
        + _FLUTTER_SEARCH_LAND
        + _FLUTTER_SEARCH_PORT
        + _FLUTTER_VIEW_SWITCH
        + _FLUTTER_SORT_OFF
        + _FLUTTER_SORT_PORT
    )
    if "DeskRemoteVinculadosView" not in page:
        raise SystemExit("selftest flutter: view Vinculados ausente")
    if "busca do RustDesk nao filtra Vinculados" not in page:
        raise SystemExit("selftest flutter: busca RustDesk ainda visivel em Vinculados")
    if apply_flutter_vinculados_tab_page_text(page) != page:
        raise SystemExit("selftest flutter: tab page Vinculados nao e idempotente")

    limit = apply_flutter_recent_limit_text(_FLUTTER_PEERS_LIMIT)
    if "maxPeers" not in limit or "10" not in limit:
        raise SystemExit("selftest flutter: limite 10 ausente")

    fixture = (
        _FLUTTER_PEER_NAME
        + _FLUTTER_PEER_NAME
        + _FLUTTER_PEER_TILE_ID
        + _FLUTTER_PEER_CARD_ID
        + """                                      child: Text(
                                        name,
                                        style: const TextStyle(
                                            color: Colors.white70,
                                            fontSize: 12),
                                child: Text(
                                  name,
                                  style: isPortrait ? null : greyStyle,
            '${translate('Delete')} "${peer.alias.isEmpty ? formatID(peer.id) : peer.alias}"?');
"""
    )
    out = apply_flutter_peer_card_text(fixture)
    if "displayName" not in out:
        raise SystemExit("selftest flutter: displayName ausente no cartao")
    if _FLUTTER_PEER_TILE_ID in out or _FLUTTER_PEER_CARD_ID in out:
        raise SystemExit("selftest flutter: ID ainda no rotulo do cartao")
    if _FLUTTER_PEER_ID_LABEL not in out:
        raise SystemExit("selftest flutter: formatID do menu Excluir foi removido")
    if "displayName" in out.split("Delete")[-1]:
        raise SystemExit("selftest flutter: displayName vazou para o menu Excluir")
    if apply_flutter_peer_card_text(out) != out:
        raise SystemExit("selftest flutter: cartao nao e idempotente")

    logo = apply_flutter_logo_size_text(
        _FLUTTER_LOGO_IMAGE
        + """
          return Container(
            constraints: BoxConstraints(maxWidth: 300, maxHeight: 60),
            child: image,
          ).marginOnly(left: 12, right: 12, top: 12);"""
    )
    if "maxHeight: 160" not in logo:
        raise SystemExit("selftest flutter: logo sem altura nova")
    if "cacheWidth: 320" not in logo:
        raise SystemExit("selftest flutter: logo sem cacheWidth")
    if "FilterQuality.high" not in logo:
        raise SystemExit("selftest flutter: logo sem FilterQuality.high")
    if apply_flutter_logo_size_text(logo) != logo:
        raise SystemExit("selftest flutter: logo nao e idempotente")

    named = apply_flutter_logo_app_name_text(_FLUTTER_LOAD_LOGO_ALIGN)
    if "DeskRemote: nome do app abaixo da logo" not in named:
        raise SystemExit("selftest flutter: nome DeskRemote abaixo da logo ausente")
    if apply_flutter_logo_app_name_text(named) != named:
        raise SystemExit("selftest flutter: nome abaixo da logo nao e idempotente")

    pane = apply_flutter_pane_width_text(_FLUTTER_PANE_WIDTH)
    if "224.0" not in pane:
        raise SystemExit("selftest flutter: painel esquerdo ainda 200px")
    if apply_flutter_pane_width_text(pane) != pane:
        raise SystemExit("selftest flutter: largura do painel nao e idempotente")

    bar_h = apply_flutter_tabbar_height_text(_FLUTTER_TABBAR_H)
    if "36.0" not in bar_h:
        raise SystemExit("selftest flutter: altura da barra ainda 28px")
    if apply_flutter_tabbar_height_text(bar_h) != bar_h:
        raise SystemExit("selftest flutter: altura da barra nao e idempotente")

    inapp = apply_flutter_inapp_alias_text(
        """    await rustDeskWinManager.newRemoteDesktop(id,
        password: password,
        isSharedPassword: isSharedPassword,
        forceRelay: forceRelay);
"""
    )
    if "busca vinculo na API no Conectar" not in inapp:
        raise SystemExit("selftest flutter: Conectar do Flutter sem busca na API")
    if "aplicarServidorDaContaDeskRemote" not in inapp:
        raise SystemExit("selftest flutter: Conectar sem aplicar servidor da instancia")
    if apply_flutter_inapp_alias_text(inapp) != inapp:
        raise SystemExit("selftest flutter: alias in-app nao e idempotente")
    inapp_old = apply_flutter_inapp_alias_text(_FLUTTER_INAPP_ALIAS_OLD)
    if "busca vinculo na API no Conectar" not in inapp_old:
        raise SystemExit("selftest flutter: patch antigo do Conectar nao atualiza")
    if "aplicarServidorDaContaDeskRemote" not in inapp_old:
        raise SystemExit("selftest flutter: patch antigo do Conectar sem servidor")
    inapp_mid = apply_flutter_inapp_alias_text(_FLUTTER_INAPP_ALIAS_NEW)
    if "aplica o servidor da instancia no Conectar" not in inapp_mid:
        raise SystemExit("selftest flutter: Conectar 2.2.0 nao ganha servidor da instancia")

    tab = apply_flutter_tabbar_text(_FLUTTER_TABBAR_TITLE)
    if "DeskRemote" not in tab or "RustDesk" in tab:
        raise SystemExit("selftest flutter: titulo da barra ainda RustDesk")
    if "onSurface" not in tab:
        raise SystemExit("selftest flutter: titulo da barra sem cor do tema")
    if apply_flutter_tabbar_text(tab) != tab:
        raise SystemExit("selftest flutter: tabbar nao e idempotente")

    load_icon = apply_flutter_load_icon_hq_text(_FLUTTER_LOAD_ICON)
    if "FilterQuality.high" not in load_icon:
        raise SystemExit("selftest flutter: loadIcon sem FilterQuality.high")
    if apply_flutter_load_icon_hq_text(load_icon) != load_icon:
        raise SystemExit("selftest flutter: loadIcon nao e idempotente")

    bar_icon = apply_flutter_titlebar_icon_size_text(_FLUTTER_TITLEBAR_ICON_16)
    if "loadIcon(24)" not in bar_icon:
        raise SystemExit("selftest flutter: barra de titulo ainda em 16px")
    if apply_flutter_titlebar_icon_size_text(bar_icon) != bar_icon:
        raise SystemExit("selftest flutter: loadIcon(24) nao e idempotente")

    about_src = (
        _FLUTTER_ABOUT_TITLE
        + "\n"
        + _FLUTTER_ABOUT_VERSION
        + "\n"
        + _FLUTTER_ABOUT_PRIVACY
        + "              InkWell(\n"
        "                  onTap: () {\n"
        + _FLUTTER_ABOUT_SITE
        + "\n                  },\n"
        "                  child: Text(translate('Website'))),\n"
        f"                          Text(\n                            {_FLUTTER_ABOUT_COPYRIGHT},\n"
        "                          ),\n"
    )
    about = apply_flutter_about_text(about_src)
    if "Sobre o DeskRemote" not in about:
        raise SystemExit("selftest flutter: titulo Sobre o DeskRemote ausente")
    if "Desenvolvido pela DeskRudder" not in about:
        raise SystemExit("selftest flutter: desenvolvido pela DeskRudder ausente")
    if "privacy.html" in about:
        raise SystemExit("selftest flutter: declaracao de privacidade ainda presente")
    if "rustdesk.com" in about:
        raise SystemExit("selftest flutter: website ainda aponta para rustdesk.com")
    if "Purslane" in about:
        raise SystemExit("selftest flutter: copyright Purslane ainda presente")
    if "DeskRudder" not in about.split("Copyright")[-1]:
        raise SystemExit("selftest flutter: copyright DeskRudder ausente")
    if apply_flutter_about_text(about) != about:
        raise SystemExit("selftest flutter: Sobre nao e idempotente")

    srv = apply_flutter_server_defaults_text(
        "class ServerConfig {\n" + _FLUTTER_SERVER_FROM + "}\n",
        "31.97.160.79",
        "testkey=",
    )
    if "DeskRemote: servidor Duplex" not in srv:
        raise SystemExit("selftest flutter: fallback Duplex ausente")
    if '"31.97.160.79"' not in srv or '"testkey="' not in srv:
        raise SystemExit("selftest flutter: host/key Duplex ausentes")
    if apply_flutter_server_defaults_text(srv, "31.97.160.79", "testkey=") != srv:
        raise SystemExit("selftest flutter: fromOptions nao e idempotente")

    net = apply_flutter_network_text(
        _FLUTTER_LISTTILE_SIG + "\n" + _FLUTTER_LISTTILE_RETURN + "\n" + _FLUTTER_ID_RELAY_TILE,
        "31.97.160.79",
    )
    if "subtitle: '31.97.160.79'" not in net:
        raise SystemExit("selftest flutter: host na tile de Rede ausente")
    if apply_flutter_network_text(net, "31.97.160.79") != net:
        raise SystemExit("selftest flutter: Rede nao e idempotente")

    uri = apply_flutter_connect_title_text(
        """  String? password;
  String? switchUuid;
  bool? forceRelay;
      case '--password':
        password = args[i + 1];
        i++;
        break;
      case '--switch_uuid':
      case UriLinkType.remoteDesktop:
        Future.delayed(Duration.zero, () {
          rustDeskWinManager.newRemoteDesktop(id!,
              password: password,
              switchUuid: switchUuid,
              forceRelay: forceRelay);
        });
    if (password != null) args.addAll(['--password', password]);
    String? switch_uuid = param["switch_uuid"];
"""
    )
    if "mainSetPeerAlias" not in uri or 'param["name"]' not in uri:
        raise SystemExit("selftest flutter: alias do vinculo ausente no uni-link")
    if "buscarRotuloVinculoDeskRemote" not in uri or "title: tituloSessao" not in uri:
        raise SystemExit("selftest flutter: title nao vai para a janela da sessao")
    if "aplicarServidorDaContaDeskRemote" not in uri:
        raise SystemExit("selftest flutter: --connect sem aplicar servidor da instancia")
    if apply_flutter_connect_title_text(uri) != uri:
        raise SystemExit("selftest flutter: uni-link title nao e idempotente")
    if "Espera até 5s" not in uri:
        raise SystemExit("selftest flutter: espera da API sem comentario na janela")
    stray_title = (
        "  String? title;\n"
        "      case '--title':\n"
        + _FLUTTER_HANDLE_URI_VARS
        + _FLUTTER_HANDLE_URI_PW
        + """      case UriLinkType.remoteDesktop:
        Future.delayed(Duration.zero, () {
          rustDeskWinManager.newRemoteDesktop(id!,
              password: password,
              switchUuid: switchUuid,
              forceRelay: forceRelay);
        });
    if (password != null) args.addAll(['--password', password]);
    String? switch_uuid = param["switch_uuid"];
"""
    )
    stray_patched = apply_flutter_connect_title_text(stray_title)
    if _FLUTTER_HANDLE_URI_VARS_TITLE not in stray_patched:
        raise SystemExit("selftest flutter: String? title; solto pulou o handleUriLink")
    if "buscarRotuloVinculoDeskRemote" not in stray_patched:
        raise SystemExit("selftest flutter: title solto impediu a busca do vinculo")
    imp = apply_flutter_common_vinculo_import_text(
        "import 'package:flutter_hbb/utils/multi_window_manager.dart';\n"
    )
    if "deskremote/sessao.dart" not in imp:
        raise SystemExit("selftest flutter: common.dart sem import da busca de vinculo")
    if apply_flutter_common_vinculo_import_text(imp) != imp:
        raise SystemExit("selftest flutter: import vinculo nao e idempotente")

    core = apply_flutter_core_main_title_text(
        """            "--password" => {
                if let Some(password) = args.next() {
                    param_array.push(format!("password={password}"));
                }
            }
            "--relay" => {
                param_array.push(format!("relay=true"));
            }
"""
    )
    if "name={encoded}" not in core:
        raise SystemExit("selftest flutter: core_main --title ausente")

    tab_label = apply_flutter_session_tab_label_text(_FLUTTER_TAB_LABEL)
    if "nunca o ID" not in tab_label:
        raise SystemExit("selftest flutter: getDesktopTabLabel sem vinculo")
    if "alias.isEmpty ? peerId" in tab_label:
        raise SystemExit("selftest flutter: aba ainda cai no ID numerico")
    if apply_flutter_session_tab_label_text(tab_label) != tab_label:
        raise SystemExit("selftest flutter: getDesktopTabLabel nao e idempotente")

    getter = apply_flutter_session_tab_getter_text(
        _FLUTTER_TABBAR_SHARED_IMPORT + _FLUTTER_TAB_GETTER + _FLUTTER_TAB_GETTER
    )
    if getter.count("PeerStringOption.find") < 2:
        raise SystemExit("selftest flutter: tablabelGetter nao usa PeerStringOption")
    if "Get.isRegistered" not in getter:
        raise SystemExit("selftest flutter: tablabelGetter sobrescreve o vinculo")
    if apply_flutter_session_tab_getter_text(getter) != getter:
        raise SystemExit("selftest flutter: tablabelGetter nao e idempotente")

    peer_info = apply_flutter_peer_info_tab_text(_FLUTTER_PEER_INFO_HOST)
    if "atualiza a aba quando chega usuario/host" not in peer_info:
        raise SystemExit("selftest flutter: peer_info sem refresh da aba")
    if apply_flutter_peer_info_tab_text(peer_info) != peer_info:
        raise SystemExit("selftest flutter: peer_info tab nao e idempotente")

    pwd = apply_flutter_core_main_password_text(_FLUTTER_CORE_POS_PASSWORD)
    if "senha posicional" not in pwd:
        raise SystemExit("selftest flutter: senha posicional ausente")
    if apply_flutter_core_main_password_text(pwd) != pwd:
        raise SystemExit("selftest flutter: senha posicional nao e idempotente")

    show = apply_flutter_show_title_text(_FLUTTER_SHOW_TITLE_FALSE)
    if "showTitle = true" not in show:
        raise SystemExit("selftest flutter: showTitle continua false")
    if apply_flutter_show_title_text(show) != show:
        raise SystemExit("selftest flutter: showTitle nao e idempotente")

    home_tab = apply_flutter_main_show_title_text(_FLUTTER_MAIN_TAB)
    if "showTitle: true" not in home_tab:
        raise SystemExit("selftest flutter: home sem showTitle")
    if apply_flutter_main_show_title_text(home_tab) != home_tab:
        raise SystemExit("selftest flutter: home showTitle nao e idempotente")

    cold = apply_flutter_core_main_cold_start_text(_FLUTTER_COLD_START)
    if "Some(vec![uni_links])" not in cold:
        raise SystemExit("selftest flutter: uni-link no frio ausente")
    if apply_flutter_core_main_cold_start_text(cold) != cold:
        raise SystemExit("selftest flutter: uni-link no frio nao e idempotente")

    win = apply_flutter_session_window_title_text(
        """  Future<MultiWindowCallResult> newRemoteDesktop(
    String remoteId, {
    String? password,
    bool? isSharedPassword,
    String? switchUuid,
    bool? forceRelay,
  }) async {
    return await newSession(
      WindowType.RemoteDesktop,
      kWindowEventNewRemoteDesktop,
      remoteId,
      _remoteDesktopWindows,
      password: password,
      forceRelay: forceRelay,
      switchUuid: switchUuid,
      isSharedPassword: isSharedPassword,
    );
  }
    bool? isRDP,
    bool? isSharedPassword,
    String? connToken,
  }) async {
    var params = {
      "type": type.index,
      "id": remoteId,
      "password": password,
      "forceRelay": forceRelay
    };
    if (connToken != null) {
      params['connToken'] = connToken;
    }
    final msg = jsonEncode(params);
"""
    )
    if "params['title']" not in win or "title: title" not in win:
        raise SystemExit("selftest flutter: title da sessao ausente no newSession")
    if apply_flutter_session_window_title_text(win) != win:
        raise SystemExit("selftest flutter: title da sessao nao e idempotente")

    remote = apply_flutter_remote_tab_title_text(
        """    if (peerId != null) {
      ConnectionTypeState.init(peerId!);
      tabController.onSelected = (id) {
      ConnectionTypeState.init(id);
      tabController.add(TabInfo(
        key: id,
        label: id,
"""
    )
    if "titulo do vinculo na aba" not in remote:
        raise SystemExit("selftest flutter: remote_tab_page sem titulo do vinculo")
    if apply_flutter_remote_tab_title_text(remote) != remote:
        raise SystemExit("selftest flutter: remote_tab_page titulo nao e idempotente")

    overlay = _FLUTTER_OVERLAY_DIR / "lib" / "deskremote"
    if not (overlay / "sessao.dart").is_file() or not (overlay / "auth_gate.dart").is_file():
        raise SystemExit("selftest flutter: overlay de login ausente")
    if not (overlay / "enroll.dart").is_file() or not (overlay / "enroll_gate.dart").is_file():
        raise SystemExit("selftest flutter: overlay de instalacao do cliente ausente")
    enroll_overlay = (overlay / "enroll.dart").read_text(encoding="utf-8")
    if "deskremote/enroll" not in enroll_overlay:
        raise SystemExit("selftest flutter: resgate do token ausente")
    if "deskremote.invalid" in enroll_overlay:
        raise SystemExit("selftest flutter: overlay de enroll nao deve embutir host")
    if "mainSetPermanentPasswordWithResult" not in enroll_overlay:
        raise SystemExit("selftest flutter: enroll nao aplica senha permanente")
    if "mainStartService" not in enroll_overlay or "mainGetConnectStatus" not in enroll_overlay:
        raise SystemExit("selftest flutter: enroll nao reconecta o hbbs depois de aplicar o servidor")
    if "mainSetOption(key: 'custom-rendezvous-server'" not in enroll_overlay:
        raise SystemExit("selftest flutter: hbbs deve ir em mainSetOption (nao LocalOption)")
    if "mainSetLocalOption(key: 'custom-rendezvous-server'" in enroll_overlay:
        raise SystemExit("selftest flutter: hbbs nao pode ficar so em LocalOption")
    if "mainSetOption" not in enroll_overlay:
        raise SystemExit("selftest flutter: enroll nao trava verification-method")
    if "travarSenhaPermanenteDeskRemote" not in enroll_overlay:
        raise SystemExit("selftest flutter: sync nao retrava senha permanente")
    lock_pw = apply_flutter_lock_password_text(
        "bool isChangePermanentPasswordDisabled() =>\n    bind.mainGetBuildinOption(key: kOptionDisableChangePermanentPassword) ==\n        'Y';\n"
    )
    if "DeskRemote: senha permanente so muda no painel" not in lock_pw:
        raise SystemExit("selftest flutter: lock da senha permanente ausente")
    if apply_flutter_lock_password_text(lock_pw) != lock_pw:
        raise SystemExit("selftest flutter: lock da senha nao e idempotente")
    hide_pw = apply_flutter_hide_password_edit_text(
        "if (!bind.isDisableSettings())\n                    InkWell(\n                      child: Tooltip(\n                        message: translate('Change Password'),\n"
    )
    if "DeskRemote: senha permanente so no painel" not in hide_pw:
        raise SystemExit("selftest flutter: lapis de senha ainda visivel")
    if apply_flutter_hide_password_edit_text(hide_pw) != hide_pw:
        raise SystemExit("selftest flutter: hide password nao e idempotente")
    enroll_gate = apply_flutter_enroll_gate_text(
        _FLUTTER_AUTH_IMPORT + _FLUTTER_HOME_PAGE_CHILD
    )
    if "DeskRemoteEnrollGate" not in enroll_gate or "token de instalacao" not in enroll_gate:
        raise SystemExit("selftest flutter: enroll gate ausente na home")
    if apply_flutter_enroll_gate_text(enroll_gate) != enroll_gate:
        raise SystemExit("selftest flutter: enroll gate nao e idempotente")
    enroll_gate_overlay = (overlay / "enroll_gate.dart").read_text(encoding="utf-8")
    if "mainIsInstalled" not in enroll_gate_overlay:
        raise SystemExit("selftest flutter: enroll gate deve esperar o Instalar do Windows")
    sessao_overlay = (overlay / "sessao.dart").read_text(encoding="utf-8")
    if "https://api-$slug." not in sessao_overlay:
        raise SystemExit("selftest flutter: API do login deve ser api-{slug}")
    if "https://$slug.$kDeskRemoteApex/v1" in sessao_overlay:
        raise SystemExit("selftest flutter: API do login ainda aponta ao host do painel")
    if "deveDescartarSessao" not in sessao_overlay:
        raise SystemExit("selftest flutter: erro de rede nao deve apagar a sessao")
    if "buscarRotuloVinculoDeskRemote" not in sessao_overlay:
        raise SystemExit("selftest flutter: busca do vinculo na frota ausente")
    if "/rustdesk/peers" not in sessao_overlay:
        raise SystemExit("selftest flutter: busca do vinculo sem GET /rustdesk/peers")
    if "/rustdesk/configuracao" not in sessao_overlay:
        raise SystemExit("selftest flutter: atendente sem GET /rustdesk/configuracao")
    if "aplicarServidorDaContaDeskRemote" not in sessao_overlay:
        raise SystemExit("selftest flutter: aplicar servidor da conta ausente")
    if "deskremote.invalid" in sessao_overlay or "31.97.160.79" in sessao_overlay:
        raise SystemExit("selftest flutter: overlay de sessao nao deve embutir host")
    if "rotuloSessaoVinculo" not in sessao_overlay:
        raise SystemExit("selftest flutter: rotuloSessaoVinculo ausente no overlay")
    if _FLUTTER_ROTULO_SESSAO_FN.replace("\r\n", "\n") not in sessao_overlay.replace(
        "\r\n", "\n"
    ):
        raise SystemExit("selftest flutter: formula do rotulo divergiu do painel")
    if "Auto Posto Expresso Medalha · SERVIDOR 001" not in sessao_overlay:
        raise SystemExit("selftest flutter: exemplo empresa ausente no rotulo")
    if _rotulo_sessao_vinculo(
        {
            "empresa_nome": "Auto Posto Expresso Medalha",
            "rede_nome": "Rede Expresso",
            "rotulo_nome": "SERVIDOR",
            "pdv_codigo": "001",
        }
    ) != "Auto Posto Expresso Medalha · SERVIDOR 001":
        raise SystemExit("selftest flutter: rotulo deve preferir empresa, nao rede")
    if _rotulo_sessao_vinculo(
        {"rede_nome": "Posto Farol", "rotulo_nome": "SERVIDOR", "pdv_codigo": "001"}
    ) != "Posto Farol · SERVIDOR 001":
        raise SystemExit("selftest flutter: rotulo cai na rede se empresa vier vazia")
    if _rotulo_sessao_vinculo({"rotulo_nome": "PDV", "pdv_codigo": "02"}) != "PDV 02":
        raise SystemExit("selftest flutter: rotulo sem empresa nem rede divergiu")
    if _rotulo_sessao_vinculo({}) != "Equipamento":
        raise SystemExit("selftest flutter: rotulo vazio deve ser Equipamento")
    if "Duration(seconds: 5)" not in sessao_overlay:
        raise SystemExit("selftest flutter: busca do vinculo sem timeout curto")
    if "outro engine" not in sessao_overlay:
        raise SystemExit("selftest flutter: timeout sem explicar a espera na aba")
    gate_overlay = (overlay / "auth_gate.dart").read_text(encoding="utf-8")
    if "_naoHerdarAposSair" not in gate_overlay:
        raise SystemExit("selftest flutter: Sair deve impedir herdar a sessao do Electron")
    if "aplicarServidorDaContaDeskRemote" not in gate_overlay:
        raise SystemExit("selftest flutter: login sem aplicar servidor da instancia")
    if "naoTentarDeNovo" not in gate_overlay:
        raise SystemExit("selftest flutter: conta sem servidor nao deve ficar em loop")
    if "_pararPoll" not in gate_overlay:
        raise SystemExit("selftest flutter: login deve parar o poll se o servidor nao estiver configurado")
    gate = apply_flutter_auth_gate_text(
        _FLUTTER_AUTH_IMPORT + _FLUTTER_HOME_PAGE_CHILD
    )
    if "DeskRemoteAuthGate" not in gate or "login DeskRudder" not in gate:
        raise SystemExit("selftest flutter: auth gate ausente na home")
    if apply_flutter_auth_gate_text(gate) != gate:
        raise SystemExit("selftest flutter: auth gate nao e idempotente")


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
    text = re.sub(
        r'(?m)^ProductName = ".*"$',
        f'ProductName = "{PRODUCT_DISPLAY_NAME}"',
        text,
        count=1,
    )
    text = re.sub(
        r'(?m)^FileDescription = ".*"$',
        f'FileDescription = "{PRODUCT_DISPLAY_NAME}"',
        text,
        count=1,
    )
    text = re.sub(
        r'(?m)^description = ".*"$',
        f'description = "{PRODUCT_DISPLAY_NAME}"',
        text,
        count=1,
    )
    text = re.sub(
        r'(?m)^LegalCopyright = ".*"$',
        f'LegalCopyright = "{COPYRIGHT_LINE}"',
        text,
        count=1,
    )
    if text != orig:
        cargo_toml.write_text(text, encoding="utf-8")
        print(
            f"  portable Cargo.toml ProductName/copyright -> {PRODUCT_DISPLAY_NAME}",
            flush=True,
        )


def patch_window_display_name(ui_rs: Path) -> None:
    """Titlebar + Sobre usam DeskRemote; APP_NAME/exe continua DeskRudder."""
    if not ui_rs.is_file():
        raise SystemExit(f"Falta {ui_rs}")
    text = ui_rs.read_text(encoding="utf-8")
    name = PRODUCT_DISPLAY_NAME

    old_title = "frame.set_title(&crate::get_app_name());"
    new_title = f'frame.set_title("{name}");'
    if old_title in text:
        text = text.replace(old_title, new_title, 1)
    elif f'frame.set_title("{name}");' not in text:
        raise SystemExit("frame.set_title(get_app_name) nao encontrado em ui.rs")

    old_fn = (
        "    fn get_app_name(&self) -> String {\n"
        "        get_app_name()\n"
        "    }"
    )
    new_fn = (
        "    fn get_app_name(&self) -> String {\n"
        f'        // Nome de exibicao na UI; exe/APP_NAME continua DeskRudder.\n'
        f'        "{name}".to_owned()\n'
        "    }"
    )
    if old_fn in text:
        text = text.replace(old_fn, new_fn, 1)
    elif f'"{name}".to_owned()' not in text or "fn get_app_name(&self)" not in text:
        raise SystemExit("UI get_app_name() nao encontrado para patch de display name")

    ui_rs.write_text(text, encoding="utf-8")
    print(f"  ui.rs: titlebar/Sobre -> {name}", flush=True)


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
        "    // DeskRemote: build so para ser acessado remotamente.\n"
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
        "    // DeskRemote: build so para controlar outros PCs.\n"
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

    new_right = (
        """                    {incoming_only ? <ConnectStatus @{this.connect_status} /> : ""}
                </div>
                {incoming_only && <div .right-pane>
                    <div .right-content style="flow:vertical;size:*;vertical-align:middle;horizontal-align:center;padding:1.5em;">
                        <img src={deskrudder_host_logo} style="display:block;width:48%;max-width:300px;min-width:140px;height:width(100%);margin:0 *;" />
                        <div .title style="margin-top:1em;text-align:center;">"""
        + PRODUCT_DISPLAY_NAME
        + """</div>
                        <div .lighter-text style="text-align:center;margin-top:0.6em;">"""
        + sciter_html(COPY_HOST_VERSAO)
        + """ {handler.get_version()}</div>
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
    )

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
    """Atalho da Area de Trabalho / menu Iniciar: DeskRemote."""
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


def patch_uninstall_completo(windows_rs: Path) -> None:
    """Desinstalar tambem limpa AppData/ProgramData/Public do DeskRemote."""
    if not windows_rs.is_file():
        raise SystemExit(f"Falta {windows_rs}")
    text = windows_rs.read_text(encoding="utf-8")
    if "deskremote-dispositivo.json" in text:
        print("  windows.rs: uninstall completo ja presente", flush=True)
        return
    old = 'if exist \\"{path}\\" rd /s /q \\"{path}\\"'
    extra_rs = (
        'if exist \\"{path}\\" rd /s /q \\"{path}\\"\n'
        "    rem DeskRudder: limpa dados do usuario. Nao apagar LocalAppData: o instalador\n"
        "    rem roda get_uninstall antes do XCOPY, e a pasta extraida fica em LocalAppData.\n"
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\deskremote-dispositivo.json\\" del /f /q \\"%APPDATA%\\\\DeskRudder\\\\deskremote-dispositivo.json\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\deskremote-sessao.json\\" del /f /q \\"%APPDATA%\\\\DeskRudder\\\\deskremote-sessao.json\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\DeskRudder.toml\\" del /f /q \\"%APPDATA%\\\\DeskRudder\\\\DeskRudder.toml\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\DeskRudder2.toml\\" del /f /q \\"%APPDATA%\\\\DeskRudder\\\\DeskRudder2.toml\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\RustDesk.toml\\" del /f /q \\"%APPDATA%\\\\DeskRudder\\\\RustDesk.toml\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\RustDesk2.toml\\" del /f /q \\"%APPDATA%\\\\DeskRudder\\\\RustDesk2.toml\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\*.toml\\" del /f /q \\"%APPDATA%\\\\DeskRudder\\\\*.toml\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\config\\" rd /s /q \\"%APPDATA%\\\\DeskRudder\\\\config\\"\n'
        '    if exist \\"%APPDATA%\\\\DeskRudder\\\\logs\\" rd /s /q \\"%APPDATA%\\\\DeskRudder\\\\logs\\"\n'
        '    if exist \\"%PROGRAMDATA%\\\\DeskRudder\\" rd /s /q \\"%PROGRAMDATA%\\\\DeskRudder\\"\n'
        '    if exist \\"%PUBLIC%\\\\DeskRudder\\" rd /s /q \\"%PUBLIC%\\\\DeskRudder\\"\n'
        '    rd /q \\"{path}\\\\..\\"'
    )
    if old not in text:
        raise SystemExit("windows.rs: rd do path de uninstall nao encontrado")
    text = text.replace(old, extra_rs, 1)
    windows_rs.write_text(text, encoding="utf-8")
    print("  windows.rs: uninstall limpa AppData/ProgramData/Public", flush=True)


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

def patch_client_version(
    cargo_toml: Path,
    portable_cargo: Path,
    common_rs: Path,
    ui_interface_rs: Path,
    client_version: str,
) -> None:
    """Separa versao de protocolo (Cargo/RustDesk) da versao DeskRudder (UI/update).

    `crate::VERSION` vem do Cargo.toml e e o que o peer anuncia. Se for < 1.2.0
    (ex.: CLIENT_VERSION 1.0.x), o modo mapa de teclado some e atalhos do PDV
    (tecla D etc.) falham. Por isso o Cargo.toml principal permanece na tag
    upstream (1.5.0); so a UI/update usam DESKRUDDER_CLIENT_VERSION.
    """
    text = cargo_toml.read_text(encoding="utf-8")
    m = re.search(r'(?m)^version = "([^"]+)"', text)
    if not m:
        raise SystemExit(f"version= nao encontrado em {cargo_toml}")
    protocol_ver = m.group(1)
    if protocol_ver == client_version:
        raise SystemExit(
            f"Cargo.toml version={protocol_ver!r} nao pode ser igual a CLIENT_VERSION — "
            "isso desliga o modo mapa (peer < 1.2.0). Mantenha a tag RustDesk no Cargo.toml."
        )
    print(
        f"  Cargo.toml version (protocolo) = {protocol_ver} (inalterado); "
        f"DeskRudder UI = {client_version}",
        flush=True,
    )

    # Instalador portable: metadado do .exe empacotador pode ser a versao DeskRudder.
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

    common = common_rs.read_text(encoding="utf-8")
    const_line = f'pub const DESKRUDDER_CLIENT_VERSION: &str = "{client_version}";\n'
    if "pub const DESKRUDDER_CLIENT_VERSION:" in common:
        common2, n = re.subn(
            r'pub const DESKRUDDER_CLIENT_VERSION: &str = "[^"]+";\n',
            const_line,
            common,
            count=1,
        )
        if n < 1:
            raise SystemExit("DESKRUDDER_CLIENT_VERSION presente mas replace falhou")
        common = common2
    else:
        marker = (
            "lazy_static::lazy_static! {\n"
            "    pub static ref SOFTWARE_UPDATE_URL:"
        )
        if marker not in common:
            raise SystemExit("SOFTWARE_UPDATE_URL nao encontrado em common.rs")
        common = common.replace(
            marker,
            f"{const_line}\n{marker}",
            1,
        )
    common_rs.write_text(common, encoding="utf-8")
    print(f"  common.rs: DESKRUDDER_CLIENT_VERSION = {client_version}", flush=True)

    ui = ui_interface_rs.read_text(encoding="utf-8")
    old_get = (
        "#[inline]\n"
        "pub fn get_version() -> String {\n"
        "    crate::VERSION.to_owned()\n"
        "}"
    )
    new_get = (
        "#[inline]\n"
        "pub fn get_version() -> String {\n"
        "    // Versao DeskRudder (UI/update). crate::VERSION = tag RustDesk (protocolo/teclado).\n"
        "    crate::DESKRUDDER_CLIENT_VERSION.to_owned()\n"
        "}"
    )
    if "crate::DESKRUDDER_CLIENT_VERSION.to_owned()" in ui:
        print("  ui_interface.rs: get_version() ja usa DESKRUDDER_CLIENT_VERSION", flush=True)
    elif old_get in ui:
        ui_interface_rs.write_text(ui.replace(old_get, new_get, 1), encoding="utf-8")
        print("  ui_interface.rs: get_version() -> DESKRUDDER_CLIENT_VERSION", flush=True)
    else:
        raise SystemExit("get_version() nao encontrado em ui_interface.rs")


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
    // DeskRemote: canal proprio (version.json no Release GitHub).
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
    // Comparar com versao DeskRudder (nao crate::VERSION / tag RustDesk).
    if get_version_number(latest) > get_version_number(crate::DESKRUDDER_CLIENT_VERSION) {{
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
    # Markup: entidades HTML. Strings TIS: \uXXXX. Ver sciter_html / sciter_tis_str.
    new = (
        "class UpdateMe: Reactor.Component {\n"
        "    function render() {\n"
        "        return <div .install-me>\n"
        "            <div>" + sciter_html(COPY_BANNER_TITULO) + "</div>\n"
        "            <div>" + sciter_html(COPY_BANNER_CORPO_ANTES)
        + "({handler.get_new_version()}). "
        + sciter_html(COPY_BANNER_CORPO_SUA)
        + "{handler.get_version()}.</div>\n"
        "            <div #install-me.link>" + sciter_html(COPY_BANNER_CTA) + "</div>\n"
        '            <div #download-percent style="display:none; padding-top: 1em;" />\n'
        "        </div>;\n"
        "    }\n"
        "\n"
        "    event click $(#install-me) {\n"
        f'        var url = "{DOWNLOAD_INSTALLER_URL}";\n'
        "        var path = handler.get_software_store_path();\n"
        "        var onsuccess = function(md5) {\n"
        '            $(#download-percent).content("'
        + sciter_tis_str(COPY_BANNER_INSTALANDO)
        + '");\n'
        "            handler.update_me(path);\n"
        "        };\n"
        "        var onerror = function(err) {\n"
        '            msgbox("custom-error", "'
        + sciter_tis_str(COPY_BANNER_ERRO_TITULO)
        + '", "'
        + sciter_tis_str(COPY_BANNER_ERRO_CORPO)
        + '");\n'
        "        };\n"
        "        var onprogress = function(loaded, total) {\n"
        "            if (!total) total = 5 * 1024 * 1024;\n"
        "            var el = $(#download-percent);\n"
        '            el.style.set{display: "block"};\n'
        '            el.content("'
        + sciter_tis_str(COPY_BANNER_BAIXANDO_PCT)
        + '" + (loaded * 100 / total));\n'
        "        };\n"
        '        $(#download-percent).style.set{display: "block"};\n'
        '        $(#download-percent).content("'
        + sciter_tis_str(COPY_BANNER_BAIXANDO)
        + '");\n'
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
        "                        // Update silencioso: o servico SYSTEM aplica a fila.\n"
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


def patch_silent_update(windows_rs: Path) -> None:
    """Update remoto sem UAC: fila em Public\\DeskRudder + watcher no --service (SYSTEM).

    PCs sem monitor/operador nao conseguem confirmar o UAC do run_uac. O fluxo:
      1) UI baixa o .exe e grava o caminho em %PUBLIC%\\DeskRudder\\pending_update.txt
      2) O servico Windows (--service, SYSTEM) le a fila e roda o .exe com --update
      3) Se ja estiver elevado, aplica direto; se nao houver servico, cai no UAC
    """
    if not windows_rs.is_file():
        raise SystemExit(f"Falta {windows_rs}")
    text = windows_rs.read_text(encoding="utf-8")

    helpers = r'''
// DeskRudder: update silencioso via servico SYSTEM (sem prompt UAC).
fn deskrudder_pending_update_path() -> Option<std::path::PathBuf> {
    let public = std::env::var_os("PUBLIC")?;
    Some(std::path::PathBuf::from(public).join("DeskRudder").join("pending_update.txt"))
}

fn deskrudder_run_update_exe(file: &str) -> ResultType<()> {
    let mut cmd = std::process::Command::new(file);
    cmd.arg("--update");
    cmd.creation_flags(CREATE_NO_WINDOW);
    match cmd.spawn() {
        Ok(_) => Ok(()),
        Err(e) => bail!("Failed to spawn update exe: {}", e),
    }
}

fn deskrudder_try_queue_silent_update(file: &str) -> bool {
    if !is_installed() || !is_self_service_running() {
        return false;
    }
    let Some(pending) = deskrudder_pending_update_path() else {
        return false;
    };
    if let Some(parent) = pending.parent() {
        if let Err(e) = std::fs::create_dir_all(parent) {
            log::error!("DeskRudder: cannot create {:?}: {}", parent, e);
            return false;
        }
    }
    if let Err(e) = std::fs::write(&pending, file) {
        log::error!("DeskRudder: cannot write pending update: {}", e);
        return false;
    }
    log::info!("DeskRudder: queued silent update via {:?}", pending);
    true
}

fn deskrudder_start_silent_update_watcher() {
    std::thread::spawn(|| {
        log::info!("DeskRudder: silent update watcher started");
        loop {
            std::thread::sleep(std::time::Duration::from_secs(2));
            let Some(pending) = deskrudder_pending_update_path() else {
                continue;
            };
            let Ok(content) = std::fs::read_to_string(&pending) else {
                continue;
            };
            let path = content.trim().to_string();
            let _ = std::fs::remove_file(&pending);
            if path.is_empty() {
                continue;
            }
            if !path.to_lowercase().ends_with(".exe") {
                log::error!("DeskRudder: invalid pending update path: {}", path);
                continue;
            }
            if !std::path::Path::new(&path).is_file() {
                log::error!("DeskRudder: pending update exe missing: {}", path);
                continue;
            }
            log::info!("DeskRudder: applying silent update from {}", path);
            if let Err(e) = deskrudder_run_update_exe(&path) {
                log::error!("DeskRudder: silent update failed: {}", e);
            }
        }
    });
}

'''

    anchor = (
        "// Used for auto update and manual update in the main window.\n"
        "pub fn update_to(file: &str) -> ResultType<()> {"
    )
    if "deskrudder_pending_update_path" in text:
        print("  windows.rs: silent update helpers ja presentes", flush=True)
    elif anchor not in text:
        raise SystemExit("update_to() anchor nao encontrado em windows.rs")
    else:
        text = text.replace(anchor, helpers + anchor, 1)
        print("  windows.rs: helpers update silencioso", flush=True)

    old_uac = (
        "        if !run_uac(file, \"--update\")? {\n"
        "            bail!(\n"
        "                \"Failed to run the update exe with UAC, error: {:?}\",\n"
        "                std::io::Error::last_os_error()\n"
        "            );\n"
        "        }"
    )
    new_uac = (
        "        // DeskRudder: preferir update silencioso (SYSTEM) antes do UAC.\n"
        "        // Necessario em PCs sem monitor/operador (UAC nao tem quem confirmar).\n"
        "        if is_root() {\n"
        "            deskrudder_run_update_exe(file)?;\n"
        "        } else if deskrudder_try_queue_silent_update(file) {\n"
        "            // Tempo para o --service ler a fila antes da UI sair.\n"
        "            std::thread::sleep(std::time::Duration::from_millis(2000));\n"
        "        } else if !run_uac(file, \"--update\")? {\n"
        "            bail!(\n"
        "                \"Failed to run the update exe with UAC, error: {:?}\",\n"
        "                std::io::Error::last_os_error()\n"
        "            );\n"
        "        }"
    )
    if "deskrudder_try_queue_silent_update(file)" in text:
        print("  windows.rs: update_to ja usa fila silenciosa", flush=True)
    elif old_uac not in text:
        raise SystemExit("run_uac(--update) nao encontrado em update_to (upstream mudou?)")
    else:
        text = text.replace(old_uac, new_uac, 1)
        print("  windows.rs: update_to -> silent queue / SYSTEM / UAC", flush=True)

    old_svc = (
        "    // Tell the system that the service is running now\n"
        "    status_handle.set_service_status(next_status)?;\n"
        "\n"
        "    let mut session_id = unsafe { get_current_session(share_rdp()) };"
    )
    new_svc = (
        "    // Tell the system that the service is running now\n"
        "    status_handle.set_service_status(next_status)?;\n"
        "\n"
        "    // DeskRudder: watcher de update silencioso (Public\\DeskRudder\\pending_update.txt)\n"
        "    deskrudder_start_silent_update_watcher();\n"
        "\n"
        "    let mut session_id = unsafe { get_current_session(share_rdp()) };"
    )
    watcher_call_marker = (
        "    // DeskRudder: watcher de update silencioso (Public\\DeskRudder\\pending_update.txt)\n"
        "    deskrudder_start_silent_update_watcher();"
    )
    if watcher_call_marker in text:
        print("  windows.rs: watcher ja iniciado no --service", flush=True)
    elif old_svc not in text:
        raise SystemExit("run_service status_handle anchor nao encontrado (upstream mudou?)")
    else:
        text = text.replace(old_svc, new_svc, 1)
        print("  windows.rs: watcher silent update no --service", flush=True)

    windows_rs.write_text(text, encoding="utf-8")


def patch_file_transfer_defaults(common_rs: Path) -> None:
    """Garante transferencia de arquivo no posto e copy-paste no controle.

    Defaults do RustDesk ja tendem a Y, mas forcamos em DEFAULT_* no startup
    para builds DeskRudder (evita opcao N residual / custom.txt). Tambem mantem
    allow-scope-violation-close=N para nao fechar a sessao em mensagem fora de escopo.
    """
    text = common_rs.read_text(encoding="utf-8")
    old = """pub fn global_init() -> bool {
    #[cfg(all(target_os = "linux", feature = "drm"))]
    crate::platform::linux::dispatch_wayland_display_probe();
    #[cfg(target_os = "linux")]
    {
        if !crate::platform::linux::is_x11() {
            crate::server::wayland::init();
        }
    }
    true
}"""
    new = """pub fn global_init() -> bool {
    #[cfg(all(target_os = "linux", feature = "drm"))]
    crate::platform::linux::dispatch_wayland_display_probe();
    #[cfg(target_os = "linux")]
    {
        if !crate::platform::linux::is_x11() {
            crate::server::wayland::init();
        }
    }
    // DeskRudder: transferencia de arquivo sempre habilitada por padrao.
    // Posto (enable-file-transfer) + controle (enable-file-copy-paste).
    // Nao fechar sessao em scope-violation (clipboard/file durante remoto).
    {
        let mut settings = config::DEFAULT_SETTINGS.write().unwrap();
        settings.insert("enable-file-transfer".to_owned(), "Y".to_owned());
        settings.insert("allow-scope-violation-close".to_owned(), "N".to_owned());
    }
    {
        let mut local = config::DEFAULT_LOCAL_SETTINGS.write().unwrap();
        local.insert("enable-file-copy-paste".to_owned(), "Y".to_owned());
    }
    true
}"""
    if 'settings.insert("enable-file-transfer"' in text:
        print("  common.rs: defaults de file transfer ja presentes", flush=True)
        return
    if old not in text:
        raise SystemExit("global_init() nao encontrado em common.rs (upstream mudou?)")
    common_rs.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  common.rs: defaults enable-file-transfer / copy-paste", flush=True)


def patch_transfer_file_spawn(remote_rs: Path) -> None:
    """Garante spawn de --file-transfer com a senha da sessao (owned String).

    O upstream passa &self.password no vec de args; se a senha vier vazia
    (login so pela UI), a janela de transferencia pede de novo — sem derrubar
    a sessao remota atual. Logamos o caso para diagnostico.
    """
    if not remote_rs.is_file():
        raise SystemExit(f"Falta {remote_rs}")
    text = remote_rs.read_text(encoding="utf-8")
    old = """    fn transfer_file(&mut self) {
        let id = self.get_id();
        let args = vec!["--file-transfer", &id, &self.password];
        if let Err(err) = crate::run_me(args) {
            log::error!("Failed to spawn file transfer: {}", err);
        }
    }"""
    new = """    fn transfer_file(&mut self) {
        let id = self.get_id();
        // DeskRudder: owned password para o spawn; se vazia, a janela FT pede login.
        let password = self.password.clone();
        if password.is_empty() {
            log::warn!(
                "DeskRudder: spawning file-transfer without password (window will prompt)"
            );
        }
        let args = vec!["--file-transfer", &id, &password];
        if let Err(err) = crate::run_me(args) {
            log::error!("Failed to spawn file transfer: {}", err);
        }
    }"""
    if "DeskRudder: spawning file-transfer without password" in text:
        print("  remote.rs: transfer_file ja patchado", flush=True)
        return
    if old not in text:
        raise SystemExit("transfer_file() nao encontrado em remote.rs (upstream mudou?)")
    remote_rs.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  remote.rs: transfer_file com senha owned + log", flush=True)


def patch_install_version_label(install_tis: Path) -> None:
    """Mostra a versao na tela de instalacao."""
    text = install_tis.read_text(encoding="utf-8")
    old = '<div style="font-size: 2em;">{translate(\'Installation\')}</div>'
    new = (
        '<div style="font-size: 2em;">{translate(\'Installation\')}</div>\n'
        '            <div .lighter-text style="margin-top: 0.4em;">'
        + sciter_html(COPY_HOST_VERSAO)
        + " {handler.get_version()}</div>"
    )
    if old not in text:
        raise SystemExit("titulo Installation nao encontrado em install.tis")
    install_tis.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("  install.tis: label Versão", flush=True)


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


_URI_CONNECT_HELPERS = '''fn deskrudder_percent_decode(s: &str) -> String {
    let s = s.replace('+', " ");
    let b = s.as_bytes();
    let mut out = Vec::with_capacity(b.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'%' && i + 2 < b.len() {
            if let Ok(v) = u8::from_str_radix(std::str::from_utf8(&b[i + 1..i + 3]).unwrap_or(""), 16) {
                out.push(v);
                i += 3;
                continue;
            }
        }
        out.push(b[i]);
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn deskrudder_connect_args_from_uri(uri: &str) -> Option<Vec<String>> {
    let scheme_end = uri.find("://")?;
    let rest = uri[scheme_end + 3..].trim_start_matches('/');
    let rest = rest.strip_prefix("connection/new/")?;
    let (id_part, query) = rest.split_once('?').unwrap_or((rest, ""));
    let id = id_part.trim();
    if id.is_empty() || !id.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    let mut args = vec!["--connect".to_string(), id.to_string()];
    let mut password = String::new();
    let mut title: Option<String> = None;
    for pair in query.split('&') {
        if let Some(raw) = pair.strip_prefix("password=") {
            let pass = deskrudder_percent_decode(raw);
            if !pass.is_empty() {
                password = pass;
            }
        } else if let Some(raw) = pair.strip_prefix("name=") {
            let t = deskrudder_percent_decode(raw);
            if !t.is_empty() {
                title = Some(t);
            }
        }
    }
    if !password.is_empty() {
        args.push(password);
    } else if title.is_some() {
        // Placeholder: o parser de --connect consome o 3o arg como senha.
        args.push(String::new());
    }
    if let Some(t) = title {
        args.push("--title".to_string());
        args.push(t);
    }
    Some(args)
}

'''


def patch_sciter_uri_connect(ui_rs: Path) -> None:
    """Sciter so aceita --connect ID [senha]. O Windows entrega deskrudder:// e o app saia."""
    text = ui_rs.read_text(encoding="utf-8")
    start_fn = "pub fn start(args: &mut [String]) {\n"
    if "deskrudder_connect_args_from_uri" in text:
        if 'strip_prefix("name=")' in text:
            print("  ui.rs: deskrudder:// ja vira --connect (com name=)", flush=True)
        else:
            import re as _re

            text2, n = _re.subn(
                r"fn deskrudder_percent_decode\(s: &str\) -> String \{.*?\n\}\n\n"
                r"fn deskrudder_connect_args_from_uri\(uri: &str\) -> Option<Vec<String>> \{.*?\n\}\n\n",
                _URI_CONNECT_HELPERS,
                text,
                count=1,
                flags=_re.S,
            )
            if n < 1 or 'strip_prefix("name=")' not in text2:
                raise SystemExit("falha ao atualizar deskrudder_connect_args_from_uri com name=")
            ui_rs.write_text(text2, encoding="utf-8")
            print("  ui.rs: deskrudder:// --connect + name=/--title", flush=True)
        return
    if start_fn not in text:
        raise SystemExit("pub fn start nao encontrado em ui.rs")
    inject = (
        _URI_CONNECT_HELPERS
        + start_fn
        + """    // DeskRudder: o handler Windows passa deskrudder://connection/new/{id}?password=
    // O Sciter so trata --connect ID [senha]; URI solta cai em "Wrong command" e o processo sai.
    if !args.is_empty() && args[0].to_ascii_lowercase().starts_with("deskrudder://") {
        if let Some(cmd) = deskrudder_connect_args_from_uri(&args[0]) {
            if let Ok(exe) = std::env::current_exe() {
                let _ = std::process::Command::new(exe).args(&cmd).spawn();
            }
        }
        return;
    }
"""
    )
    ui_rs.write_text(text.replace(start_fn, inject, 1), encoding="utf-8")
    print("  ui.rs: deskrudder://connection/new/{id} -> --connect", flush=True)


def patch_remote_session_title(ui_rs: Path) -> None:
    """--connect ID [senha] [--title ROTULO]: titlebar + alias do peer (toolbar)."""
    text = ui_rs.read_text(encoding="utf-8")
    if "deskrudder_session_title_from_args" in text:
        print("  ui.rs: --title de sessao ja patchado", flush=True)
        return
    old = """        let id = id.to_owned();
        let pass = iter.next().unwrap_or(&"".to_owned()).clone();
        let args: Vec<String> = iter.map(|x| x.clone()).collect();
        frame.set_title(&id);
"""
    new = """        let id = id.to_owned();
        let pass_raw = iter.next().unwrap_or(&"".to_owned()).clone();
        let mut rest: Vec<String> = iter.map(|x| x.clone()).collect();
        let (pass, mut args) = if pass_raw == "--title" {
            let mut a = vec!["--title".to_string()];
            a.append(&mut rest);
            ("".to_string(), a)
        } else {
            (pass_raw, rest)
        };
        let mut title = id.clone();
        if let Some(i) = args.iter().position(|x| x == "--title") {
            if i + 1 < args.len() {
                let t = args[i + 1].clone();
                if !t.is_empty() {
                    title = t;
                }
                args.drain(i..=i + 1);
            } else {
                args.remove(i);
            }
        }
        // Alias do peer: header.tis usa get_option('alias') || get_id().
        {
            use hbb_common::config::PeerConfig;
            let mut cfg = PeerConfig::load(&id);
            cfg.options.insert("alias".to_owned(), title.clone());
            cfg.store(&id);
        }
        frame.set_title(&title);
"""
    if old not in text:
        raise SystemExit("bloco set_title(&id) do --connect nao encontrado em ui.rs")
    text = text.replace(old, new, 1)
    # Marca para idempotencia
    text = text.replace(
        "frame.set_title(&title);\n",
        "frame.set_title(&title); // deskrudder_session_title_from_args\n",
        1,
    )
    ui_rs.write_text(text, encoding="utf-8")
    print("  ui.rs: --connect --title -> titlebar + alias", flush=True)


def patch_remote_dark_theme(
    remote_rs: Path, remote_tis: Path, common_css: Path, header_css: Path
) -> None:
    """Sessao remota: tema escuro + barra de titulo DWM (igual index)."""
    # Metodos no handler da sessao Sciter
    if remote_rs.is_file():
        text = remote_rs.read_text(encoding="utf-8")
        if "fn is_system_dark_theme" not in text:
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
            let hwnd = *super::DESKRUDDER_MAIN_HWND.lock().unwrap();
            super::deskrudder_set_titlebar_dark(hwnd, dark);
        }
    }
"""
            # Inserir antes do dispatch ou apos get_icon
            anchor = "    pub fn get_icon(&self) -> String {\n        super::get_icon()\n    }"
            if anchor not in text:
                raise SystemExit("get_icon em remote.rs nao encontrado para tema")
            text = text.replace(anchor, anchor + methods, 1)
            # Expor no dispatch_script_call
            if "fn is_system_dark_theme();" not in text:
                disp = "        fn get_local_option(String);\n"
                if disp not in text:
                    raise SystemExit("dispatch get_local_option nao encontrado")
                text = text.replace(
                    disp,
                    disp
                    + "        fn is_system_dark_theme();\n"
                    + "        fn set_titlebar_dark(bool);\n",
                    1,
                )
            remote_rs.write_text(text, encoding="utf-8")
            print("  remote.rs: is_system_dark_theme + set_titlebar_dark", flush=True)
        else:
            print("  remote.rs: tema escuro ja presente", flush=True)

        # DESKRUDDER_MAIN_HWND e deskrudder_set_titlebar_dark precisam ser pub(crate)
        # — patch em ui.rs se ainda privados
    # remote.tis: aplicar tema no ready
    if remote_tis.is_file():
        rt = remote_tis.read_text(encoding="utf-8")
        if "deskrudder_apply_remote_theme" not in rt:
            theme_fn = """
function deskrudder_apply_remote_theme() {
    var opt = handler.get_local_option("allow-darktheme");
    var dark;
    if (opt == "Y") dark = true;
    else if (opt == "N") dark = false;
    else {
        try { dark = handler.is_system_dark_theme(); } catch(e) { dark = false; }
    }
    self.attributes.toggleClass("darktheme", dark);
    try { handler.set_titlebar_dark(dark); } catch(e) {}
}

"""
            old_ready = "function self.ready() {\n"
            if old_ready not in rt:
                raise SystemExit("self.ready nao encontrado em remote.tis")
            rt = rt.replace(
                old_ready,
                theme_fn + old_ready + "    deskrudder_apply_remote_theme();\n",
                1,
            )
            remote_tis.write_text(rt, encoding="utf-8")
            print("  remote.tis: tema escuro na sessao", flush=True)

    dark_header_css = """
/* DeskRemote: barra da sessao remota no tema escuro */
html.darktheme header {
  background: #252525;
  color: #f3f3f3;
}
html.darktheme header #screens {
  background: #333;
  color: #f3f3f3;
}
html.darktheme header .remote-id {
  color: #f3f3f3;
}
html.darktheme header span:hover,
html.darktheme header #screen:hover {
  background: #444;
}
html.darktheme header span:active,
html.darktheme header #screen:active {
  background: #555;
}
"""
    if header_css.is_file():
        hc = header_css.read_text(encoding="utf-8")
        if "DeskRemote: barra da sessao" not in hc:
            header_css.write_text(hc.rstrip() + "\n" + dark_header_css, encoding="utf-8")
            print("  header.css: darktheme na toolbar remota", flush=True)
    if common_css.is_file():
        cc = common_css.read_text(encoding="utf-8")
        if "html.darktheme header {" not in cc:
            # common.css ja define header { background: white } — reforca dark
            common_css.write_text(
                cc.rstrip()
                + "\n\nhtml.darktheme header {\n  background: #252525;\n  color: #f3f3f3;\n}\n",
                encoding="utf-8",
            )
            print("  common.css: header darktheme", flush=True)


def patch_titlebar_symbols_visible(ui_rs: Path) -> None:
    """Torna DESKRUDDER_MAIN_HWND / deskrudder_set_titlebar_dark acessiveis em remote.rs."""
    text = ui_rs.read_text(encoding="utf-8")
    changed = False
    if "static ref DESKRUDDER_MAIN_HWND: Mutex<isize>" in text and \
            "pub(crate) static ref DESKRUDDER_MAIN_HWND" not in text:
        text = text.replace(
            "static ref DESKRUDDER_MAIN_HWND: Mutex<isize>",
            "pub(crate) static ref DESKRUDDER_MAIN_HWND: Mutex<isize>",
            1,
        )
        changed = True
    if "fn deskrudder_set_titlebar_dark(hwnd: isize, dark: bool)" in text and \
            "pub(crate) fn deskrudder_set_titlebar_dark" not in text:
        text = text.replace(
            "fn deskrudder_set_titlebar_dark(hwnd: isize, dark: bool)",
            "pub(crate) fn deskrudder_set_titlebar_dark(hwnd: isize, dark: bool)",
            1,
        )
        changed = True
    if changed:
        ui_rs.write_text(text, encoding="utf-8")
        print("  ui.rs: simbolos titlebar pub(crate)", flush=True)


def patch_windows_single_instance(windows_rs: Path) -> None:
    """Mutex + foco: atalho/painel nao abre varias janelas iguais."""
    if not windows_rs.is_file():
        raise SystemExit(f"Falta {windows_rs}")
    text = windows_rs.read_text(encoding="utf-8")
    if "deskrudder_try_lock_main_instance" in text:
        print("  windows.rs: single-instance ja presente", flush=True)
        return
    # Inserir perto do mutex do tray (mesmo padrao CreateMutexW).
    anchor = "pub fn try_lock_tray_single_instance() -> bool {"
    if anchor not in text:
        raise SystemExit("try_lock_tray_single_instance nao encontrado")
    block = r'''
/// DeskRemote: uma unica janela principal (atalho da area de trabalho).
pub fn deskrudder_try_lock_main_instance() -> bool {
    use winapi::um::{
        errhandlingapi::{GetLastError, SetLastError},
        synchapi::CreateMutexW,
    };
    let name = wide_string(&format!("Local\\{}_main_ui", crate::get_app_name()));
    unsafe {
        SetLastError(0);
        let handle = CreateMutexW(null_mut(), FALSE, name.as_ptr());
        let last_error = GetLastError();
        if !handle.is_null() {
            if last_error == ERROR_ALREADY_EXISTS {
                CloseHandle(handle);
                return false;
            }
            return true;
        }
        if last_error == ERROR_ACCESS_DENIED {
            return false;
        }
        true
    }
}

/// DeskRemote: uma unica janela de sessao por ID remoto.
pub fn deskrudder_try_lock_session_instance(id: &str) -> bool {
    use winapi::um::{
        errhandlingapi::{GetLastError, SetLastError},
        synchapi::CreateMutexW,
    };
    let safe: String = id.chars().filter(|c| c.is_ascii_alphanumeric()).collect();
    if safe.is_empty() {
        return true;
    }
    let name = wide_string(&format!("Local\\{}_session_{}", crate::get_app_name(), safe));
    unsafe {
        SetLastError(0);
        let handle = CreateMutexW(null_mut(), FALSE, name.as_ptr());
        let last_error = GetLastError();
        if !handle.is_null() {
            if last_error == ERROR_ALREADY_EXISTS {
                CloseHandle(handle);
                return false;
            }
            return true;
        }
        if last_error == ERROR_ACCESS_DENIED {
            return false;
        }
        true
    }
}

/// Traz para frente a primeira janela cujo titulo bata exatamente.
pub fn deskrudder_try_focus_window_by_titles(titles: &[&str]) -> bool {
    use winapi::um::winuser::{FindWindowW, IsIconic, SetForegroundWindow, ShowWindow, SW_RESTORE};
    unsafe {
        for title in titles {
            if title.is_empty() {
                continue;
            }
            let wtitle = wide_string(title);
            let hwnd = FindWindowW(std::ptr::null(), wtitle.as_ptr());
            if hwnd.is_null() {
                continue;
            }
            if IsIconic(hwnd) != 0 {
                ShowWindow(hwnd, SW_RESTORE);
            }
            SetForegroundWindow(hwnd);
            return true;
        }
    }
    false
}

'''
    text = text.replace(anchor, block + anchor, 1)
    windows_rs.write_text(text, encoding="utf-8")
    print("  windows.rs: single-instance main + session", flush=True)


def patch_ui_single_instance(ui_rs: Path) -> None:
    """Chama o mutex no start() da UI Sciter (main e --connect)."""
    text = ui_rs.read_text(encoding="utf-8")
    if "deskrudder_enforce_single_instance" in text:
        print("  ui.rs: single-instance ja ligado", flush=True)
        return
    helper = f'''
fn deskrudder_enforce_single_instance(args: &[String]) -> bool {{
    // true = continuar; false = ja ha instancia (sair).
    #[cfg(windows)]
    {{
        use crate::platform::windows::{{
            deskrudder_try_focus_window_by_titles, deskrudder_try_lock_main_instance,
            deskrudder_try_lock_session_instance,
        }};
        if args.is_empty() {{
            if !deskrudder_try_lock_main_instance() {{
                let _ = deskrudder_try_focus_window_by_titles(&[
                    "{PRODUCT_DISPLAY_NAME}",
                    "DeskRudder",
                ]);
                return false;
            }}
            return true;
        }}
        let cmd = args[0].as_str();
        if matches!(
            cmd,
            "--connect" | "--file-transfer" | "--port-forward" | "--rdp" | "--view-camera"
        ) && args.len() > 1
        {{
            let id = args[1].as_str();
            let mut title = id.to_string();
            if let Some(i) = args.iter().position(|x| x == "--title") {{
                if i + 1 < args.len() && !args[i + 1].is_empty() {{
                    title = args[i + 1].clone();
                }}
            }}
            if !deskrudder_try_lock_session_instance(id) {{
                let _ = deskrudder_try_focus_window_by_titles(&[title.as_str(), id]);
                return false;
            }}
        }}
    }}
    true
}}

'''
    # Inserir antes de pub fn start
    start_fn = "pub fn start(args: &mut [String]) {\n"
    if start_fn not in text:
        raise SystemExit("pub fn start nao encontrado para single-instance")
    if "fn deskrudder_enforce_single_instance" not in text:
        text = text.replace(start_fn, helper + start_fn, 1)

    # Apos o bloco URI, antes do macos dock — ou no inicio do start apos URI
    uri_end = """        return;
    }
    #[cfg(target_os = "macos")]
    crate::platform::delegate::show_dock();
"""
    inject = """        return;
    }
    // DeskRemote: uma janela principal / uma sessao por ID.
    if !deskrudder_enforce_single_instance(args) {
        return;
    }
    #[cfg(target_os = "macos")]
    crate::platform::delegate::show_dock();
"""
    if "deskrudder_enforce_single_instance(args)" in text:
        pass
    elif uri_end in text:
        text = text.replace(uri_end, inject, 1)
    else:
        # Sem bloco URI (ordem de patches): inserir no comeco de start
        old = start_fn
        new = (
            start_fn
            + """    if !deskrudder_enforce_single_instance(args) {
        return;
    }
"""
        )
        if "deskrudder_enforce_single_instance(args)" not in text:
            text = text.replace(old, new, 1)

    ui_rs.write_text(text, encoding="utf-8")
    print("  ui.rs: single-instance no start()", flush=True)


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
        default=None,
        help="Arquivo com versao DeskRudder X.Y.Z "
        "(padrao: CLIENT_VERSION no Sciter, CLIENT_VERSION_FLUTTER no Flutter)",
    )
    ap.add_argument(
        "--profile",
        choices=("posto", "controle"),
        default="posto",
        help="posto=so-recebe (PDV); controle=atendente (pode iniciar sessao)",
    )
    ap.add_argument(
        "--ui",
        choices=("sciter", "flutter"),
        default="sciter",
        help="sciter=v1 congelado 1.x.x; flutter=2.x.x (atendente ou cliente)",
    )
    args = ap.parse_args()
    _selftest_sciter_copy()
    _selftest_flutter_home_footer()
    _selftest_client_version_linhas()
    src = args.rustdesk_src.resolve()
    if not (src / ".git").exists() and not (src / "Cargo.toml").is_file():
        print(f"Nao parece um clone rustdesk: {src}", file=sys.stderr)
        return 1

    profile: str = args.profile
    ui: str = args.ui
    configurar_canal_update(profile, ui)

    host, key = load_server(args.config.resolve())
    brand = args.branding.resolve()
    if args.client_version:
        version_file = args.client_version
    elif ui == "flutter" and profile == "posto":
        version_file = here / "CLIENT_VERSION_FLUTTER_CLIENTE"
    elif ui == "flutter":
        version_file = here / "CLIENT_VERSION_FLUTTER"
    else:
        version_file = here / "CLIENT_VERSION"
    client_version = load_client_version(version_file.resolve(), ui)
    print(f">> Branding DeskRudder em {src}")
    print(f"   profile={profile}")
    print(f"   ui={ui}")
    print(f"   host={host}")
    print(f"   client_version={client_version}")
    print(f"   update={UPDATE_VERSION_JSON_URL}")

    copy_icons(brand, src)  # inclui copy_flutter_icons quando o clone tem Flutter
    patch_cargo_bundle_name(src / "Cargo.toml")
    common_rs = src / "src" / "common.rs"
    ui_interface_rs = src / "src" / "ui_interface.rs"
    patch_client_version(
        src / "Cargo.toml",
        src / "libs" / "portable" / "Cargo.toml",
        common_rs,
        ui_interface_rs,
        client_version,
    )
    patch_portable_metadata(src / "libs" / "portable" / "Cargo.toml")

    # Ícone da janela/titlebar (Sciter get_icon): arte completa em 32px.
    png_icon = brand / "deskrudder-32.png"
    if not png_icon.is_file():
        png_icon = brand / "32x32.png"
    if not png_icon.is_file():
        png_icon = brand / "128x128.png"
    if not png_icon.is_file():
        png_icon = brand / "deskrudder-128.png"
    patch_sciter_window_icon(src / "src" / "ui.rs", png_icon)
    patch_window_display_name(src / "src" / "ui.rs")
    patch_powered_by(src / "src" / "lang")
    patch_flutter_powered_url(src / "flutter" / "lib" / "common.dart")
    patch_flutter_home_footer(
        src / "flutter" / "lib" / "desktop" / "pages" / "desktop_home_page.dart"
    )
    patch_flutter_deskremote_ui(src, host, key, profile)

    cfg_rs = src / "libs" / "hbb_common" / "src" / "config.rs"
    if not cfg_rs.is_file():
        print(f"Falta {cfg_rs} (submodule hbb_common?).", file=sys.stderr)
        return 1
    cfg_host, cfg_key = (host, key)
    if ui == "flutter":
        cfg_host, cfg_key = HOST_FLUTTER_CLIENTE_PENDENTE, KEY_FLUTTER_CLIENTE_PENDENTE
    patch_config_rs(cfg_rs, cfg_host, cfg_key)
    if profile == "posto":
        patch_incoming_only(cfg_rs)
    elif profile == "controle":
        patch_outgoing_only(cfg_rs)
    index_tis = src / "src" / "ui" / "index.tis"
    install_tis = src / "src" / "ui" / "install.tis"
    windows_rs = src / "src" / "platform" / "windows.rs"
    ui_rs = src / "src" / "ui.rs"
    if profile == "posto":
        patch_host_only_ui(index_tis, brand)
    patch_shortcut_display_name(windows_rs)
    patch_uninstall_completo(windows_rs)
    # UpdateMe antes do patch de URLs (ele ainda contem rustdesk.com no upstream).
    patch_update_check(common_rs)
    patch_update_banner(index_tis)
    patch_update_me_handler(ui_interface_rs)
    patch_silent_update(windows_rs)
    patch_file_transfer_defaults(common_rs)
    patch_transfer_file_spawn(src / "src" / "ui" / "remote.rs")
    patch_website_urls(index_tis, install_tis)
    patch_install_path(windows_rs, install_tis)
    patch_system_dark_theme(ui_rs, index_tis)
    patch_titlebar_symbols_visible(ui_rs)
    patch_sciter_uri_connect(ui_rs)
    patch_remote_session_title(ui_rs)
    patch_remote_dark_theme(
        src / "src" / "ui" / "remote.rs",
        src / "src" / "ui" / "remote.tis",
        src / "src" / "ui" / "common.css",
        src / "src" / "ui" / "header.css",
    )
    patch_windows_single_instance(windows_rs)
    patch_ui_single_instance(ui_rs)
    patch_install_version_label(install_tis)

    # Sanity: chave, host e servidor de produto presentes
    body = cfg_rs.read_text(encoding="utf-8")
    if "DeskRudder" not in body:
        print("Verificacao falhou apos patch.", file=sys.stderr)
        return 1
    if ui == "flutter":
        if HOST_FLUTTER_CLIENTE_PENDENTE not in body or KEY_FLUTTER_CLIENTE_PENDENTE not in body:
            print("Verificacao falhou: Flutter sem placeholder de servidor.", file=sys.stderr)
            return 1
        if host in body:
            print("Verificacao falhou: Flutter nao deve embutir o servidor da Duplex.", file=sys.stderr)
            return 1
    else:
        if host not in body or key not in body:
            print("Verificacao falhou apos patch.", file=sys.stderr)
            return 1
        if f'RwLock::new("{host}".to_owned())' not in body:
            print("Verificacao falhou: PROD_RENDEZVOUS_SERVER sem host.", file=sys.stderr)
            return 1
    if profile == "posto":
        if "DeskRemote: build so para ser acessado" not in body:
            print("Verificacao falhou: is_incoming_only nao patchado.", file=sys.stderr)
            return 1
        if "DeskRemote: build so para controlar" in body:
            print("Verificacao falhou: profile posto nao deve forcar outgoing_only.", file=sys.stderr)
            return 1
    elif profile == "controle":
        if "DeskRemote: build so para controlar" not in body:
            print("Verificacao falhou: is_outgoing_only nao patchado.", file=sys.stderr)
            return 1
        if "DeskRemote: build so para ser acessado" in body:
            print("Verificacao falhou: profile controle nao deve forcar incoming_only.", file=sys.stderr)
            return 1
    else:
        print(f"Verificacao falhou: profile desconhecido {profile!r}.", file=sys.stderr)
        return 1

    ui_body = ui_rs.read_text(encoding="utf-8")
    our_b64 = base64.b64encode(png_icon.read_bytes()).decode("ascii")
    if our_b64 not in ui_body:
        print("Verificacao falhou: get_icon() sem PNG DeskRemote.", file=sys.stderr)
        return 1
    if f'frame.set_title("{PRODUCT_DISPLAY_NAME}");' not in ui_body:
        print(
            f"Verificacao falhou: titlebar sem set_title({PRODUCT_DISPLAY_NAME}).",
            file=sys.stderr,
        )
        return 1
    if f'"{PRODUCT_DISPLAY_NAME}".to_owned()' not in ui_body:
        print(
            f"Verificacao falhou: UI get_app_name sem {PRODUCT_DISPLAY_NAME}.",
            file=sys.stderr,
        )
        return 1
    if "fn is_system_dark_theme" not in ui_body or "set_titlebar_dark" not in ui_body:
        print("Verificacao falhou: tema/titlebar ausente em ui.rs.", file=sys.stderr)
        return 1
    if "deskrudder_connect_args_from_uri" not in ui_body:
        print("Verificacao falhou: parser deskrudder:// ausente em ui.rs.", file=sys.stderr)
        return 1
    if 'strip_prefix("name=")' not in ui_body:
        print("Verificacao falhou: URI sem name= (titulo da sessao).", file=sys.stderr)
        return 1
    if "deskrudder_session_title_from_args" not in ui_body:
        print("Verificacao falhou: --title da sessao ausente em ui.rs.", file=sys.stderr)
        return 1
    if "deskrudder_enforce_single_instance" not in ui_body:
        print("Verificacao falhou: single-instance ausente em ui.rs.", file=sys.stderr)
        return 1
    if "deskrudder_enforce_single_instance(args)" not in ui_body:
        print("Verificacao falhou: single-instance nao chamado em start().", file=sys.stderr)
        return 1
    windows_body = windows_rs.read_text(encoding="utf-8")
    if "deskrudder_try_lock_main_instance" not in windows_body:
        print("Verificacao falhou: mutex da janela principal ausente.", file=sys.stderr)
        return 1
    if "deskrudder_try_lock_session_instance" not in windows_body:
        print("Verificacao falhou: mutex da sessao por ID ausente.", file=sys.stderr)
        return 1
    if "deskrudder_try_focus_window_by_titles" not in windows_body:
        print("Verificacao falhou: foco da janela existente ausente.", file=sys.stderr)
        return 1
    if "DwmSetWindowAttribute" not in ui_body:
        print("Verificacao falhou: DWM titlebar ausente.", file=sys.stderr)
        return 1
    remote_rs_body = (src / "src" / "ui" / "remote.rs").read_text(encoding="utf-8")
    if "fn is_system_dark_theme" not in remote_rs_body:
        print("Verificacao falhou: tema escuro ausente em remote.rs.", file=sys.stderr)
        return 1
    remote_tis_body = (src / "src" / "ui" / "remote.tis").read_text(encoding="utf-8")
    if "deskrudder_apply_remote_theme" not in remote_tis_body:
        print("Verificacao falhou: tema da sessao remota ausente.", file=sys.stderr)
        return 1

    index_body = index_tis.read_text(encoding="utf-8")
    if profile == "posto":
        if (
            f">{PRODUCT_DISPLAY_NAME}</div>" not in index_body
            or "deskrudder_host_logo" not in index_body
        ):
            print("Verificacao falhou: UI host-only sem logo/DeskRemote.", file=sys.stderr)
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
        if sciter_html(COPY_HOST_VERSAO) + " {handler.get_version()}" not in index_body:
            print("Verificacao falhou: versão não aparece na UI.", file=sys.stderr)
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
    if sciter_html(COPY_BANNER_TITULO) not in index_body:
        print("Verificacao falhou: banner de atualização ausente.", file=sys.stderr)
        return 1
    if sciter_html(COPY_BANNER_CORPO_ANTES) not in index_body:
        print("Verificacao falhou: texto do banner de atualização ausente.", file=sys.stderr)
        return 1
    if sciter_html(COPY_BANNER_CTA) not in index_body:
        print("Verificacao falhou: CTA do banner de atualização ausente.", file=sys.stderr)
        return 1
    if sciter_tis_str(COPY_BANNER_INSTALANDO) not in index_body:
        print("Verificacao falhou: fluxo in-app de update incompleto.", file=sys.stderr)
        return 1
    if sciter_tis_str(COPY_BANNER_ERRO_CORPO) not in index_body:
        print("Verificacao falhou: mensagem de erro do update ausente.", file=sys.stderr)
        return 1
    if any(b > 127 for b in index_tis.read_bytes()):
        print(
            "Verificacao falhou: index.tis tem byte não-ASCII "
            "(Sciter Windows quebra acentos UTF-8).",
            file=sys.stderr,
        )
        return 1
    if DOWNLOAD_INSTALLER_URL not in index_body:
        print("Verificacao falhou: URL de download do profile ausente no banner.", file=sys.stderr)
        return 1

    ui_iface = ui_interface_rs.read_text(encoding="utf-8")
    if "update_to(&_path)" not in ui_iface:
        print("Verificacao falhou: update_me sem update_to.", file=sys.stderr)
        return 1
    if "crate::DESKRUDDER_CLIENT_VERSION.to_owned()" not in ui_iface:
        print("Verificacao falhou: get_version() sem DESKRUDDER_CLIENT_VERSION.", file=sys.stderr)
        return 1

    cargo_body = (src / "Cargo.toml").read_text(encoding="utf-8")
    if re.search(rf'(?m)^version = "{re.escape(client_version)}"$', cargo_body):
        print(
            "Verificacao falhou: Cargo.toml nao pode usar CLIENT_VERSION "
            "(peer < 1.2.0 desliga modo mapa).",
            file=sys.stderr,
        )
        return 1
    if not re.search(r'(?m)^version = "1\.\d+\.\d+"$', cargo_body):
        print("Verificacao falhou: Cargo.toml sem versao RustDesk 1.x.", file=sys.stderr)
        return 1

    common_body = common_rs.read_text(encoding="utf-8")
    if "do_check_deskrudder_update" not in common_body:
        print("Verificacao falhou: check de update DeskRudder ausente.", file=sys.stderr)
        return 1
    if f'pub const DESKRUDDER_CLIENT_VERSION: &str = "{client_version}";' not in common_body:
        print("Verificacao falhou: DESKRUDDER_CLIENT_VERSION ausente.", file=sys.stderr)
        return 1
    if "get_version_number(crate::DESKRUDDER_CLIENT_VERSION)" not in common_body:
        print("Verificacao falhou: update check nao usa DESKRUDDER_CLIENT_VERSION.", file=sys.stderr)
        return 1
    if 'settings.insert("enable-file-transfer"' not in common_body:
        print("Verificacao falhou: default enable-file-transfer ausente.", file=sys.stderr)
        return 1
    if 'local.insert("enable-file-copy-paste"' not in common_body:
        print("Verificacao falhou: default enable-file-copy-paste ausente.", file=sys.stderr)
        return 1
    if "allow-scope-violation-close" not in common_body:
        print("Verificacao falhou: allow-scope-violation-close nao forcado.", file=sys.stderr)
        return 1

    install_body = install_tis.read_text(encoding="utf-8")
    if sciter_html(COPY_HOST_VERSAO) + " {handler.get_version()}" not in install_body:
        print("Verificacao falhou: versão ausente na tela de instalação.", file=sys.stderr)
        return 1
    if any(b > 127 for b in install_tis.read_bytes()):
        print(
            "Verificacao falhou: install.tis tem byte não-ASCII "
            "(Sciter Windows quebra acentos UTF-8).",
            file=sys.stderr,
        )
        return 1

    win_body = windows_rs.read_text(encoding="utf-8")
    if SHORTCUT_DISPLAY_NAME not in win_body:
        print(f"Verificacao falhou: atalho sem nome {PRODUCT_DISPLAY_NAME}.", file=sys.stderr)
        return 1
    if r"DeskRudder\\Acesso Remoto" not in win_body and "DeskRudder\\\\Acesso Remoto" not in win_body:
        # Fonte: "{}\\DeskRudder\\Acesso Remoto" -> Python ve "{}\\DeskRudder\\Acesso Remoto"
        if "DeskRudder\\Acesso Remoto" not in win_body:
            print("Verificacao falhou: pasta de instalacao Acesso Remoto ausente.", file=sys.stderr)
            return 1
    if "deskrudder_try_queue_silent_update" not in win_body:
        print("Verificacao falhou: fila de update silencioso ausente.", file=sys.stderr)
        return 1
    if "DeskRudder: watcher de update silencioso" not in win_body:
        print("Verificacao falhou: watcher de update silencioso nao iniciado no servico.", file=sys.stderr)
        return 1
    if "pending_update.txt" not in win_body:
        print("Verificacao falhou: caminho pending_update.txt ausente.", file=sys.stderr)
        return 1
    if "deskremote-dispositivo.json" not in win_body:
        print("Verificacao falhou: uninstall nao limpa AppData do DeskRemote.", file=sys.stderr)
        return 1
    if "%PROGRAMDATA%\\\\DeskRudder" not in win_body:
        print("Verificacao falhou: uninstall nao limpa ProgramData.", file=sys.stderr)
        return 1

    remote_body = (src / "src" / "ui" / "remote.rs").read_text(encoding="utf-8")
    if "DeskRudder: spawning file-transfer without password" not in remote_body:
        print("Verificacao falhou: transfer_file sem fallback de senha.", file=sys.stderr)
        return 1

    flutter_home = (
        src / "flutter" / "lib" / "desktop" / "pages" / "desktop_home_page.dart"
    )
    flutter_common = src / "flutter" / "lib" / "common.dart"
    if flutter_home.is_file():
        home_body = flutter_home.read_text(encoding="utf-8")
        if _FLUTTER_HOME_FOOTER_MARKER not in home_body:
            print(
                "Verificacao falhou: rodape Flutter (marca + versao) ausente.",
                file=sys.stderr,
            )
            return 1
        if "mainGetVersion()" not in home_body:
            print("Verificacao falhou: versao Flutter ausente no rodape.", file=sys.stderr)
            return 1
        if "DeskRemote: nome do app abaixo da logo" not in home_body:
            print("Verificacao falhou: nome DeskRemote ausente abaixo da logo.", file=sys.stderr)
            return 1
        if "DeskRemote: logo 160 + nome" not in home_body:
            print("Verificacao falhou: painel esquerdo Flutter ainda 200px.", file=sys.stderr)
            return 1
        if _FLUTTER_HOME_POWERED_TOP in home_body:
            print(
                "Verificacao falhou: Desenvolvido por ainda no topo do Flutter.",
                file=sys.stderr,
            )
            return 1
        if "DeskRemote: canal proprio (version.json)" not in home_body:
            print(
                "Verificacao falhou: banner de atualizacao Flutter ainda escondido no custom client.",
                file=sys.stderr,
            )
            return 1
        if "_deskRemoteBaixarAtualizacao" not in home_body:
            print("Verificacao falhou: download do Release Flutter ausente.", file=sys.stderr)
            return 1
    if flutter_common.is_file():
        common_dart = flutter_common.read_text(encoding="utf-8")
        if WEBSITE_URL.rstrip("/") not in common_dart:
            print(
                "Verificacao falhou: loadPowered Flutter sem deskrudder.com.br.",
                file=sys.stderr,
            )
            return 1
        if "DeskRemote: logo do painel" not in common_dart:
            print("Verificacao falhou: logo Flutter sem tamanho de painel.", file=sys.stderr)
            return 1
        if "FilterQuality.high" not in common_dart:
            print("Verificacao falhou: logo Flutter sem FilterQuality.high.", file=sys.stderr)
            return 1
        if "cacheWidth: 320" not in common_dart:
            print("Verificacao falhou: logo Flutter sem cacheWidth 320.", file=sys.stderr)
            return 1
        if "maxHeight: 160" not in common_dart:
            print("Verificacao falhou: logo Flutter ainda pequena no painel.", file=sys.stderr)
            return 1
        if "DeskRemote: ico com borda branca nítida na barra de título" not in common_dart:
            print("Verificacao falhou: loadIcon da barra sem nitidez.", file=sys.stderr)
            return 1
        if profile != "posto":
            if "deskremote/sessao.dart" not in common_dart:
                print("Verificacao falhou: common.dart sem import da busca de vinculo.", file=sys.stderr)
                return 1
            if "DeskRemote: busca vinculo na API se o painel nao mandou name=" not in common_dart:
                print("Verificacao falhou: alias do vinculo ausente no Flutter.", file=sys.stderr)
                return 1
            if "DeskRemote: busca vinculo na API no Conectar" not in common_dart:
                print("Verificacao falhou: Conectar do Flutter nao busca o vinculo.", file=sys.stderr)
                return 1
            if "DeskRemote: aplica o servidor da instancia" not in common_dart:
                print("Verificacao falhou: Flutter nao aplica o servidor da instancia.", file=sys.stderr)
                return 1
            if "DeskRemote: vinculo (alias) ou usuario@host na aba" not in common_dart:
                print("Verificacao falhou: aba da sessao Flutter ainda usa o ID.", file=sys.stderr)
                return 1
            if "DeskRemote: servidor Duplex" in common_dart or f'"{host}"' in common_dart:
                print("Verificacao falhou: Flutter do atendente ainda embute o servidor da Duplex.", file=sys.stderr)
                return 1
        flutter_assets = src / "flutter" / "assets" / "logo.png"
        if not flutter_assets.is_file():
            print("Verificacao falhou: flutter/assets/logo.png ausente.", file=sys.stderr)
            return 1
        flutter_icon = src / "flutter" / "assets" / "icon.png"
        if not flutter_icon.is_file():
            print("Verificacao falhou: flutter/assets/icon.png (titlebar) ausente.", file=sys.stderr)
            return 1
        if (src / "flutter" / "assets" / "icon.svg").is_file():
            print("Verificacao falhou: flutter/assets/icon.svg RustDesk ainda presente.", file=sys.stderr)
            return 1
    flutter_tabs = src / "flutter" / "lib" / "models" / "peer_tab_model.dart"
    if profile != "posto" and flutter_tabs.is_file():
        tabs_body = flutter_tabs.read_text(encoding="utf-8")
        if "DeskRemote: Recentes e Vinculados" not in tabs_body:
            print("Verificacao falhou: Flutter ainda nao mostra Recentes+Vinculados.", file=sys.stderr)
            return 1
        if "Vinculados" not in tabs_body:
            print("Verificacao falhou: rotulo Vinculados ausente nas abas.", file=sys.stderr)
            return 1
    flutter_peer_tab = src / "flutter" / "lib" / "common" / "widgets" / "peer_tab_page.dart"
    if profile != "posto" and flutter_peer_tab.is_file():
        peer_tab_body = flutter_peer_tab.read_text(encoding="utf-8")
        if "DeskRemoteVinculadosView" not in peer_tab_body:
            print("Verificacao falhou: aba Vinculados nao substitui Favoritos.", file=sys.stderr)
            return 1
        if "busca do RustDesk nao filtra Vinculados" not in peer_tab_body:
            print("Verificacao falhou: busca do RustDesk ainda aparece em Vinculados.", file=sys.stderr)
            return 1
    flutter_peers = src / "flutter" / "lib" / "common" / "widgets" / "peers_view.dart"
    if profile != "posto" and flutter_peers.is_file():
        peers_body = flutter_peers.read_text(encoding="utf-8")
        if "DeskRemote: 10 ultimas sessoes recentes" not in peers_body:
            print("Verificacao falhou: limite de 10 sessoes Flutter ausente.", file=sys.stderr)
            return 1
    flutter_card = src / "flutter" / "lib" / "common" / "widgets" / "peer_card.dart"
    if profile != "posto" and flutter_card.is_file():
        card_body = flutter_card.read_text(encoding="utf-8")
        if "DeskRemote: nome do vinculo" not in card_body:
            print("Verificacao falhou: cartao Flutter ainda mostra ID.", file=sys.stderr)
            return 1
    flutter_tabbar = src / "flutter" / "lib" / "desktop" / "widgets" / "tabbar_widget.dart"
    if flutter_tabbar.is_file():
        tabbar_body = flutter_tabbar.read_text(encoding="utf-8")
        if "DeskRemote: titulo da barra customizada" not in tabbar_body:
            print("Verificacao falhou: titulo da barra Flutter ainda RustDesk.", file=sys.stderr)
            return 1
        if "DeskRemote: nome do app na barra" not in tabbar_body:
            print("Verificacao falhou: showTitle da barra Flutter ainda false.", file=sys.stderr)
            return 1
        if "loadIcon(24)" not in tabbar_body:
            print("Verificacao falhou: ico da barra de titulo ainda 16px.", file=sys.stderr)
            return 1
    flutter_consts = src / "flutter" / "lib" / "consts.dart"
    if flutter_consts.is_file():
        consts_body = flutter_consts.read_text(encoding="utf-8")
        if "DeskRemote: ico 24px + nome na barra" not in consts_body:
            print("Verificacao falhou: altura da barra Flutter ainda 28px.", file=sys.stderr)
            return 1
        if profile != "posto" and "DeskRemote: aba reage a alias" not in tabbar_body:
            print("Verificacao falhou: tablabelGetter Flutter nao reage ao vinculo.", file=sys.stderr)
            return 1
    flutter_main_tab = src / "flutter" / "lib" / "desktop" / "pages" / "desktop_tab_page.dart"
    if flutter_main_tab.is_file():
        main_tab_body = flutter_main_tab.read_text(encoding="utf-8")
        if "showTitle: true" not in main_tab_body:
            print("Verificacao falhou: home Flutter sem nome na barra.", file=sys.stderr)
            return 1
        if profile == "posto":
            if "DeskRemote: cliente so abre depois do token de instalacao" not in main_tab_body:
                print("Verificacao falhou: token de instalacao ausente na home Flutter.", file=sys.stderr)
                return 1
            overlay_enroll = src / "flutter" / "lib" / "deskremote" / "enroll.dart"
            overlay_enroll_gate = src / "flutter" / "lib" / "deskremote" / "enroll_gate.dart"
            if not overlay_enroll.is_file() or not overlay_enroll_gate.is_file():
                print("Verificacao falhou: dart DeskRemote (enroll) ausente no clone.", file=sys.stderr)
                return 1
            enroll_txt = overlay_enroll.read_text(encoding="utf-8")
            if "mainSetPermanentPasswordWithResult" not in enroll_txt:
                print("Verificacao falhou: enroll sem senha permanente.", file=sys.stderr)
                return 1
            if "mainSetOption(key: 'custom-rendezvous-server'" not in enroll_txt:
                print("Verificacao falhou: enroll sem mainSetOption do hbbs.", file=sys.stderr)
                return 1
            if flutter_common.is_file():
                common_lock = flutter_common.read_text(encoding="utf-8")
                if "DeskRemote: senha permanente so muda no painel" not in common_lock:
                    print("Verificacao falhou: common.dart ainda permite editar senha.", file=sys.stderr)
                    return 1
            if flutter_home.is_file():
                home_lock = flutter_home.read_text(encoding="utf-8")
                if "DeskRemote: senha permanente so no painel" not in home_lock:
                    print("Verificacao falhou: home Flutter ainda tem lapis de senha.", file=sys.stderr)
                    return 1
        else:
            if "DeskRemote: Recentes/Conectar exigem login DeskRudder" not in main_tab_body:
                print("Verificacao falhou: login DeskRudder ausente na home Flutter.", file=sys.stderr)
                return 1
            overlay_sessao = src / "flutter" / "lib" / "deskremote" / "sessao.dart"
            overlay_gate = src / "flutter" / "lib" / "deskremote" / "auth_gate.dart"
            overlay_vinc = src / "flutter" / "lib" / "deskremote" / "vinculados.dart"
            if not overlay_sessao.is_file() or not overlay_gate.is_file() or not overlay_vinc.is_file():
                print("Verificacao falhou: dart DeskRemote (login/vinculados) ausente no clone.", file=sys.stderr)
                return 1
            overlay_sessao_txt = overlay_sessao.read_text(encoding="utf-8")
            if "https://api-$slug." not in overlay_sessao_txt:
                print("Verificacao falhou: login Flutter nao usa api-{slug}.", file=sys.stderr)
                return 1
            if "https://$slug.$kDeskRemoteApex/v1" in overlay_sessao_txt:
                print("Verificacao falhou: login Flutter ainda chama o host do painel.", file=sys.stderr)
                return 1
            if "buscarRotuloVinculoDeskRemote" not in overlay_sessao_txt:
                print("Verificacao falhou: busca do vinculo na frota ausente no overlay.", file=sys.stderr)
                return 1
            if "listarFrotaVinculadaDeskRemote" not in overlay_sessao_txt:
                print("Verificacao falhou: listagem da frota Vinculados ausente no overlay.", file=sys.stderr)
                return 1
            if "/rustdesk/configuracao" not in overlay_sessao_txt:
                print("Verificacao falhou: overlay sem GET /rustdesk/configuracao.", file=sys.stderr)
                return 1
            if "aplicarServidorDaContaDeskRemote" not in overlay_sessao_txt:
                print("Verificacao falhou: overlay sem aplicar servidor da instancia.", file=sys.stderr)
                return 1
            overlay_gate_txt = overlay_gate.read_text(encoding="utf-8")
            if "aplicarServidorDaContaDeskRemote" not in overlay_gate_txt:
                print("Verificacao falhou: login Flutter sem aplicar servidor da instancia.", file=sys.stderr)
                return 1
            if "_pararPoll" not in overlay_gate_txt:
                print("Verificacao falhou: login Flutter nao para o poll sem servidor.", file=sys.stderr)
                return 1
    flutter_multi = src / "flutter" / "lib" / "utils" / "multi_window_manager.dart"
    if profile != "posto" and flutter_multi.is_file():
        multi_body = flutter_multi.read_text(encoding="utf-8")
        if "DeskRemote: title na janela da sessao" not in multi_body:
            print("Verificacao falhou: newSession sem title do vinculo.", file=sys.stderr)
            return 1
    flutter_remote = src / "flutter" / "lib" / "desktop" / "pages" / "remote_tab_page.dart"
    if profile != "posto" and flutter_remote.is_file():
        remote_body = flutter_remote.read_text(encoding="utf-8")
        if "DeskRemote: titulo do vinculo na aba" not in remote_body:
            print("Verificacao falhou: aba remota sem titulo do vinculo.", file=sys.stderr)
            return 1
    flutter_model = src / "flutter" / "lib" / "models" / "model.dart"
    if profile != "posto" and flutter_model.is_file():
        model_body = flutter_model.read_text(encoding="utf-8")
        if "DeskRemote: atualiza a aba quando chega usuario/host" not in model_body:
            print("Verificacao falhou: peer_info Flutter nao atualiza a aba.", file=sys.stderr)
            return 1
    flutter_settings = (
        src / "flutter" / "lib" / "desktop" / "pages" / "desktop_setting_page.dart"
    )
    if flutter_settings.is_file():
        settings_body = flutter_settings.read_text(encoding="utf-8")
        if "Sobre o DeskRemote" not in settings_body:
            print("Verificacao falhou: Sobre o DeskRemote ausente.", file=sys.stderr)
            return 1
        if "Desenvolvido pela DeskRudder" not in settings_body:
            print("Verificacao falhou: desenvolvido pela DeskRudder ausente no Sobre.", file=sys.stderr)
            return 1
        if "privacy.html" in settings_body:
            print("Verificacao falhou: Sobre ainda linka privacidade do RustDesk.", file=sys.stderr)
            return 1
        if "Purslane" in settings_body:
            print("Verificacao falhou: copyright Purslane ainda no Sobre.", file=sys.stderr)
            return 1
        if WEBSITE_URL.rstrip("/") not in settings_body:
            print("Verificacao falhou: website do Sobre sem deskrudder.com.br.", file=sys.stderr)
            return 1
        if "DeskRemote: host Duplex na Rede" in settings_body:
            print("Verificacao falhou: Flutter ainda mostra o host da Duplex em Rede.", file=sys.stderr)
            return 1
    flutter_rc = src / "flutter" / "windows" / "runner" / "Runner.rc"
    if flutter_rc.is_file():
        rc_body = flutter_rc.read_text(encoding="utf-8")
        if COPYRIGHT_LINE not in rc_body or "Purslane" in rc_body:
            print("Verificacao falhou: Runner.rc sem copyright DeskRudder.", file=sys.stderr)
            return 1
    core_main_body_path = src / "src" / "core_main.rs"
    if (
        profile != "posto"
        and core_main_body_path.is_file()
        and (src / "flutter" / "lib" / "common.dart").is_file()
    ):
        core_body = core_main_body_path.read_text(encoding="utf-8")
        if "DeskRemote: --title vira name=" not in core_body:
            print("Verificacao falhou: core_main sem --title do vinculo.", file=sys.stderr)
            return 1
        if "DeskRemote: senha posicional" not in core_body:
            print("Verificacao falhou: core_main sem senha posicional do Electron.", file=sys.stderr)
            return 1
        if "DeskRemote: no frio, entrega o uni-link" not in core_body:
            print("Verificacao falhou: core_main nao entrega uni-link no frio.", file=sys.stderr)
            return 1

    print(">> OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
