"""Pools Boleto Cloud e vínculos no painel SaaS Ops (#1392)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import httpx

from app.models.boleto_pool import BoletoPool, BoletoPoolVinculo
from app.models.cliente_saas import ClienteSaaS
from app.services import saas_boleto_cloud as svc
from app.services.secret_box import decrypt_str, encrypt_str


def test_boleto_cloud_404_sem_control_plane(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.get("/v1/saas/boleto-cloud/pools", headers=auth_headers["ops"])
    assert r.status_code == 404


def test_boleto_cloud_403_atendente(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/saas/boleto-cloud/pools", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_boleto_cloud_get_404_sem_cadastro(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/saas/boleto-cloud", headers=auth_headers["ops"])
    assert r.status_code == 404


def test_boleto_cloud_upsert_mascara_e_mantem_se_vazio(client, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["ops"]

    criado = client.put(
        "/v1/saas/boleto-cloud",
        headers=h,
        json={
            "apelido": "piloto-sandbox",
            "api_base_url": "https://sandbox.boletocloud.com/api/v1",
            "api_key": "api-key_secreta",
            "conta_token": "token_conta_secreto",
            "ativo": True,
        },
    )
    assert criado.status_code == 200, criado.text
    body = criado.json()
    assert body["apelido"] == "piloto-sandbox"
    assert body["tem_api_key"] is True
    assert body["tem_conta_token"] is True
    assert "api_key" not in body
    assert "conta_token" not in body
    assert "api_key_cifrada" not in body

    row = db_session.query(BoletoPool).one()
    assert decrypt_str(row.api_key_cifrada) == "api-key_secreta"
    assert decrypt_str(row.conta_token_cifrado) == "token_conta_secreto"

    manter = client.put(
        "/v1/saas/boleto-cloud",
        headers=h,
        json={
            "apelido": "piloto-renomeado",
            "api_base_url": "https://sandbox.boletocloud.com/api/v1",
            "ativo": True,
        },
    )
    assert manter.status_code == 200, manter.text
    assert manter.json()["apelido"] == "piloto-renomeado"
    assert manter.json()["tem_api_key"] is True
    db_session.refresh(row)
    assert decrypt_str(row.api_key_cifrada) == "api-key_secreta"

    get_r = client.get("/v1/saas/boleto-cloud", headers=h)
    assert get_r.status_code == 200
    assert get_r.json()["tem_api_key"] is True
    assert get_r.json()["tem_conta_token"] is True


def test_pool_crud_lista_e_testar(client, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["ops"]

    criado = client.post(
        "/v1/saas/boleto-cloud/pools",
        headers=h,
        json={
            "apelido": "pool-a",
            "api_base_url": "https://sandbox.boletocloud.com/api/v1",
            "api_key": "key-a",
            "faixa_teto": 1000,
            "ativo": True,
        },
    )
    assert criado.status_code == 201, criado.text
    pool_id = criado.json()["id"]
    assert criado.json()["tem_api_key"] is True
    assert criado.json()["clientes_vinculados"] == 0

    lista = client.get("/v1/saas/boleto-cloud/pools", headers=h)
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1
    assert any(p["id"] == pool_id for p in lista.json()["items"])

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp
    resultado = svc.testar_pool(db_session, pool_id, client=mock_http)
    assert resultado.ok is True
    args, kwargs = mock_http.get.call_args
    assert args[0].endswith("/boletos")
    assert "Authorization" in kwargs["headers"]


def test_vinculo_cliente_encerra_anterior(client, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["ops"]

    cli = ClienteSaaS(
        nome="Cliente Pool",
        slug="cliente-pool-test",
        status="ativo",
        aprovacao_status="aprovado",
        data_inicio=date.today(),
    )
    db_session.add(cli)
    db_session.commit()
    db_session.refresh(cli)

    p1 = client.post(
        "/v1/saas/boleto-cloud/pools",
        headers=h,
        json={
            "apelido": "origem",
            "api_base_url": "https://sandbox.boletocloud.com/api/v1",
            "api_key": "k1",
            "ativo": True,
        },
    ).json()
    p2 = client.post(
        "/v1/saas/boleto-cloud/pools",
        headers=h,
        json={
            "apelido": "destino",
            "api_base_url": "https://sandbox.boletocloud.com/api/v1",
            "api_key": "k2",
            "ativo": True,
        },
    ).json()

    v1 = client.post(
        f"/v1/saas/boleto-cloud/clientes/{cli.id}/vinculos",
        headers=h,
        json={"pool_id": p1["id"], "encerrar_anterior": True},
    )
    assert v1.status_code == 201, v1.text
    assert v1.json()["ativo_agora"] is True

    v2 = client.post(
        f"/v1/saas/boleto-cloud/clientes/{cli.id}/vinculos",
        headers=h,
        json={"pool_id": p2["id"], "encerrar_anterior": True},
    )
    assert v2.status_code == 201, v2.text
    assert v2.json()["pool_id"] == p2["id"]
    assert v2.json()["ativo_agora"] is True

    lista = client.get(f"/v1/saas/boleto-cloud/clientes/{cli.id}/vinculos", headers=h)
    assert lista.status_code == 200
    items = lista.json()["items"]
    assert len(items) == 2
    antigos = [x for x in items if x["pool_id"] == p1["id"]]
    assert antigos[0]["vigencia_ate"] is not None
    assert antigos[0]["ativo_agora"] is False

    # Migração: vínculo novo no destino; histórico do pool origem permanece.
    assert db_session.query(BoletoPoolVinculo).filter(BoletoPoolVinculo.pool_id == p1["id"]).count() == 1


def test_boleto_cloud_testar_sem_credencial_400(client, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    db_session.add(
        BoletoPool(
            apelido="vazio",
            api_base_url="https://sandbox.boletocloud.com/api/v1",
            ativo=True,
        )
    )
    db_session.commit()
    r = client.post("/v1/saas/boleto-cloud/testar", headers=auth_headers["ops"])
    assert r.status_code == 400


def test_boleto_cloud_testar_mock_ok(client, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    client.put(
        "/v1/saas/boleto-cloud",
        headers=auth_headers["ops"],
        json={
            "apelido": "piloto",
            "api_base_url": "https://sandbox.boletocloud.com/api/v1",
            "api_key": "k",
            "conta_token": "t",
            "ativo": True,
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp

    resultado = svc.testar_conexao(db_session, client=mock_http)
    assert resultado.ok is True
    assert resultado.http_status == 200
    mock_http.get.assert_called_once()
    args, kwargs = mock_http.get.call_args
    assert args[0].endswith("/boletos")
    assert "Authorization" in kwargs["headers"]


def test_boleto_cloud_testar_mock_401(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    db_session.add(
        BoletoPool(
            apelido="bad",
            api_base_url="https://sandbox.boletocloud.com/api/v1",
            api_key_cifrada=encrypt_str("k"),
            conta_token_cifrado=encrypt_str("t"),
            ativo=True,
        )
    )
    db_session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp
    resultado = svc.testar_conexao(db_session, client=mock_http)
    assert resultado.ok is False
    assert resultado.http_status == 401


def test_boleto_cloud_testar_rede_falhou(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    db_session.add(
        BoletoPool(
            apelido="net",
            api_base_url="https://sandbox.boletocloud.com/api/v1",
            api_key_cifrada=encrypt_str("k"),
            conta_token_cifrado=encrypt_str("t"),
            ativo=True,
        )
    )
    db_session.commit()

    mock_http = MagicMock()
    mock_http.get.side_effect = httpx.ConnectError("offline")
    resultado = svc.testar_conexao(db_session, client=mock_http)
    assert resultado.ok is False
    assert resultado.http_status is None
