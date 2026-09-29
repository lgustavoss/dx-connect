"""CRM — leads, funil e negociações (#322 / #336–#340)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

    lst = client.get("/v1/comercial/custos/itens", headers=h_com)
    assert lst.status_code == 200, lst.text
    assert lst.json()["total"] >= 1

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


def _negociacao_comercial(client, auth_headers) -> int:
    r = client.post(
        "/v1/crm/leads",
        headers=auth_headers["comercial"],
        json={"nome": "Posto Lembrete"},
    )
    assert r.status_code == 201, r.text
    return r.json()["negociacao_ativa_id"]


def test_nota_mostra_autor_e_autor_edita_em_5_minutos(client, auth_headers, db_session, seed_base):
    h = auth_headers["comercial"]
    neg_id = _negociacao_comercial(client, auth_headers)
    quando = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    nota = client.post(
        f"/v1/crm/negociacoes/{neg_id}/atividades",
        headers=h,
        json={"tipo": "nota", "texto": "Reunião marcada", "lembrete_em": quando},
    )
    assert nota.status_code == 201, nota.text
    body = nota.json()
    assert body["autor_nome"] == "Comercial"
    assert body["autor_id"] == seed_base["comercial"].id
    assert body["pode_editar"] is True
    assert body["lembrete_em"] is not None
    atividade_id = body["id"]

    edit = client.patch(
        f"/v1/crm/negociacoes/{neg_id}/atividades/{atividade_id}",
        headers=h,
        json={"texto": "Reunião remarcada para quinta"},
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["texto"] == "Reunião remarcada para quinta"
    assert edit.json()["updated_at"] is not None
    assert edit.json()["lembrete_em"] is not None

    alheio = client.patch(
        f"/v1/crm/negociacoes/{neg_id}/atividades/{atividade_id}",
        headers=auth_headers["admin"],
        json={"texto": "Não sou o autor"},
    )
    assert alheio.status_code == 403

    bloqueado = client.post(
        f"/v1/crm/negociacoes/{neg_id}/atividades",
        headers=auth_headers["a1"],
        json={"tipo": "nota", "texto": "Atendente não comercial"},
    )
    assert bloqueado.status_code == 403

    from app.models.crm import CrmNegociacaoAtividade

    row = db_session.get(CrmNegociacaoAtividade, atividade_id)
    row.created_at = datetime.now(timezone.utc) - timedelta(minutes=6)
    db_session.commit()

    tarde = client.patch(
        f"/v1/crm/negociacoes/{neg_id}/atividades/{atividade_id}",
        headers=h,
        json={"texto": "Fora da janela"},
    )
    assert tarde.status_code == 400
    assert "5 minutos" in tarde.json()["detail"]


def test_mudanca_de_estagio_nao_edita_e_lembrete_no_passado_rejeitado(client, auth_headers):
    h = auth_headers["comercial"]
    neg_id = _negociacao_comercial(client, auth_headers)
    mv = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio",
        headers=h,
        json={"estagio_slug": "em_negociacao"},
    )
    assert mv.status_code == 200, mv.text

    acts = client.get(f"/v1/crm/negociacoes/{neg_id}/atividades", headers=h)
    estagio = next(a for a in acts.json()["items"] if a["tipo"] == "mudanca_estagio")
    assert estagio["pode_editar"] is False
    edit = client.patch(
        f"/v1/crm/negociacoes/{neg_id}/atividades/{estagio['id']}",
        headers=h,
        json={"texto": "Alterar estágio na mão"},
    )
    assert edit.status_code == 400

    passado = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    ruim = client.post(
        f"/v1/crm/negociacoes/{neg_id}/atividades",
        headers=h,
        json={"tipo": "nota", "texto": "Tarde demais", "lembrete_em": passado},
    )
    assert ruim.status_code == 400


def test_lembrete_repete_ate_o_autor_confirmar(client, auth_headers, db_session, seed_base):
    from app.models.crm import CrmNegociacaoAtividade
    from app.services.crm import reivindicar_lembretes_vencidos

    h = auth_headers["comercial"]
    neg_id = _negociacao_comercial(client, auth_headers)
    futuro = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    nota = client.post(
        f"/v1/crm/negociacoes/{neg_id}/atividades",
        headers=h,
        json={"tipo": "reuniao", "texto": "Apresentação do sistema", "lembrete_em": futuro},
    )
    assert nota.status_code == 201, nota.text
    atividade_id = nota.json()["id"]

    row = db_session.get(CrmNegociacaoAtividade, atividade_id)
    row.lembrete_em = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    pendentes = client.get("/v1/crm/lembretes-pendentes", headers=h)
    assert pendentes.status_code == 200, pendentes.text
    assert [item["atividade_id"] for item in pendentes.json()] == [atividade_id]
    assert client.get("/v1/crm/lembretes-pendentes", headers=auth_headers["a1"]).status_code == 403

    payloads = reivindicar_lembretes_vencidos(db_session)
    db_session.commit()
    assert len(payloads) == 1
    assert payloads[0]["negociacao_id"] == neg_id
    assert payloads[0]["lead_nome"] == "Posto Lembrete"
    assert payloads[0]["texto"] == "Apresentação do sistema"
    db_session.refresh(row)
    assert row.lembrete_disparado_em is None
    assert row.lembrete_tentativa_em is not None
    # Segunda reserva na mesma janela não dispara de novo (outro worker).
    assert reivindicar_lembretes_vencidos(db_session) == []

    row.lembrete_tentativa_em = datetime.now(timezone.utc) - timedelta(minutes=3)
    db_session.commit()
    de_novo = reivindicar_lembretes_vencidos(db_session)
    db_session.commit()
    assert len(de_novo) == 1
    assert de_novo[0]["atividade_id"] == atividade_id

    alheio = client.post(f"/v1/crm/lembretes/{atividade_id}/ciente", headers=auth_headers["admin"])
    assert alheio.status_code == 403

    ok = client.post(f"/v1/crm/lembretes/{atividade_id}/ciente", headers=h)
    assert ok.status_code == 204, ok.text
    assert client.get("/v1/crm/lembretes-pendentes", headers=h).json() == []
    db_session.refresh(row)
    row.lembrete_tentativa_em = datetime.now(timezone.utc) - timedelta(minutes=3)
    db_session.commit()
    assert reivindicar_lembretes_vencidos(db_session) == []
    assert seed_base["comercial"].id == row.autor_id
