"""Deploy GHA em duas stacks (#880) — contrato de secrets e artefactos."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WF = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
SCRIPT = (ROOT / "deploy" / "scripts" / "gha-deploy-vps.sh").read_text(encoding="utf-8")
DOCS = (ROOT / "deploy" / "github-actions.md").read_text(encoding="utf-8")


def test_workflow_exige_dois_vite_e_dois_dist():
    assert "VITE_API_URL_ADMIN" in WF
    assert "DEPLOY_FRONTEND_DIST_ADMIN" in WF
    assert "dist-duplexsoft" in WF
    assert "dist-admin-center" in WF
    assert "VITE_SAAS_CONTROL_PLANE" in WF
    assert "deploy/admin-center/**" in WF


def test_gha_script_atualiza_admin_center_e_bloqueia_saas_no_cliente():
    assert "stack-client.sh migrate admin-center" in SCRIPT
    assert "stack-client.sh up admin-center" in SCRIPT
    assert "saas_control_plane=true" in SCRIPT
    assert "SAAS_CONTROL_PLANE=true" in SCRIPT  # guarda no .env do cliente
    assert "dist-admin-center" in SCRIPT
    assert "dist-duplexsoft" in SCRIPT
    assert "VITE_API_URL_ADMIN" in SCRIPT


def test_docs_listam_secrets_novos():
    assert "VITE_API_URL_ADMIN" in DOCS
    assert "DEPLOY_FRONTEND_DIST_ADMIN" in DOCS
    assert "api.deskrudder.com.br" in DOCS
    assert "#880" in DOCS
