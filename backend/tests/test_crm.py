"""CRM — leads, funil e negociações (#322 / #336–#340)."""

from __future__ import annotations

from decimal import Decimal


def test_atendente_403_crm_e_comercial_ok(client, auth_headers):
    r = client.get("/v1/crm/leads", headers=auth_headers["a1"])
    assert r.status_code == 403

    r2 = client.get("/v1/crm/funil-estagios", headers=auth_headers["comercial"])
    assert r2.status_code == 200
    assert len(r2.json()) >= 5
    assert any(e["slug"] == "lead" for e in r2.json())


def test_comercial_403_cadastros_admin(client, auth_headers):
    h = auth_headers["comercial"]
    assert client.get("/v1/redes", headers=h).status_code == 403
    assert client.get("/v1/audit", headers=h).status_code == 403
    assert client.get("/v1/comercial/salario-minimo", headers=h).status_code == 403
    assert client.post("/v1/crm/funil-estagios", headers=h, json={
        "slug": "x",
        "nome": "X",
        "ordem": 1,
        "tipo": "aberto",
    }).status_code == 403


def test_fluxo_lead_negociacao_estagio_e_cnpj(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    comercial_id = seed_base["comercial"].id

    # Cria lead (+ negociação ativa)
    r = client.post(
        "/v1/crm/leads",
        headers=h,
        json={"nome": "Posto Alpha", "telefone": "11999990000", "origem": "whatsapp"},
    )
    assert r.status_code == 201, r.text
    lead = r.json()
    assert lead["responsavel_id"] == comercial_id
    assert lead["estagio_slug"] == "lead"
    assert lead["negociacao_ativa_id"] is not None
    neg_id = lead["negociacao_ativa_id"]

    # Segunda negociação ativa bloqueada
    r2 = client.post(
        "/v1/crm/negociacoes",
        headers=h,
        json={"lead_id": lead["id"]},
    )
    assert r2.status_code == 400

    # Linha sem CNPJ (ok no início)
    ln = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={"razao_social": "Alpha LTDA", "valor_negociado": "500.00", "item_ids": []},
    )
    assert ln.status_code == 201, ln.text
    assert ln.json()["cnpj"] is None
    assert Decimal(ln.json()["margem_calculada"]) == Decimal("500.00")

    # Avança para em_negociacao
    mv = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio",
        headers=h,
        json={"estagio_slug": "em_negociacao", "nota": "Cliente interessado"},
    )
    assert mv.status_code == 200, mv.text
    assert mv.json()["estagio_slug"] == "em_negociacao"

    # Documentação exige CNPJ
    bad = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio",
        headers=h,
        json={"estagio_slug": "documentacao"},
    )
    assert bad.status_code == 400
    assert "CNPJ" in bad.json()["detail"]

    # Preenche CNPJ e avança
    up = client.patch(
        f"/v1/crm/negociacoes/{neg_id}/linhas/{ln.json()['id']}",
        headers=h,
        json={"cnpj": "12.345.678/0001-95"},
    )
    assert up.status_code == 200, up.text
    assert up.json()["cnpj"] == "12345678000195"

    ok = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio",
        headers=h,
        json={"estagio_slug": "documentacao"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["estagio_slug"] == "documentacao"

    # Timeline
    acts = client.get(f"/v1/crm/negociacoes/{neg_id}/atividades", headers=h)
    assert acts.status_code == 200
    assert acts.json()["total"] >= 2

    nota = client.post(
        f"/v1/crm/negociacoes/{neg_id}/atividades",
        headers=h,
        json={"tipo": "nota", "texto": "Enviar docs por e-mail"},
    )
    assert nota.status_code == 201

    # Perdido arquiva negociação
    perd = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio",
        headers=h,
        json={"estagio_slug": "perdido", "nota": "Sem retorno"},
    )
    assert perd.status_code == 200
    assert perd.json()["ativa"] is False
    lead2 = client.get(f"/v1/crm/leads/{lead['id']}", headers=h)
    assert lead2.json()["perdido_em"] is not None


def test_admin_ve_todas_e_filtro_so_minhas(client, auth_headers, seed_base):
    h_com = auth_headers["comercial"]
    h_adm = auth_headers["admin"]

    client.post("/v1/crm/leads", headers=h_com, json={"nome": "Lead Comercial"})
    client.post(
        "/v1/crm/leads",
        headers=h_adm,
        json={"nome": "Lead Admin", "responsavel_id": seed_base["admin"].id},
    )

    todas = client.get("/v1/crm/leads", headers=h_com)
    assert todas.status_code == 200
    assert todas.json()["total"] == 2

    minhas = client.get("/v1/crm/leads", headers=h_com, params={"so_minhas": True})
    assert minhas.json()["total"] == 1
    assert minhas.json()["items"][0]["nome"] == "Lead Comercial"


def test_comercial_pode_simular_custos(client, auth_headers):
    h_adm = auth_headers["admin"]
    h_com = auth_headers["comercial"]

    client.post(
        "/v1/comercial/salario-minimo",
        headers=h_adm,
        json={"valor": "1518.00", "vigencia_inicio": "2025-01-01", "vigencia_fim": None},
    )
    item = client.post(
        "/v1/comercial/custos/itens",
        headers=h_adm,
        json={
            "nome": "Licença",
            "slug": "licenca-crm-test",
            "tipo": "percentual_sm",
            "percentual_sm": "10",
            "aplica_tier_posto": False,
            "ordem": 1,
            "ativo": True,
        },
    )
    assert item.status_code == 201, item.text

    sim = client.post(
        "/v1/comercial/custos/simular",
        headers=h_com,
        json={"item_ids": [item.json()["id"]], "quantidade_pdvs": 1},
    )
    assert sim.status_code == 200, sim.text
    assert "snapshot" in sim.json()

    # Atendente continua bloqueado
    assert (
        client.post(
            "/v1/comercial/custos/simular",
            headers=auth_headers["a1"],
            json={"item_ids": [item.json()["id"]]},
        ).status_code
        == 403
    )
