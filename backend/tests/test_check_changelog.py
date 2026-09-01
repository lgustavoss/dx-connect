"""Testes do validador de CHANGELOG (#400 / #673)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_changelog import (  # noqa: E402
    is_deps_only_change,
    is_saas_path,
    parse_unreleased_bullets,
    products_required_by_paths,
    requires_changelog,
)
from prepare_release import parse_changelog_unreleased  # noqa: E402


def test_parse_unreleased_bullets():
    text = """## [Unreleased]

### DeskRudder

#### Melhorias

- Item A (#1)

## [26.06.001] - 2026-06-22

- Old
"""
    assert parse_unreleased_bullets(text) == ["Item A (#1)"]


def test_parse_changelog_com_produtos():
    text = """## [Unreleased]

### DeskRudder

#### Correções

- Fix chat (#1)

### SaaS Control Plane

#### Melhorias

- Licenças (#2)
"""
    changes = parse_changelog_unreleased(text, warn_legacy=False)
    assert len(changes) == 2
    assert changes[0] == {"product": "deskrudder", "category": "correcoes", "text": "Fix chat (#1)"}
    assert changes[1] == {"product": "saas", "category": "melhorias", "text": "Licenças (#2)"}


def test_parse_changelog_legado_vira_deskrudder():
    text = """## [Unreleased]

### Corrigido

- Algo antigo (#9)
"""
    changes = parse_changelog_unreleased(text, warn_legacy=False)
    assert changes == [{"product": "deskrudder", "category": "correcoes", "text": "Algo antigo (#9)"}]


def test_requires_changelog_product_paths():
    assert requires_changelog(["frontend/src/pages/Foo.tsx"]) is True
    assert requires_changelog(["docs/RELEASES.md"]) is False
    assert requires_changelog(["CHANGELOG.md"]) is False


def test_requires_changelog_deps_only():
    assert is_deps_only_change(["frontend/package.json", "frontend/package-lock.json"]) is True
    assert is_deps_only_change(["backend/requirements.txt"]) is True
    assert requires_changelog(["frontend/package.json", "frontend/package-lock.json"]) is False
    assert requires_changelog(["backend/requirements.txt", "backend/requirements-dev.txt"]) is False


def test_requires_changelog_deps_plus_product():
    assert is_deps_only_change(["frontend/package.json", "frontend/src/pages/Foo.tsx"]) is False
    assert requires_changelog(["frontend/package-lock.json", "frontend/src/App.tsx"]) is True


def test_saas_path_heuristic():
    assert is_saas_path("frontend/src/pages/saas/SaasSobre.tsx") is True
    assert is_saas_path("backend/app/api/saas.py") is True
    assert is_saas_path("backend/app/services/saas_clientes.py") is True
    assert is_saas_path("frontend/src/pages/Sobre.tsx") is False


def test_products_required_by_paths_misto():
    needed = products_required_by_paths(
        [
            "frontend/src/pages/saas/SaasSobre.tsx",
            "frontend/src/pages/Sobre.tsx",
        ]
    )
    assert needed == {"deskrudder", "saas"}


def test_check_changelog_script_ok_without_product_diff():
    if shutil.which("git") is None:
        pytest.skip("git não está na PATH (imagem backend sem git; CI tem)")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_changelog.py"), "--base", "HEAD", "--head", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
