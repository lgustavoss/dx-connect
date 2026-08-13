"""Filtros da listagem de licenças e plano na aprovação go-live."""

from __future__ import annotations

from datetime import date, timedelta


def test_listar_clientes_filtros(client, auth_headers, db_session, monkeypatch):
    from app.config import settings
    from app.models.saas_plano import SaasPlano

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_RENEWAL_ALERT_DAYS_BEFORE", 14)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]

    pro = SaasPlano(codigo="profissional", nome="Profissional", ativo=True, ordem=20)
    db_session.add(pro)
    db_session.commit()

    hoje = date.today()
    a = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Filtro A",
            "slug": "filtro-a",
            "status": "ativo",
            "data_inicio": str(hoje),
            "data_renovacao": str(hoje + timedelta(days=7)),
            "plano_id": pro.id,
        },
    )
    assert a.status_code == 201, a.text
    # Marcar aprovação pendente + fila
    from app.database import SessionLocal
    from app.models.cliente_saas import ClienteSaaS

    db = SessionLocal()
    try:
        row = db.query(ClienteSaaS).filter(ClienteSaaS.slug == "filtro-a").one()
        row.aprovacao_status = "pendente"
        row.provisionamento_status = "aguardando_ops"
        db.commit()
    finally:
        db.close()

    client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Filtro B",
            "slug": "filtro-b",
            "status": "ativo",
            "data_inicio": str(hoje),
            "data_renovacao": str(hoje - timedelta(days=2)),
        },
    )

    by_plano = client.get(f"/v1/saas/clientes?plano_id={pro.id}", headers=h)
    assert by_plano.status_code == 200
    assert by_plano.json()["total"] == 1
    assert by_plano.json()["items"][0]["slug"] == "filtro-a"

    by_aprov = client.get("/v1/saas/clientes?aprovacao_status=pendente", headers=h)
    assert by_aprov.status_code == 200
    assert any(i["slug"] == "filtro-a" for i in by_aprov.json()["items"])

    by_fila = client.get("/v1/saas/clientes?provisionamento_fila=true", headers=h)
    assert by_fila.status_code == 200
    assert any(i["slug"] == "filtro-a" for i in by_fila.json()["items"])

    vencendo = client.get("/v1/saas/clientes?vencendo=true", headers=h)
    assert vencendo.status_code == 200
    assert any(i["slug"] == "filtro-a" for i in vencendo.json()["items"])

    vencidas = client.get("/v1/saas/clientes?vencidas=true", headers=h)
    assert vencidas.status_code == 200
    assert any(i["slug"] == "filtro-b" for i in vencidas.json()["items"])


def test_aprovar_com_plano_id(client, auth_headers, db_session, monkeypatch):
    from app.config import settings
    from app.core import kb_public_rate_limit as rl
    from app.models.saas_plano import SaasPlano

    rl._trial_buckets.clear()
    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_TRIAL_DAYS", 14)
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]

    pro = SaasPlano(codigo="profissional", nome="Profissional", ativo=True, ordem=20)
    db_session.add(pro)
    db_session.commit()

    r = client.post(
        "/v1/saas/public/trial",
        json={
            "empresa": "Upgrade Soft",
            "slug": "upgrade-soft",
            "contato_nome": "Lia",
            "contato_email": "lia@upgrade.example",
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    ok = client.post(
        f"/v1/saas/clientes/{cid}/aprovar",
        headers=h,
        json={"ativar": True, "provisionar": True, "plano_id": pro.id},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["aprovacao_status"] == "aprovado"
    assert body["plano_id"] == pro.id
    assert body["plano"] == "Profissional"
