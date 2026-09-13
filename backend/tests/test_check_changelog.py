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
    compose_changelog_for_main_sync,
    compose_changelog_for_staging_pr,
    extract_published_history,
    extract_unreleased_block,
    has_new_published_version,
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


def test_requires_changelog_tests_only():
    assert requires_changelog(["backend/tests/test_faturamento.py"]) is False
    assert requires_changelog(["backend/tests/test_foo.py", "backend/app/api/foo.py"]) is True


def test_saas_path_heuristic():
    assert is_saas_path("frontend/src/pages/saas/SaasSobre.tsx") is True
    assert is_saas_path("backend/app/api/saas.py") is True
    assert is_saas_path("backend/app/services/saas_clientes.py") is True
    assert is_saas_path("backend/alembic/versions/136_saas_alertas_ops_1036.py") is True
    assert is_saas_path("backend/alembic/versions/100_ponto_foo.py") is False
    assert is_saas_path("frontend/src/pages/Sobre.tsx") is False


def test_products_required_by_paths_misto():
    needed = products_required_by_paths(
        [
            "frontend/src/pages/saas/SaasSobre.tsx",
            "frontend/src/pages/Sobre.tsx",
        ]
    )
    assert needed == {"deskrudder", "saas"}


def test_products_required_saas_com_wiring_compartilhado():
    """Registo de rota SaaS em main/App/client não exige ### DeskRudder."""
    needed = products_required_by_paths(
        [
            "backend/app/api/saas_alertas.py",
            "backend/app/services/saas_alertas_ops.py",
            "backend/alembic/versions/136_saas_alertas_ops_1036.py",
            "backend/app/main.py",
            "backend/app/config.py",
            "backend/app/models/__init__.py",
            "frontend/src/App.tsx",
            "frontend/src/api/client.ts",
            "frontend/src/pages/saas/SaasAlertas.tsx",
        ]
    )
    assert needed == {"saas"}


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


_PREAMBLE = """# Changelog

Formato baseado em Keep a Changelog.

"""

_PUBLISHED = """## [26.08.019] - 2026-08-31

### DeskRudder

#### Melhorias

- Contato no chat (#1012)
"""

_HEAD_UNRELEASED = """## [Unreleased]

### DeskRudder

#### Melhorias

- WhatsApp retenção de mídia (#899)
"""


def test_compose_staging_pr_keeps_head_unreleased():
    staging = _PREAMBLE + "## [Unreleased]\n\n" + _PUBLISHED
    head = _PREAMBLE + _HEAD_UNRELEASED + _PUBLISHED
    out = compose_changelog_for_staging_pr(staging, head)
    assert parse_unreleased_bullets(out) == ["WhatsApp retenção de mídia (#899)"]
    assert "## [26.08.019]" in out
    assert out.count("## [Unreleased]") == 1


def test_compose_staging_pr_empty_head_stays_empty():
    staging = _PREAMBLE + "## [Unreleased]\n\n" + _PUBLISHED
    head = _PREAMBLE + "## [Unreleased]\n\n" + _PUBLISHED
    out = compose_changelog_for_staging_pr(staging, head)
    assert parse_unreleased_bullets(out) == []


def test_extract_published_skips_unreleased():
    text = _PREAMBLE + _HEAD_UNRELEASED + _PUBLISHED
    hist = extract_published_history(text)
    assert hist.startswith("## [26.08.019]")
    assert "WhatsApp" not in hist


def test_compose_main_sync_drops_published_bullets():
    staging = (
        _PREAMBLE
        + "## [Unreleased]\n\n"
        + "## [26.09.001] - 2026-09-12\n\n### DeskRudder\n\n#### Melhorias\n\n"
        + "- WhatsApp retenção de mídia (#899)\n\n"
        + _PUBLISHED
    )
    main = _PREAMBLE + _HEAD_UNRELEASED + _PUBLISHED
    out = compose_changelog_for_main_sync(main, staging)
    assert parse_unreleased_bullets(out) == []
    assert "## [26.09.001]" in out


def test_compose_main_sync_keeps_unpublished_bullets():
    staging = _PREAMBLE + "## [Unreleased]\n\n" + _PUBLISHED
    main = (
        _PREAMBLE
        + "## [Unreleased]\n\n### DeskRudder\n\n#### Melhorias\n\n"
        + "- WhatsApp retenção de mídia (#899)\n"
        + "- Feature nova só na main (#1100)\n\n"
        + _PUBLISHED
    )
    out = compose_changelog_for_main_sync(main, staging)
    assert parse_unreleased_bullets(out) == [
        "WhatsApp retenção de mídia (#899)",
        "Feature nova só na main (#1100)",
    ]


def test_extract_unreleased_block_present():
    block = extract_unreleased_block(_PREAMBLE + _HEAD_UNRELEASED + _PUBLISHED)
    assert block.startswith("## [Unreleased]")
    assert "WhatsApp" in block
    assert "26.08.019" not in block


def test_has_new_published_version_passo5():
    base = _PREAMBLE + "## [Unreleased]\n\n" + _PUBLISHED
    head = _PREAMBLE + "## [Unreleased]\n\n## [26.09.001] - 2026-09-12\n\n- x\n\n" + _PUBLISHED
    assert has_new_published_version(base, head) is True
    assert has_new_published_version(head, head) is False
