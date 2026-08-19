"""Proposta comercial — templates, montagem e PDF (#323 / #345–#347)."""

from __future__ import annotations

import pytest

TERMOS_INTERNOS = (
    "total_custo",
    "margem_calculada",
    "snapshot_custo",
    "valor_custo",
    "override_custo",
    "tef_override",
    "lucro bruto",
)


@pytest.fixture(autouse=True)
def _pdf_fake(monkeypatch):
    def _fake(html: str) -> bytes:
        return b"%PDF-1.4\n" + html.encode("utf-8")

    monkeypatch.setattr("app.services.comercial_proposta.html_para_pdf", _fake)


def _criar_item_catalogo(client, h_admin) -> int:
    client.post(
        "/v1/comercial/salario-minimo",
        headers=h_admin,
        json={"valor": "1518.00", "vigencia_inicio": "2025-01-01", "vigencia_fim": None},
    )
    item = client.post(
        "/v1/comercial/custos/itens",
        headers=h_admin,
        json={
            "nome": "Licença mensal",
            "slug": "licenca-proposta-test",
            "tipo": "percentual_sm",
            "percentual_sm": "10",
            "aplica_tier_posto": False,
            "ordem": 1,
            "ativo": True,
        },
    )
    assert item.status_code == 201, item.text
    return item.json()["id"]


def _negociacao_com_linha(client, h, *, item_id: int | None = None):
    lead = client.post("/v1/crm/leads", headers=h, json={"nome": "Posto Proposta"}).json()
    neg_id = lead["negociacao_ativa_id"]
    payload = {
        "razao_social": "Posto Proposta LTDA",
        "cnpj": "12.345.678/0001-95",
        "valor_negociado": "800.00",
        "item_ids": [item_id] if item_id else [],
    }
    ln = client.post(f"/v1/crm/negociacoes/{neg_id}/linhas", headers=h, json=payload)
    assert ln.status_code == 201, ln.text
    return neg_id, ln.json()


def _assert_sem_internos(texto: str | bytes) -> None:
    blob = texto.decode("utf-8", errors="ignore") if isinstance(texto, (bytes, bytearray)) else texto
    low = blob.lower()
    for termo in TERMOS_INTERNOS:
        assert termo not in low, f"vazamento de «{termo}» no documento do cliente"


def test_atendente_403_proposta(client, auth_headers, seed_base):
    h = auth_headers["a1"]
    assert client.get("/v1/comercial/proposta-templates", headers=h).status_code == 403
    assert client.get("/v1/comercial/propostas", headers=h, params={"negociacao_id": 1}).status_code == 403
    assert client.post(
        "/v1/comercial/propostas",
        headers=h,
        json={"negociacao_id": 1},
    ).status_code == 403


def test_comercial_403_crud_templates(client, auth_headers):
    h = auth_headers["comercial"]
    r = client.post(
        "/v1/comercial/proposta-templates",
        headers=h,
        json={"nome": "X", "conteudo_html": "<p>{{razao_social}}</p>"},
    )
    assert r.status_code == 403


