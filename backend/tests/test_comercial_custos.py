"""Testes do catálogo comercial de custos (#321 / #329–#335)."""

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

    ant = client.get("/v1/comercial/salario-minimo/na-data", headers=h, params={"data": "2024-06-01"})
    assert ant.status_code == 200
    assert Decimal(ant.json()["valor"]) == Decimal("1412.00")
    assert ant.json()["vigencia_fim"] == "2024-12-31"

    hoje = client.get("/v1/comercial/salario-minimo/na-data", headers=h, params={"data": "2025-06-01"})
    assert Decimal(hoje.json()["valor"]) == Decimal("1518.00")

    bad = client.post(
        "/v1/comercial/salario-minimo/atualizar-valor",
        headers=h,
        json={"valor": "1600.00", "vigencia_inicio": "2025-01-01"},
    )
    assert bad.status_code == 400


def test_sm_somente_admin(client, auth_headers):
    r = client.get("/v1/comercial/salario-minimo", headers=auth_headers["a1"])
    assert r.status_code == 403


def _seed_sm_e_itens(client, h):
    client.post(
        "/v1/comercial/salario-minimo",
        headers=h,
        json={"valor": "1000.00", "vigencia_inicio": "2020-01-01", "vigencia_fim": None},
    )
    pct = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={
            "nome": "Posto",
            "slug": "posto",
            "tipo": "percentual_sm",
            "percentual_sm": "30",
            "aplica_tier_posto": True,
            "ordem": 1,
        },
    )
    assert pct.status_code == 201, pct.text
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
    return pct.json(), fixo.json(), tef.json()


def test_item_crud_e_simular(client, auth_headers):
    h = auth_headers["admin"]
    item_pct, item_fixo, item_tef = _seed_sm_e_itens(client, h)

    dup = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={"nome": "X", "slug": "posto", "tipo": "valor_fixo", "valor_fixo": "1"},
    )
    assert dup.status_code == 400

    # Sem desconto: 30% de 1000 = 300; fixo 50; TEF 100+2*30=160 → 510
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
    assert Decimal(body["total"]) == Decimal("510.00")
    assert Decimal(body["total_custo"]) == Decimal("510.00")
    assert Decimal(body["salario_minimo"]) == Decimal("1000.00")
    assert len(body["linhas"]) == 3
    assert "snapshot" in body
    assert body["snapshot"]["versao"] == 1
    assert body["snapshot"]["total_custo"] == "510.00"
    assert body["desconto_posto_100k"] is False

    patch = client.patch(
        f"/v1/comercial/custos/itens/{item_fixo['id']}",
        headers=h,
        json={"ativo": False},
    )
    assert patch.status_code == 200
    assert patch.json()["ativo"] is False

    sim2 = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={"item_ids": [item_fixo["id"]], "quantidade_pdvs": 1},
    )
    assert sim2.status_code == 400


def test_desconto_posto_100k_aplica_20_pct(client, auth_headers):
    """#332 — cliente declarou <100k → comercial ativa desconto (20% SM)."""
    h = auth_headers["admin"]
    item_pct, _, _ = _seed_sm_e_itens(client, h)
    assert item_pct["aplica_tier_posto"] is True

    sem = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={"item_ids": [item_pct["id"]], "quantidade_pdvs": 1},
    )
    assert Decimal(sem.json()["total"]) == Decimal("300.00")  # 30%

    com = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={
            "item_ids": [item_pct["id"]],
            "quantidade_pdvs": 1,
            "desconto_posto_100k": True,
        },
    )
    assert com.status_code == 200, com.text
    body = com.json()
    assert Decimal(body["total"]) == Decimal("200.00")  # 20%
    assert body["desconto_posto_100k"] is True
    assert Decimal(body["linhas"][0]["percentual_usado"]) == Decimal("20")
    assert body["snapshot"]["itens"][0]["percentual_usado"] == "20"


def test_tef_pdvs_e_override(client, auth_headers):
    """#331 — fórmula PDVs + override de custo/valor cliente na proposta."""
    h = auth_headers["admin"]
    _, _, item_tef = _seed_sm_e_itens(client, h)

    um = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={"item_ids": [item_tef["id"]], "quantidade_pdvs": 1},
    )
    assert Decimal(um.json()["total"]) == Decimal("100.00")

    dois = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={"item_ids": [item_tef["id"]], "quantidade_pdvs": 2},
    )
    assert Decimal(dois.json()["total"]) == Decimal("130.00")

    n = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={"item_ids": [item_tef["id"]], "quantidade_pdvs": 5},
    )
    assert Decimal(n.json()["total"]) == Decimal("220.00")  # 100 + 4*30

    over = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={
            "item_ids": [item_tef["id"]],
            "quantidade_pdvs": 3,
            "tef_override": {
                "tef_custo_base": "80.00",
                "tef_custo_adicional": "25.00",
                "tef_valor_cliente_base": "120.00",
                "tef_valor_cliente_adicional": "40.00",
            },
        },
    )
    assert over.status_code == 200, over.text
    body = over.json()
    # custo: 80 + 2*25 = 130; valor cliente NÃO entra no total
    assert Decimal(body["total"]) == Decimal("130.00")
    assert body["linhas"][0]["override_custo"] is True
    assert Decimal(body["linhas"][0]["tef_valor_cliente"]) == Decimal("200.00")  # 120+2*40
    snap = body["snapshot"]["itens"][0]
    assert snap["override_custo"] is True
    assert snap["tef_base_catalogo"] == "100.00"
    assert snap["tef_base_usado"] == "80.00"
    assert snap["tef_valor_cliente"] == "200.00"


def test_snapshot_imutavel_apos_alterar_sm(client, auth_headers):
    """#335 — snapshot já calculado não muda se o catálogo/SM mudarem depois."""
    h = auth_headers["admin"]
    item_pct, _, _ = _seed_sm_e_itens(client, h)
    sim = client.post(
        "/v1/comercial/custos/simular",
        headers=h,
        json={"item_ids": [item_pct["id"]], "quantidade_pdvs": 1, "desconto_posto_100k": True},
    )
    snap = sim.json()["snapshot"]
    total_antes = snap["total_custo"]

    client.post(
        "/v1/comercial/salario-minimo/atualizar-valor",
        headers=h,
        json={"valor": "2000.00", "vigencia_inicio": "2026-01-01"},
    )
    # Objecto snapshot já devolvido permanece igual
    assert snap["total_custo"] == total_antes
    assert snap["salario_minimo"]["valor"] == "1000.00"


def test_item_exige_campos_por_tipo(client, auth_headers):
    h = auth_headers["admin"]
    r = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={"nome": "Sem %", "slug": "sem-pct", "tipo": "percentual_sm"},
    )
    assert r.status_code == 422


def test_aplica_tier_posto_so_percentual(client, auth_headers):
    h = auth_headers["admin"]
    r = client.post(
        "/v1/comercial/custos/itens",
        headers=h,
        json={
            "nome": "TEF bad",
            "slug": "tef-bad",
            "tipo": "composto_tef",
            "tef_base": "1",
            "tef_adicional": "1",
            "aplica_tier_posto": True,
        },
    )
    assert r.status_code == 422
