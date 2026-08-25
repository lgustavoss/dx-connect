"""Templates e seed do control-plane comercial (#875 / #876)."""

from pathlib import Path

from app.models import Atendente, Tenant
from app.seed import _ensure_saas_ops_producao

ROOT = Path(__file__).resolve().parents[2]
CP = ROOT / "deploy" / "admin-center"


def test_templates_api_comercial_nao_e_duplexsoft():
    nginx = (CP / "nginx.site.conf.example").read_text(encoding="utf-8")
    assert "server_name api.deskrudder.com.br" in nginx
    assert "127.0.0.1:8001" in nginx
    assert "server_name api-duplexsoft" not in nginx
    front = (CP / "frontend.env.production.example").read_text(encoding="utf-8")
    assert "VITE_API_URL=https://api.deskrudder.com.br" in front
    assert "VITE_SAAS_CONTROL_PLANE=true" in front
    env = (CP / "client.env.example").read_text(encoding="utf-8")
    assert "CLIENT_SLUG=admin-center" in env
    assert "SAAS_CONTROL_PLANE=true" in env
    assert "SAAS_PROVISION_API_PORT_START=8002" in env
    assert "SAAS_INGEST_PUBLIC_URL=https://api.deskrudder.com.br/v1/saas/ingest/solicitacoes" in env
    script = (ROOT / "deploy" / "scripts" / "provision-client.sh").read_text(encoding="utf-8")
    assert "provision-control-plane.sh" in script
    assert "deploy/admin-center" in script
    compose = (CP / "docker-compose.stack.yml").read_text(encoding="utf-8")
    assert "context: ../../backend" in compose


def test_seed_saas_ops_producao_cria_conta(db_session, monkeypatch):
    from app.config import settings

    db_session.add(Tenant(id=1, nome="Padrão", ativo=True))
    db_session.commit()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SEED_SAAS_OPS_EMAIL", "ops@deskrudder.com.br")
    monkeypatch.setattr(settings, "SEED_SAAS_OPS_PASSWORD", "temporaria8")
    _ensure_saas_ops_producao(db_session)
    row = db_session.query(Atendente).filter(Atendente.email == "ops@deskrudder.com.br").one()
    assert row.role == "saas_ops"
    assert row.must_change_password is True
    _ensure_saas_ops_producao(db_session)
    assert db_session.query(Atendente).filter(Atendente.role == "saas_ops").count() == 1


def test_seed_saas_ops_nao_cria_em_dev(db_session, monkeypatch):
    from app.config import settings

    db_session.add(Tenant(id=1, nome="Padrão", ativo=True))
    db_session.commit()
    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SEED_SAAS_OPS_EMAIL", "ops@deskrudder.com.br")
    monkeypatch.setattr(settings, "SEED_SAAS_OPS_PASSWORD", "temporaria8")
    _ensure_saas_ops_producao(db_session)
    assert db_session.query(Atendente).filter(Atendente.email == "ops@deskrudder.com.br").first() is None
