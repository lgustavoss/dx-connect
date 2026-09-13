"""Alertas operacionais SaaS Ops por instância (#1036)."""

from __future__ import annotations

from datetime import date

from app.models.cliente_saas import ClienteSaaS
from app.services import saas_alertas_ops as svc


def _criar_cliente(client, headers, slug: str = "cliente-alertas") -> dict:
    r = client.post(
        "/v1/saas/clientes",
        headers=headers,
        json={
            "nome": "Cliente Alertas",
            "slug": slug,
            "status": "ativo",
            "plano": "profissional",
            "data_inicio": str(date.today()),
            "data_renovacao": str(date.today()),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_alertas_rbac(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    assert client.get("/v1/saas/alertas/resumo", headers=auth_headers["admin"]).status_code == 403
    assert client.get("/v1/saas/alertas?cliente_saas_id=1", headers=auth_headers["a1"]).status_code == 403
    assert client.get("/v1/saas/alertas/resumo", headers=auth_headers["ops"]).status_code == 200


def test_alertas_control_plane_off_404(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    assert client.get("/v1/saas/alertas?cliente_saas_id=1", headers=auth_headers["ops"]).status_code == 404


def test_alertas_lista_exige_cliente(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/saas/alertas", headers=auth_headers["ops"])
    assert r.status_code == 422


def test_motor_stack_e_api_resumo_mitigar(client, auth_headers, monkeypatch, db_session):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_ALERTAS_OPS_PROBE_FALHAS", 1)
    monkeypatch.setattr(
        svc,
        "_http_get",
        lambda url, timeout: (None, None, "connection refused"),
    )
    h = auth_headers["ops"]
    body = _criar_cliente(client, h, slug="ops-alerta-1")
    cid = body["id"]

    row = db_session.query(ClienteSaaS).filter(ClienteSaaS.id == cid).one()
    row.stack_status = "stopped"
    row.provisionamento_status = "sucesso"
    row.api_port = 19999
    db_session.commit()

    n = svc.processar_alertas_ops(db_session, limit=50)
    db_session.commit()
    assert n >= 1

    resumo = client.get("/v1/saas/alertas/resumo", headers=h)
    assert resumo.status_code == 200, resumo.text
    data = resumo.json()
    assert data["alertas_ativos"] >= 1
    assert data["instancias_afetadas"] >= 1

    lista = client.get(f"/v1/saas/alertas?estado=ativo&cliente_saas_id={cid}", headers=h)
    assert lista.status_code == 200
    items = lista.json()["items"]
    assert any(i["cliente_saas_id"] == cid for i in items)
    assert any(i["codigo_sinal"] == "stack_parada" for i in items)

    alerta_stack = next(i for i in items if i["codigo_sinal"] == "stack_parada")
    detalhe = client.get(f"/v1/saas/alertas/{alerta_stack['id']}", headers=h)
    assert detalhe.status_code == 200
    assert detalhe.json()["eventos"]
    assert detalhe.json()["eventos"][0]["tipo"] == "aberto"

    mit = client.post(
        f"/v1/saas/alertas/{alerta_stack['id']}/mitigar",
        headers=h,
        json={"mensagem": "Manutenção planejada"},
    )
    assert mit.status_code == 200, mit.text
    assert mit.json()["estado"] == "mitigado"

    row = db_session.query(ClienteSaaS).filter(ClienteSaaS.id == cid).one()
    row.stack_status = "running"
    db_session.commit()
    svc.processar_alertas_ops(db_session, limit=50)
    db_session.commit()

    por_cliente = client.get(f"/v1/saas/alertas/cliente/{cid}", headers=h)
    assert por_cliente.status_code == 200
    estados = {i["codigo_sinal"]: i["estado"] for i in por_cliente.json()["items"]}
    assert estados.get("stack_parada") == "resolvido"


def test_dedup_nao_reabre_ciclo_aberto(client, auth_headers, monkeypatch, db_session):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(svc, "_http_get", lambda url, timeout: (200, {"status": "ok"}, None))
    h = auth_headers["ops"]
    body = _criar_cliente(client, h, slug="ops-alerta-dedup")
    cid = body["id"]
    row = db_session.query(ClienteSaaS).filter(ClienteSaaS.id == cid).one()
    row.stack_status = "stopped"
    row.provisionamento_status = "sucesso"
    db_session.commit()

    svc.processar_alertas_ops(db_session)
    db_session.commit()
    svc.processar_alertas_ops(db_session)
    db_session.commit()

    lista = client.get(f"/v1/saas/alertas?cliente_saas_id={cid}", headers=h)
    stacks = [i for i in lista.json()["items"] if i["codigo_sinal"] == "stack_parada"]
    assert len(stacks) == 1
    assert stacks[0]["ciclo_id"] == 1
