"""Testes do validador de CHANGELOG (#400)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_changelog import parse_unreleased_bullets, requires_changelog  # noqa: E402


def test_parse_unreleased_bullets():
    text = """## [Unreleased]

### Melhorias

- Item A (#1)

## [26.06.001] - 2026-06-22

- Old
"""
    assert parse_unreleased_bullets(text) == ["Item A (#1)"]


def test_requires_changelog_product_paths():
    assert requires_changelog(["frontend/src/pages/Foo.tsx"]) is True
    assert requires_changelog(["docs/RELEASES.md"]) is False
    assert requires_changelog(["CHANGELOG.md"]) is False


def test_check_changelog_script_ok_without_product_diff():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_changelog.py"), "--base", "HEAD", "--head", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
