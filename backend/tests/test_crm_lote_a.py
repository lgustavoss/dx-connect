"""CRM lote A — identidade do lead, notas, nova negociação e origem (#1319)."""
from __future__ import annotations


def _criar_lead(client, h, **campos):
    payload = {"nome": "Posto Teste", **campos}
    r = client.post("/v1/crm/leads", headers=h, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_origens_lead_seed_crud_e_permissao(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]

    r = client.get("/v1/crm/origens-lead", headers=h_com)
    assert r.status_code == 200, r.text
    nomes = [o["nome"] for o in r.json()]
    assert nomes[:5] == ["WhatsApp", "Indicação", "Site", "Visita", "Outro"]

    # Quem não edita o funil não mexe na lista
    assert client.post("/v1/crm/origens-lead", headers=h_com, json={"nome": "Balcão"}).status_code == 403

    novo = client.post("/v1/crm/origens-lead", headers=h_admin, json={"nome": "Balcão", "ordem": 60})
    assert novo.status_code == 201, novo.text
    oid = novo.json()["id"]
    assert client.post("/v1/crm/origens-lead", headers=h_admin, json={"nome": "balcão"}).status_code == 400

    ren = client.patch(f"/v1/crm/origens-lead/{oid}", headers=h_admin, json={"nome": "Balcão da loja"})
    assert ren.status_code == 200, ren.text
    assert ren.json()["nome"] == "Balcão da loja"

    # Em uso não pode excluir; desativar pode
    _criar_lead(client, h_com, origem="Balcão da loja")
    assert client.delete(f"/v1/crm/origens-lead/{oid}", headers=h_admin).status_code == 409
    assert client.patch(f"/v1/crm/origens-lead/{oid}", headers=h_admin, json={"ativo": False}).status_code == 200
    ativos = client.get("/v1/crm/origens-lead", headers=h_com).json()
    assert all(o["id"] != oid for o in ativos)


def test_origem_do_lead_vem_da_lista(client, auth_headers):
    h = auth_headers["comercial"]
    lead = _criar_lead(client, h, origem="whatsapp")  # minúsculo vira o nome canônico
    assert lead["origem"] == "WhatsApp"

    assert (
        client.post("/v1/crm/leads", headers=h, json={"nome": "Posto X", "origem": "panfleto"}).status_code
        == 400
    )
    assert (
        client.patch(f"/v1/crm/leads/{lead['id']}", headers=h, json={"origem": "panfleto"}).status_code
        == 400
    )
    ok = client.patch(f"/v1/crm/leads/{lead['id']}", headers=h, json={"origem": "Indicação"})
    assert ok.status_code == 200 and ok.json()["origem"] == "Indicação"


def test_notas_da_criacao_viram_primeira_anotacao(client, auth_headers):
    h = auth_headers["comercial"]
    lead = _criar_lead(client, h, notas="Cliente pediu retorno à tarde")
    neg_id = lead["negociacao_ativa_id"]

    ativ = client.get(f"/v1/crm/negociacoes/{neg_id}/atividades", headers=h)
    assert ativ.status_code == 200, ativ.text
    textos = [a["texto"] for a in ativ.json()["items"]]
    assert "Cliente pediu retorno à tarde" in textos


def test_identidade_do_lead_sugere_rede_e_razao_social(client, auth_headers):
    h = auth_headers["comercial"]
    lead = _criar_lead(client, h, nome="Medalha", empresa_texto="Auto Posto Medalha")
    neg = client.get(f"/v1/crm/negociacoes/{lead['negociacao_ativa_id']}", headers=h).json()
    assert neg["nome_base_webposto"] == "Auto Posto Medalha"

    linha = client.post(
        f"/v1/crm/negociacoes/{neg['id']}/linhas", headers=h, json={"valor_negociado": "100.00"}
    )
    assert linha.status_code == 201, linha.text
    assert linha.json()["razao_social"] == "Auto Posto Medalha"

    # Valor explícito do comercial manda (a sugestão é só a primeira vez)
    linha2 = client.post(
        f"/v1/crm/negociacoes/{neg['id']}/linhas",
        headers=h,
        json={"razao_social": "Medalha LTDA", "valor_negociado": "10.00"},
    )
    assert linha2.status_code == 201, linha2.text
    assert linha2.json()["razao_social"] == "Medalha LTDA"


def test_segunda_negociacao_ativa_bloqueada_com_nome_da_rede(client, auth_headers):
    h = auth_headers["comercial"]
    lead = _criar_lead(client, h, empresa_texto="Posto A")
    neg = client.post(
        "/v1/crm/negociacoes",
        headers=h,
        json={"lead_id": lead["id"], "nome_base_webposto": "Outra Rede"},
    )
    # Já existe negociação ativa: sem encerrar não cria
    assert neg.status_code == 400


def test_lead_perdido_aceita_nova_negociacao(client, auth_headers):
    h = auth_headers["comercial"]
    lead = _criar_lead(client, h, nome="Perdido Teste")
    neg_id = lead["negociacao_ativa_id"]

    mv = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio", headers=h, json={"estagio_slug": "perdido"}
    )
    assert mv.status_code == 200, mv.text

    nova = client.post("/v1/crm/negociacoes", headers=h, json={"lead_id": lead["id"]})
    assert nova.status_code == 201, nova.text
    assert nova.json()["ativa"] is True
    assert nova.json()["id"] != neg_id

    # A nova negociação reabre o lead no primeiro estágio
    refeito = client.get(f"/v1/crm/leads/{lead['id']}", headers=h).json()
    assert refeito["estagio_slug"] == "lead"
    assert refeito["negociacao_ativa_id"] == nova.json()["id"]
