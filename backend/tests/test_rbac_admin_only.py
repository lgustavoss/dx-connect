"""Rotas de cadastro / auditoria: apenas admin (403 para atendente)."""

from __future__ import annotations


def test_atendente_403_redes(client, auth_headers):
    r = client.get("/v1/redes", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_403_redes_post(client, auth_headers):
    r = client.post(
        "/v1/redes",
        headers=auth_headers["a1"],
        json={"nome": "X", "ativo": True},
    )
    assert r.status_code == 403


def test_atendente_403_audit(client, auth_headers):
    r = client.get("/v1/audit", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_403_atendentes_lista(client, auth_headers):
    r = client.get("/v1/atendentes", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_403_funcionarios_rede(client, auth_headers):
    r = client.get("/v1/funcionarios-rede", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_403_empresa_detalhe(client, seed_base, auth_headers):
    r = client.get(f"/v1/empresas/{seed_base['empresa'].id}", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_403_empresa_patch(client, seed_base, auth_headers):
    r = client.patch(
        f"/v1/empresas/{seed_base['empresa'].id}",
        headers=auth_headers["a1"],
        json={"nome": "Hackeado"},
    )
    assert r.status_code == 403


def test_atendente_403_setor_detalhe(client, seed_base, auth_headers):
    r = client.get(f"/v1/setores/{seed_base['setor1'].id}", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_403_status_ticket_detalhe(client, seed_base, auth_headers):
    r = client.get(f"/v1/status-ticket/{seed_base['status'].id}", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_403_cadastro_aux_sincronizar_municipios(client, auth_headers):
    r = client.post("/v1/cadastro-aux/municipios/sincronizar", headers=auth_headers["a1"])
    assert r.status_code == 403
