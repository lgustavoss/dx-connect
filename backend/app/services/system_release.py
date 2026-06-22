"""Versão CalVer e release notes (#401)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REPO_ROOT = Path(__file__).resolve().parents[3]


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
    releases: list[dict[str, Any]] = list(raw.get("releases") or [])
    upcoming: list[dict[str, Any]] = list(raw.get("upcoming") or [])

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
        "upcoming": upcoming,
    }


def system_info_payload() -> dict[str, Any]:
    version = resolve_app_version()
    return {
        "version": version,
        "version_display": version_display(version) if version else None,
        "git_sha": (os.environ.get("DX_CONNECT_GIT_SHA") or "").strip() or None,
        "environment": settings.ENVIRONMENT,
    }
