#!/usr/bin/env python3
"""
Prepara manifest de releases e release-notes.json (#401).

Modo --deploy: bump CalVer, consome seção [Unreleased] do CHANGELOG e atualiza artefatos.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from bump_calver import next_calver, version_display

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
MANIFEST_FILE = ROOT / "docs" / "releases" / "manifest.json"
BACKEND_DATA = ROOT / "backend" / "app" / "data" / "release_notes.json"
FRONTEND_PUBLIC = ROOT / "frontend" / "public" / "release-notes.json"

CATEGORY_MAP = {
    "melhorias": "melhorias",
    "melhoria": "melhorias",
    "added": "melhorias",
    "correcoes": "correcoes",
    "correção": "correcoes",
    "correcao": "correcoes",
    "fixed": "correcoes",
    "interno": "interno",
    "infra": "interno",
    "internal": "interno",
    "changed": "melhorias",
}

_LEGACY_BRAND_RE = re.compile(r"DX/Duplexsoft|Duplexsoft|DX Connect|DX-Connect", re.IGNORECASE)


def sanitize_release_text(text: str) -> str:
    """Remove referências à marca legada em textos voltados ao usuário (release notes)."""
    result = text
    for old, new in (
        (
            "painel lateral do login e assets legados DX/Duplexsoft removidos — marca DeskRudder em todo o painel",
            "marca DeskRudder no login e em todo o painel",
        ),
        (
            "assets legados DX/Duplexsoft removidos — marca DeskRudder em todo o painel",
            "marca DeskRudder no login e em todo o painel",
        ),
    ):
        result = result.replace(old, new)
    if _LEGACY_BRAND_RE.search(result) and "Identidade visual (#434)" in result:
        return "Identidade visual (#434): marca DeskRudder no login e em todo o painel"
    return result


def _today_sp() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _load_manifest() -> dict:
    if not MANIFEST_FILE.is_file():
        return {"releases": []}
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def _save_manifest(data: dict) -> None:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_changelog_unreleased(text: str) -> list[dict[str, str]]:
    """Extrai bullets da seção [Unreleased] agrupados por ### categoria."""
    m = re.search(r"## \[Unreleased\](.*?)(?=\n## \[|\Z)", text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    body = m.group(1)
    changes: list[dict[str, str]] = []
    current_cat = "melhorias"
    for line in body.splitlines():
        hdr = re.match(r"^###\s+(.+)$", line.strip())
        if hdr:
            key = hdr.group(1).strip().lower()
            current_cat = CATEGORY_MAP.get(key, "melhorias")
            continue
        bullet = re.match(r"^-\s+(.+)$", line.strip())
        if bullet:
            changes.append(
                {"category": current_cat, "text": sanitize_release_text(bullet.group(1).strip())}
            )
    return changes


def finalize_changelog_release(text: str, version: str, date: str) -> str:
    """Move [Unreleased] para [version] e recria [Unreleased] vazio."""
    unreleased = parse_changelog_unreleased(text)
    if not unreleased:
        return text
    block_lines = [f"## [{version}] - {date}", ""]
    by_cat: dict[str, list[str]] = {}
    for c in unreleased:
        label = c["category"]
        cat_title = {
            "melhorias": "Melhorias",
            "correcoes": "Correções",
            "interno": "Interno / Infra",
        }.get(label, "Melhorias")
        by_cat.setdefault(cat_title, []).append(c["text"])
    for cat_title, items in by_cat.items():
        block_lines.append(f"### {cat_title}")
        block_lines.append("")
        for item in items:
            block_lines.append(f"- {item}")
        block_lines.append("")
    new_block = "\n".join(block_lines).rstrip() + "\n"

    without_unreleased = re.sub(
        r"## \[Unreleased\].*?(?=\n## \[|\Z)",
        "## [Unreleased]\n\n",
        text,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Insere release após cabeçalho Unreleased
    parts = without_unreleased.split("## [Unreleased]", 1)
    if len(parts) != 2:
        return text
    return parts[0] + "## [Unreleased]\n\n" + new_block + "\n" + parts[1].lstrip("\n")


def build_payload(*, current_version: str | None, manifest: dict, upcoming: list[dict]) -> dict:
    releases = []
    for rel in manifest.get("releases") or []:
        entry = dict(rel)
        entry["changes"] = [
            {**ch, "text": sanitize_release_text(ch["text"])}
            if isinstance(ch, dict) and isinstance(ch.get("text"), str)
            else ch
            for ch in entry.get("changes") or []
        ]
        releases.append(entry)
    current = None
    if current_version:
        for rel in releases:
            if rel.get("version") == current_version:
                current = rel
                break
        if current is None and releases:
            current = releases[-1]
    return {
        "current_version": current_version,
        "current_version_display": version_display(current_version) if current_version else None,
        "current": current,
        "releases": releases,
        "upcoming": upcoming,
    }


def write_release_notes(payload: dict) -> None:
    BACKEND_DATA.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    BACKEND_DATA.write_text(text, encoding="utf-8")
    FRONTEND_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_PUBLIC.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true", help="Bump CalVer e publica release a partir do CHANGELOG")
    ap.add_argument("--write-env", action="store_true", help="Imprime DX_CONNECT_VERSION= para GITHUB_ENV")
    ap.add_argument("--version", help="Força versão (sem bump)")
    args = ap.parse_args()

    current_raw = _read_text(VERSION_FILE).strip()
    changelog = _read_text(CHANGELOG_FILE)
    manifest = _load_manifest()

    version = args.version
    if args.deploy:
        version = next_calver(current_raw or None)
        changes = parse_changelog_unreleased(changelog)
        if not changes:
            changes = [{"category": "interno", "text": "Atualização do sistema"}]
        entry = {
            "version": version,
            "version_display": version_display(version),
            "date": _today_sp(),
            "status": "published",
            "changes": changes,
        }
        manifest.setdefault("releases", []).append(entry)
        _save_manifest(manifest)
        VERSION_FILE.write_text(version + "\n", encoding="utf-8")
        if changelog.strip():
            CHANGELOG_FILE.write_text(finalize_changelog_release(changelog, version, _today_sp()), encoding="utf-8")
        current_raw = version
    elif version:
        current_raw = version

    payload = build_payload(current_version=current_raw or None, manifest=manifest, upcoming=[])
    write_release_notes(payload)

    if args.write_env and current_raw:
        print(f"DX_CONNECT_VERSION={current_raw}")
        print(f"VITE_APP_VERSION={current_raw}")
        print(f"VITE_APP_VERSION_DISPLAY={version_display(current_raw)}")

    if args.deploy:
        print(f"Release preparada: {version_display(current_raw)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
