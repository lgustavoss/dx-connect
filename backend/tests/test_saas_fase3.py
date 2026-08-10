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
    assert d.get("comandos_ops")
    assert "provision-client.sh --slug acme-suporte" in d["comandos_ops"]
    assert "stack-client.sh migrate acme-suporte" in d["comandos_ops"]
    assert "stack-client.sh health acme-suporte" in d["comandos_ops"]

    conf = client.post(f"/v1/saas/clientes/{cid}/confirmar-provisionamento", headers=h, json={})
    assert conf.status_code == 200, conf.text
    cbody = conf.json()
    assert cbody["provisionamento_status"] == "sucesso"
    assert cbody.get("comandos_ops") in (None, "")
    assert "confirmado" in (cbody["provisionamento_mensagem"] or "").lower()

    # Confirmar de novo (já sucesso) deve falhar
    conf2 = client.post(f"/v1/saas/clientes/{cid}/confirmar-provisionamento", headers=h, json={})
    assert conf2.status_code == 400


def test_confirmar_provisionamento_rejeita_pendente(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]

    criar = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Gamma",
            "slug": "gamma-ops",
            "status": "trial",
            "data_inicio": str(date.today()),
        },
    )
    assert criar.status_code == 201, criar.text
    cid = criar.json()["id"]

    r = client.post(f"/v1/saas/clientes/{cid}/solicitar-provisionamento", headers=h)
    assert r.status_code == 200
    assert r.json()["provisionamento_status"] == "pendente"

    conf = client.post(f"/v1/saas/clientes/{cid}/confirmar-provisionamento", headers=h, json={})
    assert conf.status_code == 400


def test_provisionar_exec_mock_sucesso_e_falha(client, auth_headers, monkeypatch, tmp_path):
    from app.config import settings
    from app.database import SessionLocal
    from app.services import saas_provisionamento as prov

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    monkeypatch.setattr(settings, "SAAS_REPO_ROOT", str(tmp_path))

    scripts = tmp_path / "deploy" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "provision-client.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (scripts / "stack-client.sh").write_text("#!/bin/bash\n", encoding="utf-8")

    calls: list[list[str]] = []

    class _Result:
        def __init__(self, returncode: int = 0, stderr: str = "", stdout: str = ""):
            self.returncode = returncode
            self.stderr = stderr
            self.stdout = stdout

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return _Result(0)

    monkeypatch.setattr(prov.subprocess, "run", fake_run)

    h = auth_headers["ops"]
    criar = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Delta",
            "slug": "delta-exec",
            "status": "trial",
            "data_inicio": str(date.today()),
        },
    )
    assert criar.status_code == 201, criar.text
    cid = criar.json()["id"]

    assert client.post(f"/v1/saas/clientes/{cid}/solicitar-provisionamento", headers=h).status_code == 200

    db = SessionLocal()
    try:
        n = prov.processar_provisionamentos_pendentes(db, limit=5)
        db.commit()
    finally:
        db.close()
    assert n >= 1

    detalhe = client.get(f"/v1/saas/clientes/{cid}", headers=h)
    assert detalhe.status_code == 200
    assert detalhe.json()["provisionamento_status"] == "sucesso"

    # provision-client + migrate/up/health com ordem <cmd> <slug>
    assert any("provision-client.sh" in " ".join(c) for c in calls)
    stack_calls = [c for c in calls if any("stack-client.sh" in part for part in c)]
    assert len(stack_calls) == 3
    assert [c[-2] for c in stack_calls] == ["migrate", "up", "health"]
    assert all(c[-1] == "delta-exec" for c in stack_calls)

    # Segunda licença: falha no migrate
    calls.clear()

    def fail_on_migrate(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        if any(part == "migrate" for part in cmd):
            return _Result(1, stderr="boom migrate")
        return _Result(0)

    monkeypatch.setattr(prov.subprocess, "run", fail_on_migrate)

    criar2 = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Epsilon",
            "slug": "epsilon-fail",
            "status": "trial",
            "data_inicio": str(date.today()),
        },
    )
    assert criar2.status_code == 201, criar2.text
    cid2 = criar2.json()["id"]
    assert client.post(f"/v1/saas/clientes/{cid2}/solicitar-provisionamento", headers=h).status_code == 200

    db = SessionLocal()
    try:
        prov.processar_provisionamentos_pendentes(db, limit=5)
        db.commit()
    finally:
        db.close()

    d2 = client.get(f"/v1/saas/clientes/{cid2}", headers=h).json()
    assert d2["provisionamento_status"] == "falha"
    assert "migrate" in (d2["provisionamento_mensagem"] or "").lower()
    assert d2.get("comandos_ops")


