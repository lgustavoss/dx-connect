"""Canal de contacto B2B na landing (DR-06 / #516)."""

from __future__ import annotations


def test_contato_publico_cria_lead(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_NOTIFY_EMAIL", None)

    r = client.post(
        "/v1/saas/public/contato",
        json={
            "nome": "Maria Prospect",
            "email": "maria@empresa.example",
            "empresa": "Empresa XYZ",
            "mensagem": "Quero uma demonstração do DeskRudder.",
        },
    )
    assert r.status_code == 201, r.text
    assert "recebida" in r.json()["mensagem"].lower()

    lista = client.get("/v1/saas/leads", headers=auth_headers["ops"])
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1
    lead = next(i for i in lista.json()["items"] if i["email"] == "maria@empresa.example")
    assert lead["status"] == "novo"
    assert lead["empresa"] == "Empresa XYZ"

    patch = client.patch(
        f"/v1/saas/leads/{lead['id']}",
        headers=auth_headers["ops"],
        json={"status": "em_atendimento", "notas_internas": "Ligação agendada"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "em_atendimento"


def test_contato_nao_usa_kb(client, monkeypatch):
    """Garante endpoint próprio — não /kb/public/chat."""
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.post(
        "/v1/saas/public/contato",
        json={
            "nome": "João",
            "email": "joao@ex.com",
            "mensagem": "Olá",
        },
    )
    assert r.status_code == 201
    assert "/kb/" not in r.url.path


def test_contato_desligado_404(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.post(
        "/v1/saas/public/contato",
        json={"nome": "X", "email": "x@ex.com", "mensagem": "oi"},
    )
    assert r.status_code == 404


def test_leads_atendente_403(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/saas/leads", headers=auth_headers["a1"])
    assert r.status_code == 403