def test_admin_crud_template_e_preview_sanitiza(client, auth_headers):
    h = auth_headers["admin"]
    created = client.post(
        "/v1/comercial/proposta-templates",
        headers=h,
        json={
            "nome": "Institucional",
            "conteudo_html": "<h1>{{razao_social}}</h1><script>alert(1)</script>",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["versao"] == 1
    assert "<script" not in body["conteudo_html"].lower()

    prev = client.post(
        "/v1/comercial/proposta-templates/preview",
        headers=h,
        json={"conteudo_html": '<p onclick="x()">Oi</p><iframe src="x"></iframe>'},
    )
    assert prev.status_code == 200
    html = prev.json()["html"]
    assert "onclick" not in html.lower()
    assert "iframe" not in html.lower()

    patched = client.patch(
        f"/v1/comercial/proposta-templates/{body['id']}",
        headers=h,
        json={"conteudo_html": "<p>Olá {{cnpj}}</p>"},
    )
    assert patched.status_code == 200
    assert "Olá" in patched.json()["conteudo_html"]

    lista = client.get("/v1/comercial/proposta-templates", headers=h)
    assert lista.status_code == 200
    assert any(t["id"] == body["id"] for t in lista.json())


def test_comercial_gera_proposta_sem_custo_e_pdf(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    item_id = _criar_item_catalogo(client, auth_headers["admin"])
    neg_id, linha = _negociacao_com_linha(client, h, item_id=item_id)

    gerada = client.post(
        "/v1/comercial/propostas",
        headers=h,
        json={
            "negociacao_id": neg_id,
            "linha_ids": [linha["id"]],
            "condicoes": "Pagamento até o dia 10.",
        },
    )
    assert gerada.status_code == 201, gerada.text
    prop = gerada.json()
    assert prop["status"] == "rascunho"
    html = prop["conteudo_html_snapshot"]
    assert "Posto Proposta LTDA" in html
    assert "800" in html
    assert "Licença mensal" in html
    assert "Pagamento até o dia 10" in html
    _assert_sem_internos(html)
    assert "margem" not in html.lower()
    assert "custo" not in html.lower()

    pdf = client.get(f"/v1/comercial/propostas/{prop['id']}/pdf", headers=h)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    _assert_sem_internos(pdf.content)
    assert b"custo" not in pdf.content.lower()
    assert b"margem" not in pdf.content.lower()

    lst = client.get("/v1/comercial/propostas", headers=h, params={"negociacao_id": neg_id})
    assert lst.status_code == 200
    assert len(lst.json()) == 1


def test_regeneracao_invalida_rascunho_e_preserva_snapshot(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    h_adm = auth_headers["admin"]
    neg_id, _ = _negociacao_com_linha(client, h)

    t1 = client.get("/v1/comercial/proposta-templates", headers=h)
    assert t1.status_code == 200, t1.text
    tmpl_id = t1.json()[0]["id"]

    p1 = client.post(
        "/v1/comercial/propostas",
        headers=h,
        json={"negociacao_id": neg_id, "template_id": tmpl_id, "condicoes": "v1"},
    )
    assert p1.status_code == 201, p1.text
    html_v1 = p1.json()["conteudo_html_snapshot"]
    assert "v1" in html_v1

    client.patch(
        f"/v1/comercial/proposta-templates/{tmpl_id}",
        headers=h_adm,
        json={"conteudo_html": "<p>NOVO {{razao_social}}</p><div>{{condicoes}}</div>"},
    )

    p2 = client.post(
        "/v1/comercial/propostas",
        headers=h,
        json={"negociacao_id": neg_id, "template_id": tmpl_id, "condicoes": "v2"},
    )
    assert p2.status_code == 201, p2.text
    assert p2.json()["id"] != p1.json()["id"]

    antiga = client.get(f"/v1/comercial/propostas/{p1.json()['id']}", headers=h)
    assert antiga.status_code == 200
    assert antiga.json()["status"] == "substituida"
    assert antiga.json()["conteudo_html_snapshot"] == html_v1
    assert "NOVO" not in antiga.json()["conteudo_html_snapshot"]

    nova = client.get(f"/v1/comercial/propostas/{p2.json()['id']}", headers=h)
    assert nova.json()["status"] == "rascunho"
    assert "v2" in nova.json()["conteudo_html_snapshot"]
    assert "NOVO" in nova.json()["conteudo_html_snapshot"]


def test_marcar_enviada_avanca_funil(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    neg_id, _ = _negociacao_com_linha(client, h)
    p = client.post("/v1/comercial/propostas", headers=h, json={"negociacao_id": neg_id})
    assert p.status_code == 201, p.text

    env = client.post(
        f"/v1/comercial/propostas/{p.json()['id']}/marcar-enviada",
        headers=h,
        json={"canal": "email", "avancar_funil": True},
    )
    assert env.status_code == 200, env.text
    assert env.json()["status"] == "enviada"
    assert env.json()["canal"] == "email"
    assert env.json()["enviado_em"]

    neg = client.get(f"/v1/crm/negociacoes/{neg_id}", headers=h)
    assert neg.status_code == 200
    assert neg.json()["estagio_slug"] == "proposta_enviada"

    acts = client.get(f"/v1/crm/negociacoes/{neg_id}/atividades", headers=h)
    textos = " ".join(a["texto"] for a in acts.json()["items"])
    assert "enviada" in textos.lower()
