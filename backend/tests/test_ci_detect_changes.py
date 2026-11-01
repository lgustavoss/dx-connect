"""Detecção de paths para pular pytest/build no CI e no /revisar-e-testar."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if not (SCRIPTS / "ci_detect_changes.py").is_file():
    SCRIPTS = Path("/scripts")
sys.path.insert(0, str(SCRIPTS))

from ci_detect_changes import classify, format_result, path_matches  # noqa: E402


def test_frontend_only_nao_dispara_backend():
    result = classify(
        [
            "frontend/src/components/Sidebar.tsx",
            "frontend/src/index.css",
        ]
    )
    assert result == {"backend": False, "frontend": True, "mobile": False}


def test_backend_only_nao_dispara_frontend():
    result = classify(["backend/app/api/tickets.py", "backend/tests/test_health.py"])
    assert result == {"backend": True, "frontend": False, "mobile": False}


def test_ci_yml_dispara_os_tres():
    result = classify([".github/workflows/ci.yml"])
    assert result == {"backend": True, "frontend": True, "mobile": True}


def test_scripts_dispara_backend():
    result = classify(["scripts/ci_detect_changes.py"])
    assert result == {"backend": True, "frontend": False, "mobile": False}


def test_docs_e_cursor_nao_disparam_jobs_pesados():
    result = classify(
        [
            "docs/RELEASES.md",
            ".cursor/commands/revisar-e-testar.md",
            "CHANGELOG.md",
        ]
    )
    assert result == {"backend": False, "frontend": False, "mobile": False}


def test_format_result():
    assert (
        format_result({"backend": True, "frontend": False, "mobile": False})
        == "backend=true\nfrontend=false\nmobile=false"
    )


def test_mobile_only_nao_dispara_frontend_nem_backend():
    result = classify(["mobile/src/screens/LoginScreen.tsx", "mobile/package.json"])
    assert result == {"backend": False, "frontend": False, "mobile": True}


def test_path_matches_normaliza_barra():
    assert path_matches("frontend\\src\\App.tsx", ("frontend/",)) is True
    assert path_matches(".github/workflows/ci.yml", (".github/workflows/ci.yml",)) is True
