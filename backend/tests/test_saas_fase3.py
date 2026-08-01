"""Provisionamento, trial e renovações SaaS (#524 / #527 / #528)."""

from __future__ import annotations

from datetime import date, timedelta


def test_provisionar_enfileira_sem_exec(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]

    criar = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Acme",
            "slug": "acme-suporte",
            "status": "trial",
            "data_inicio": str(date.today()),
        },
    )
    assert criar.status_code == 201, criar.text
    cid = criar.json()["id"]

    r = client.post(f"/v1/saas/clientes/{cid}/solicitar-provisionamento", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provisionamento_solicitado"] is True
    assert body["provisionamento_status"] == "pendente"
    assert body["api_port"] is not None

    from app.database import SessionLocal
    from app.services.saas_provisionamento import processar_provisionamentos_pendentes

    db = SessionLocal()
    try:
        n = processar_provisionamentos_pendentes(db, limit=5)
        db.commit()
    finally:
        db.close()
    assert n >= 1

    detalhe = client.get(f"/v1/saas/clientes/{cid}", headers=h)
    assert detalhe.status_code == 200
    d = detalhe.json()
    assert d["provisionamento_status"] == "aguardando_ops"
    assert "Execução automática desligada" in (d["provisionamento_mensagem"] or "")
    assert d["instancia_url"] and "acme-suporte.deskrudder.com.br" in d["instancia_url"]


def test_trial_publico_cria_licenca(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_TRIAL_DAYS", 10)
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)

    r = client.post(
        "/v1/saas/public/trial",
        json={
            "empresa": "Beta Soft",
            "slug": "beta-soft",
            "contato_nome": "Ana",
            "contato_email": "ana@beta.example",
            "notas": "Quero testar 2 semanas",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "beta-soft"
    assert body["status"] == "trial"
    assert body["data_renovacao"] == str(date.today() + timedelta(days=10))

    lista = client.get("/v1/saas/clientes?busca=beta", headers=auth_headers["ops"])
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1
    item = next(i for i in lista.json()["items"] if i["slug"] == "beta-soft")
    assert item["contato_email"] == "ana@beta.example"


def test_trial_publico_slug_duplicado(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    payload = {
        "empresa": "A",
        "slug": "dup-trial",
        "contato_nome": "X",
        "contato_email": "x@ex.com",
    }
    assert client.post("/v1/saas/public/trial", json=payload).status_code == 201
    r = client.post("/v1/saas/public/trial", json={**payload, "empresa": "B"})
    assert r.status_code == 409


def test_trial_desligado_404(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.post(
        "/v1/saas/public/trial",
        json={
            "empresa": "Z",
            "slug": "z-trial",
            "contato_nome": "Z",
            "contato_email": "z@ex.com",
        },
    )
    assert r.status_code == 404


def test_renovar_estende_data_e_reativa(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["ops"]
    criar = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Gama",
            "slug": "gama",
            "status": "suspenso",
            "data_inicio": str(date.today() - timedelta(days=40)),
            "data_renovacao": str(date.today() - timedelta(days=5)),
        },
    )
    cid = criar.json()["id"]
    r = client.post(f"/v1/saas/clientes/{cid}/renovar", headers=h, json={"dias": 30})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ativo"
    assert body["data_renovacao"] == str(date.today() + timedelta(days=30))
    assert body["dias_para_renovacao"] == 30


def test_renovar_com_nova_data(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["ops"]
    criar = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Delta",
            "slug": "delta-co",
            "status": "ativo",
            "data_inicio": str(date.today()),
            "data_renovacao": str(date.today() + timedelta(days=2)),
        },
    )
    cid = criar.json()["id"]
    nova = date.today() + timedelta(days=90)
    r = client.post(
        f"/v1/saas/clientes/{cid}/renovar",
        headers=h,
        json={"nova_data": str(nova)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data_renovacao"] == str(nova)
    assert r.json()["dias_para_renovacao"] == 90


def test_trial_com_provisionamento(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_TRIAL_DAYS", 14)
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)

    r = client.post(
        "/v1/saas/public/trial",
        json={
            "empresa": "Prov Soft",
            "slug": "prov-soft",
            "contato_nome": "Joao",
            "contato_email": "joao@prov.example",
            "solicitar_provisionamento": True,
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    detalhe = client.get(f"/v1/saas/clientes/{cid}", headers=auth_headers["ops"])
    assert detalhe.status_code == 200
    d = detalhe.json()
    assert d["provisionamento_solicitado"] is True
    assert d["provisionamento_status"] == "pendente"
    assert d["contato_email"] == "joao@prov.example"


def test_worker_renovacao_suspende_vencido(client, auth_headers, monkeypatch):
    from app.config import settings
    from app.database import SessionLocal
    from app.services.saas_renovacoes import processar_renovacoes

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_RENEWAL_ALERT_DAYS_BEFORE", 7)
    h = auth_headers["ops"]

    vencido = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Vencido",
            "slug": "vencido-co",
            "status": "ativo",
            "data_inicio": str(date.today() - timedelta(days=60)),
            "data_renovacao": str(date.today() - timedelta(days=1)),
        },
    ).json()["id"]

    risco = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Risco",
            "slug": "risco-co",
            "status": "ativo",
            "data_inicio": str(date.today()),
            "data_renovacao": str(date.today() + timedelta(days=3)),
        },
    ).json()["id"]

    db = SessionLocal()
    try:
        n = processar_renovacoes(db, limit=50)
        db.commit()
    finally:
        db.close()
    assert n >= 2

    assert client.get(f"/v1/saas/clientes/{vencido}", headers=h).json()["status"] == "suspenso"
    assert client.get(f"/v1/saas/clientes/{risco}", headers=h).json()["status"] == "ativo"

    # Segunda passagem não reemite (dedup)
    db = SessionLocal()
    try:
        n2 = processar_renovacoes(db, limit=50)
        db.commit()
    finally:
        db.close()
    assert n2 == 0
