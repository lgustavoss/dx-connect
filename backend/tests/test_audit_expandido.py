"""Auditoria expandida (#290–#292)."""

from __future__ import annotations

from app.core.audit import registrar_audit, registrar_audit_v2, sanitize_payload
from app.models import AuditLog


def _criar_ticket(client, auth_headers, seed_base, **extra):
    body = {
        "empresa_id": seed_base["empresa"].id,
        "setor_id": seed_base["setor1"].id,
        "assunto": "Teste auditoria",
        "descricao": "Corpo",
        **extra,
    }
    r = client.post("/v1/tickets", headers=auth_headers["admin"], json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_sanitize_payload_redact_secrets():
    out = sanitize_payload({"campo": "ok", "senha": "123", "nested": {"api_key": "x"}})
    assert out["campo"] == "ok"
    assert out["senha"] == "[redacted]"
    assert out["nested"]["api_key"] == "[redacted]"


def test_ticket_assign_gera_audit(client, auth_headers, seed_base, db_session):
    t = _criar_ticket(client, auth_headers, seed_base)
    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )
    assert r.status_code == 200, r.text
    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "ticket", AuditLog.entity_id == t["id"], AuditLog.action == "assign")
        .first()
    )
    assert row is not None
    assert row.payload_json is not None
    assert row.payload_json.get("para_atendente_id") == seed_base["a1"].id


def test_audit_filtro_action_e_csv(client, auth_headers, seed_base, db_session):
    t = _criar_ticket(client, auth_headers, seed_base)
    registrar_audit(
        db_session,
        "ticket",
        t["id"],
        "status_change",
        seed_base["admin"].id,
        payload={"de_status_id": 1, "para_status_id": 2},
    )
    db_session.commit()

    r = client.get("/v1/audit", headers=auth_headers["admin"], params={"action": "status_change"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert all(item["action"] == "status_change" for item in data["items"])

    r_csv = client.get(
        "/v1/audit",
        headers={**auth_headers["admin"], "Accept": "text/csv"},
        params={"format": "csv", "action": "status_change"},
    )
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers.get("content-type", "")
    assert "status_change" in r_csv.text


def test_audit_campos_expandidos_na_api(client, auth_headers, db_session):
    registrar_audit_v2(
        db_session,
        "settings",
        1,
        "update",
        None,
        payload={"chave": "valor"},
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id="req-test-1",
    )
    db_session.commit()

    r = client.get("/v1/audit", headers=auth_headers["admin"], params={"busca": "req-test-1"})
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["ip_address"] == "127.0.0.1"
    assert item["request_id"] == "req-test-1"
    assert item["payload_json"] == {"chave": "valor"}