def test_trial_publico_cria_licenca(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_TRIAL_DAYS", 10)
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")

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
    assert "fila" in body["mensagem"].lower() or "provisionamento" in body["mensagem"].lower()

    lista = client.get("/v1/saas/clientes?busca=beta", headers=auth_headers["ops"])
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1
    item = next(i for i in lista.json()["items"] if i["slug"] == "beta-soft")
    assert item["contato_email"] == "ana@beta.example"
    assert item["provisionamento_solicitado"] is True
    assert item["provisionamento_status"] == "pendente"
    assert item["aprovacao_status"] == "pendente"
    assert item["api_port"] is not None


def test_aprovar_go_live_e_rejeitar_trial(client, auth_headers, monkeypatch):
    from app.config import settings
    from app.core import kb_public_rate_limit as rl

    rl._trial_buckets.clear()
    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_TRIAL_DAYS", 14)
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]

    r = client.post(
        "/v1/saas/public/trial",
        json={
            "empresa": "Aprova Soft",
            "slug": "aprova-soft",
            "contato_nome": "Lia",
            "contato_email": "lia@aprova.example",
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    resumo = client.get("/v1/saas/resumo", headers=h)
    assert resumo.status_code == 200
    assert resumo.json()["aprovacoes_pendentes"] >= 1

    ok = client.post(f"/v1/saas/clientes/{cid}/aprovar", headers=h, json={"ativar": True})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["aprovacao_status"] == "aprovado"
    assert body["status"] == "ativo"

    # Já aprovada + ativa → erro
    again = client.post(f"/v1/saas/clientes/{cid}/aprovar", headers=h, json={})
    assert again.status_code == 400

    # Novo trial para rejeitar
    r2 = client.post(
        "/v1/saas/public/trial",
        json={
            "empresa": "Rejeita Soft",
            "slug": "rejeita-soft",
            "contato_nome": "Bob",
            "contato_email": "bob@rejeita.example",
        },
    )
    cid2 = r2.json()["id"]
    rej = client.post(
        f"/v1/saas/clientes/{cid2}/rejeitar",
        headers=h,
        json={"notas": "Fora do ICP"},
    )
    assert rej.status_code == 200, rej.text
    b2 = rej.json()
    assert b2["aprovacao_status"] == "rejeitado"
    assert b2["status"] == "churn"
    assert b2["aprovacao_notas"] == "Fora do ICP"
    assert b2["provisionamento_status"] == "falha"


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


def test_trial_enfileira_mesmo_sem_flag_legado(client, auth_headers, monkeypatch):
    """solicitar_provisionamento=false no body é ignorado — sempre enfileira."""
    from app.config import settings
    from app.core import kb_public_rate_limit as rl

    rl._trial_buckets.clear()
    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_TRIAL_DAYS", 14)
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")

    r = client.post(
        "/v1/saas/public/trial",
        json={
            "empresa": "Prov Soft",
            "slug": "prov-soft",
            "contato_nome": "Joao",
            "contato_email": "joao@prov.example",
            "solicitar_provisionamento": False,
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


def test_suspender_reativar_stack_ops_assisted(client, auth_headers, monkeypatch):
    from app.config import settings
    from app.database import SessionLocal
    from app.services.saas_provisionamento import processar_provisionamentos_pendentes

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)
    h = auth_headers["ops"]

    cid = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Stack Co",
            "slug": "stack-co",
            "status": "ativo",
            "data_inicio": str(date.today()),
        },
    ).json()["id"]

    assert client.post(f"/v1/saas/clientes/{cid}/solicitar-provisionamento", headers=h).status_code == 200
    db = SessionLocal()
    try:
        processar_provisionamentos_pendentes(db, limit=5)
        db.commit()
    finally:
        db.close()

    conf = client.post(f"/v1/saas/clientes/{cid}/confirmar-provisionamento", headers=h, json={})
    assert conf.status_code == 200, conf.text
    assert conf.json()["stack_status"] == "running"

    susp = client.post(f"/v1/saas/clientes/{cid}/suspender", headers=h)
    assert susp.status_code == 200, susp.text
    s = susp.json()
    assert s["status"] == "suspenso"
    assert s["stack_ops_pendente"] == "down"
    assert s["comandos_stack"] and "stack-client.sh down" in s["comandos_stack"]

    conf_down = client.post(f"/v1/saas/clientes/{cid}/confirmar-stack", headers=h)
    assert conf_down.status_code == 200
    assert conf_down.json()["stack_status"] == "stopped"
    assert conf_down.json()["stack_ops_pendente"] is None

    reat = client.post(f"/v1/saas/clientes/{cid}/reativar", headers=h)
    assert reat.status_code == 200
    r = reat.json()
    assert r["status"] == "ativo"
    assert r["stack_ops_pendente"] == "up"
    assert r["comandos_stack"] and "stack-client.sh up" in r["comandos_stack"]

    conf_up = client.post(f"/v1/saas/clientes/{cid}/confirmar-stack", headers=h)
    assert conf_up.status_code == 200
    assert conf_up.json()["stack_status"] == "running"


def test_entrega_pos_health_notifica_contacto(client, auth_headers, monkeypatch):
    from app.config import settings
    from app.database import SessionLocal
    from app.services.saas_provisionamento import processar_provisionamentos_pendentes

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_EXEC_ENABLED", False)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", "ops@deskrudder.local")

    sent: list[tuple[str, str]] = []

    def fake_enviar(db, *, to_addr, subject, body):
        sent.append((to_addr, subject))

    monkeypatch.setattr(
        "app.services.saas_notify.enviar_mensagem_texto_sistema",
        fake_enviar,
    )

    h = auth_headers["ops"]
    cid = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Entrega Co",
            "slug": "entrega-co",
            "status": "ativo",
            "data_inicio": str(date.today()),
            "contato_email": "cliente@entrega.example",
            "contato_nome": "Ana",
        },
    ).json()["id"]

    assert client.post(f"/v1/saas/clientes/{cid}/solicitar-provisionamento", headers=h).status_code == 200
    db = SessionLocal()
    try:
        processar_provisionamentos_pendentes(db, limit=5)
        db.commit()
    finally:
        db.close()

    conf = client.post(f"/v1/saas/clientes/{cid}/confirmar-provisionamento", headers=h, json={})
    assert conf.status_code == 200, conf.text
    assert conf.json()["entrega_notificada_em"] is not None
    assert any(addr == "cliente@entrega.example" and "ambiente pronto" in subj.lower() for addr, subj in sent)

    reenv = client.post(f"/v1/saas/clientes/{cid}/reenviar-entrega", headers=h)
    assert reenv.status_code == 200
    assert sum(1 for a, _ in sent if a == "cliente@entrega.example") >= 2


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
