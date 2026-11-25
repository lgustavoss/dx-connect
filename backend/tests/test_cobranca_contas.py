"""Contas bancárias de cobrança na instância (#1392)."""

from __future__ import annotations

from app.models.boleto_pool import CobrancaContaBancaria
from app.services.secret_box import decrypt_str


def test_contas_403_sem_permissao(client, auth_headers):
    r = client.get("/v1/cobranca/contas-bancarias", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_contas_crud_mascara_token(client, auth_headers, db_session):
    h = auth_headers["admin"]

    criado = client.post(
        "/v1/cobranca/contas-bancarias",
        headers=h,
        json={
            "apelido": "Conta principal",
            "banco_codigo": "001",
            "banco_nome": "Banco do Brasil",
            "agencia": "1234",
            "conta": "56789",
            "conta_dv": "0",
            "padrao": True,
            "boleto_cloud_token": "token-secreto",
        },
    )
    assert criado.status_code == 201, criado.text
    body = criado.json()
    assert body["apelido"] == "Conta principal"
    assert body["tem_token"] is True
    assert body["padrao"] is True
    assert "boleto_cloud_token" not in body
    assert "boleto_cloud_token_cifrado" not in body

    row = db_session.query(CobrancaContaBancaria).one()
    assert decrypt_str(row.boleto_cloud_token_cifrado) == "token-secreto"

    # Segunda conta padrão desaloca a primeira.
    outra = client.post(
        "/v1/cobranca/contas-bancarias",
        headers=h,
        json={
            "apelido": "Conta B",
            "padrao": True,
            "boleto_cloud_token": "outro",
        },
    )
    assert outra.status_code == 201, outra.text
    db_session.refresh(row)
    assert row.padrao is False

    manter = client.put(
        f"/v1/cobranca/contas-bancarias/{row.id}",
        headers=h,
        json={
            "apelido": "Conta principal renomeada",
            "banco_codigo": "001",
            "ativo": True,
            "padrao": False,
        },
    )
    assert manter.status_code == 200, manter.text
    assert manter.json()["apelido"] == "Conta principal renomeada"
    assert manter.json()["tem_token"] is True
    db_session.refresh(row)
    assert decrypt_str(row.boleto_cloud_token_cifrado) == "token-secreto"

    des = client.post(
        f"/v1/cobranca/contas-bancarias/{outra.json()['id']}/desativar",
        headers=h,
    )
    assert des.status_code == 200
    assert des.json()["ativo"] is False
    assert des.json()["padrao"] is False

    lista = client.get("/v1/cobranca/contas-bancarias", headers=h)
    assert lista.status_code == 200
    assert lista.json()["total"] == 2
