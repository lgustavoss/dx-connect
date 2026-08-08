"""Testes do catálogo comercial de custos (#321 / #329–#333)."""

from __future__ import annotations

from decimal import Decimal


def test_sm_crud_e_na_data(client, auth_headers):
    h = auth_headers["admin"]
    r = client.post(
        "/v1/comercial/salario-minimo",
        headers=h,
        json={"valor": "1412.00", "vigencia_inicio": "2024-01-01", "vigencia_fim": "2024-12-31"},
    )
    assert r.status_code == 201, r.text
    sm1 = r.json()
    assert Decimal(sm1["valor"]) == Decimal("1412.00")

    r2 = client.post(
        "/v1/comercial/salario-minimo",
        headers=h,
        json={"valor": "1518.00", "vigencia_inicio": "2025-01-01", "vigencia_fim": None},
    )
    assert r2.status_code == 201, r2.text

    # Sobreposição rejeitada
    r_dup = client.post(
        "/v1/comercial/salario-minimo",
        headers=h,
        json={"valor": "1500.00", "vigencia_inicio": "2024-06-01", "vigencia_fim": "2024-08-01"},
    )
    assert r_dup.status_code == 400
    assert "sobrepõe" in r_dup.json()["detail"].lower() or "sobrepoe" in r_dup.json()["detail"].lower()

    na = client.get("/v1/comercial/salario-minimo/na-data", headers=h, params={"data": "2024-07-15"})
    assert na.status_code == 200
    assert na.json()["id"] == sm1["id"]

    na2 = client.get("/v1/comercial/salario-minimo/na-data", headers=h, params={"data": "2025-03-01"})
    assert na2.status_code == 200
    assert Decimal(na2.json()["valor"]) == Decimal("1518.00")

    lst = client.get("/v1/comercial/salario-minimo", headers=h)
    assert lst.status_code == 200
    assert lst.json()["total"] == 2


def test_sm_atualizar_valor_preserva_passado(client, auth_headers):
    h = auth_headers["admin"]
    r0 = client.post(
        "/v1/comercial/salario-minimo/atualizar-valor",
        headers=h,
        json={"valor": "1412.00", "vigencia_inicio": "2024-01-01"},
    )
    assert r0.status_code == 201, r0.text
    assert r0.json()["vigencia_fim"] is None

    r1 = client.post(
        "/v1/comercial/salario-minimo/atualizar-valor",
        headers=h,
        json={"valor": "1518.00", "vigencia_inicio": "2025-01-01"},
    )
    assert r1.status_code == 201, r1.text
    assert Decimal(r1.json()["valor"]) == Decimal("1518.00")
    assert r1.json()["vigencia_inicio"] == "2025-01-01"
    assert r1.json()["vigencia_fim"] is None

    # Passado intacto
    ant = client.get("/v1/comercial/salario-minimo/na-data", headers=h, params={"data": "2024-06-01"})
    assert ant.status_code == 200
    assert Decimal(ant.json()["valor"]) == Decimal("1412.00")
    assert ant.json()["vigencia_fim"] == "2024-12-31"

    # Presente usa novo
    hoje = client.get("/v1/comercial/salario-minimo/na-data", headers=h, params={"data": "2025-06-01"})
    assert Decimal(hoje.json()["valor"]) == Decimal("1518.00")

    # Não permite data <= início do vigente
    bad = client.post(
        "/v1/comercial/salario-minimo/atualizar-valor",
        headers=h,
        json={"valor": "1600.00", "vigencia_inicio": "2025-01-01"},
    )
    assert bad.status_code == 400


def test_sm_somente_admin(client, auth_headers):
    r = client.get("/v1/comercial/salario-minimo", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_item_crud_e_simular(client, auth_headers):
    h = auth_headers["admin"]
    client.post(
        "/v1/comercial/salario-minimo",
        headers=h,
        json={"valor": "1000.00", "vigencia_inicio": "2020-01-01", "vigencia_fim": None},
    )

    pct = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={
            "nome": "Posto bandeira branca",
            "slug": "posto-bb",
            "tipo": "percentual_sm",
            "percentual_sm": "20",
            "ordem": 1,
        },
    )
    assert pct.status_code == 201, pct.text
    item_pct = pct.json()

    fixo = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={
            "nome": "Módulo fiscal",
            "slug": "mod-fiscal",
            "tipo": "valor_fixo",
            "valor_fixo": "50.00",
            "ordem": 2,
        },
    )
    assert fixo.status_code == 201, fixo.text
    item_fixo = fixo.json()

    tef = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={
            "nome": "TEF",
            "slug": "tef",
            "tipo": "composto_tef",
            "tef_base": "100.00",
            "tef_adicional": "30.00",
            "ordem": 3,
        },
    )
    assert tef.status_code == 201, tef.text
    item_tef = tef.json()

    # slug duplicado
    dup = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={"nome": "X", "slug": "posto-bb", "tipo": "valor_fixo", "valor_fixo": "1"},
    )
    assert dup.status_code == 400

    sim = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={
            "item_ids": [item_pct["id"], item_fixo["id"], item_tef["id"]],
            "quantidade_pdvs": 3,
            "data_referencia": "2025-06-01",
        },
    )
    assert sim.status_code == 200, sim.text
    body = sim.json()
    # 20% de 1000 = 200; fixo 50; TEF 100 + 2*30 = 160 → total 410
    assert Decimal(body["total"]) == Decimal("410.00")
    assert Decimal(body["salario_minimo"]) == Decimal("1000.00")
    assert len(body["linhas"]) == 3

    patch = client.patch(
        f"/v1/comercial/custos/itens/{item_fixo['id']}",
        headers=h,
        json={"ativo": False},
    )
    assert patch.status_code == 200
    assert patch.json()["ativo"] is False

    # item inativo não entra na simulação
    sim2 = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={"item_ids": [item_fixo["id"]], "quantidade_pdvs": 1},
    )
    assert sim2.status_code == 400


def test_item_exige_campos_por_tipo(client, auth_headers):
    h = auth_headers["admin"]
    r = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={"nome": "Sem %", "slug": "sem-pct", "tipo": "percentual_sm"},
    )
    assert r.status_code == 422
