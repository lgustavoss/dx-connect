"""Versão CalVer e release notes (#401)."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REPO_ROOT = Path(__file__).resolve().parents[3]

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


def _sanitize_release(rel: dict[str, Any] | None) -> dict[str, Any] | None:
    if not rel:
        return rel
    out = dict(rel)
    changes = []
    for ch in out.get("changes") or []:
        if not isinstance(ch, dict):
            changes.append(ch)
            continue
        item = dict(ch)
        if isinstance(item.get("text"), str):
            item["text"] = sanitize_release_text(item["text"])
        changes.append(item)
    out["changes"] = changes
    return out


def version_display(version: str) -> str:
    v = version.strip().lstrip("v")
    return f"v{v}"


def _read_version_file() -> str | None:
    for candidate in (_REPO_ROOT / "VERSION", Path.cwd() / "VERSION"):
        if candidate.is_file():
            raw = candidate.read_text(encoding="utf-8").strip()
            if raw:
                return raw.lstrip("v")
    return None


def resolve_app_version() -> str | None:
    env = (os.environ.get("DX_CONNECT_VERSION") or "").strip().lstrip("v")
    if env:
        return env
    return _read_version_file()


@lru_cache(maxsize=1)
def _load_release_notes_raw() -> dict[str, Any]:
    path = _DATA_DIR / "release_notes.json"
    if not path.is_file():
        return {"releases": [], "upcoming": []}
    return json.loads(path.read_text(encoding="utf-8"))


def reload_release_notes_cache() -> None:
    _load_release_notes_raw.cache_clear()


def release_notes_payload(*, version_override: str | None = None) -> dict[str, Any]:
    raw = _load_release_notes_raw()
    version = version_override or resolve_app_version()
    releases: list[dict[str, Any]] = [_sanitize_release(r) or r for r in (raw.get("releases") or [])]

    current = None
    if version:
        for rel in releases:
            if rel.get("version") == version:
                current = rel
                break
        if current is None and releases:
            current = releases[-1]

    return {
        "current_version": version,
        "current_version_display": version_display(version) if version else None,
        "current": current,
        "releases": releases,
        "upcoming": [],
    }


def system_info_payload() -> dict[str, Any]:
    version = resolve_app_version()
    return {
        "version": version,
        "version_display": version_display(version) if version else None,
        "git_sha": (os.environ.get("DX_CONNECT_GIT_SHA") or "").strip() or None,
        "environment": settings.ENVIRONMENT,
    }
