"""Contrato comercial — templates, snapshot por CNPJ e PDF (#324 / #349–#352)."""

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
            "slug": "licenca-contrato-test",
            "tipo": "percentual_sm",
            "percentual_sm": "10",
            "aplica_tier_posto": False,
            "ordem": 1,
            "ativo": True,
        },
    )
    assert item.status_code == 201, item.text
    return item.json()["id"]


DADOS_FISCAIS_OK = {
    "endereco": "Rua das Palmeiras",
    "numero": "100",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "cep": "01001000",
    "resp_legal_nome": "Maria Silva",
    "resp_legal_cpf": "39053344705",
}


def _negociacao_com_linha(client, h, *, item_id: int | None = None, cnpj: str = "12.345.678/0001-95"):
    lead = client.post("/v1/crm/leads", headers=h, json={"nome": "Posto Contrato"}).json()
    neg_id = lead["negociacao_ativa_id"]
    base = client.patch(
        f"/v1/crm/negociacoes/{neg_id}",
        headers=h,
        json={"nome_base_webposto": "base_posto_contrato_qa"},
    )
    assert base.status_code == 200, base.text
    payload = {
        "razao_social": "Posto Contrato LTDA",
        "cnpj": cnpj,
        "valor_negociado": "900.00",
        "item_ids": [item_id] if item_id else [],
        "dados_fiscais": DADOS_FISCAIS_OK,
    }
    ln = client.post(f"/v1/crm/negociacoes/{neg_id}/linhas", headers=h, json=payload)
    assert ln.status_code == 201, ln.text
    return neg_id, ln.json()


def _anexar_pdf_assinado(client, h, contrato_id: int, *, referencia: str | None = "prot-1"):
    r = client.post(
        f"/v1/comercial/contratos/{contrato_id}/pdf-assinado",
        headers=h,
        files={"arquivo": ("assinado.pdf", b"%PDF-1.4 signed", "application/pdf")},
        data={"referencia_externa": referencia} if referencia is not None else None,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _assert_sem_internos(texto: str | bytes) -> None:
    blob = texto.decode("utf-8", errors="ignore") if isinstance(texto, (bytes, bytearray)) else texto
    low = blob.lower()
    for termo in TERMOS_INTERNOS:
        assert termo not in low, f"vazamento de «{termo}» no documento do cliente"


def test_atendente_403_contrato(client, auth_headers, seed_base):
    h = auth_headers["a1"]
    assert client.get("/v1/comercial/contrato-templates", headers=h).status_code == 403
    assert client.get("/v1/comercial/contratos", headers=h, params={"negociacao_id": 1}).status_code == 403
    assert client.post("/v1/comercial/contratos", headers=h, json={"linha_id": 1}).status_code == 403


def test_comercial_403_crud_contrato_templates(client, auth_headers):
    h = auth_headers["comercial"]
    r = client.post(
        "/v1/comercial/contrato-templates",
        headers=h,
        json={"nome": "X", "conteudo_html": "<p>{{razao_social}}</p>"},
    )
    assert r.status_code == 403


def test_admin_crud_contrato_template_e_preview(client, auth_headers):
    h = auth_headers["admin"]
    created = client.post(
        "/v1/comercial/contrato-templates",
        headers=h,
        json={
            "nome": "Institucional",
            "conteudo_html": "<h1>{{razao_social}}</h1><script>alert(1)</script>{{setup_bloco}}",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["versao"] == 1
    assert "<script" not in body["conteudo_html"].lower()

    prev = client.post(
        "/v1/comercial/contrato-templates/preview",
        headers=h,
        json={"conteudo_html": '<p onclick="x()">Oi</p><iframe src="x"></iframe>'},
    )
    assert prev.status_code == 200
    html = prev.json()["html"]
    assert "onclick" not in html.lower()
    assert "iframe" not in html.lower()

    patched = client.patch(
        f"/v1/comercial/contrato-templates/{body['id']}",
        headers=h,
        json={"conteudo_html": "<p>Olá {{cnpj}}</p>"},
    )
    assert patched.status_code == 200
    assert "Olá" in patched.json()["conteudo_html"]
    assert patched.json()["versao"] == 2

    mesmo_html = client.patch(
        f"/v1/comercial/contrato-templates/{body['id']}",
        headers=h,
        json={"ativo": True},
    )
    assert mesmo_html.status_code == 200
    assert mesmo_html.json()["versao"] == 2


def test_comercial_gera_contrato_sem_custo_e_pdf(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    item_id = _criar_item_catalogo(client, auth_headers["admin"])
    neg_id, linha = _negociacao_com_linha(client, h, item_id=item_id)

    gerada = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={
            "linha_id": linha["id"],
            "setup_valor": "1500.00",
            "setup_isento": False,
            "fidelidade_meses": 12,
        },
    )
    assert gerada.status_code == 201, gerada.text
    c = gerada.json()
    assert c["status"] == "rascunho"
    assert c["negociacao_id"] == neg_id
    assert float(c["valor_mensalidade"]) == 900
    assert c["setup_valor"] is not None
    assert c["fidelidade_meses"] == 12
    assert len(c["pdfs"]) == 1
    html = client.get(f"/v1/comercial/contratos/{c['id']}", headers=h).json()
    pdf = client.get(f"/v1/comercial/contratos/{c['id']}/pdf", headers=h)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    blob = pdf.content.decode("utf-8", errors="ignore")
    assert "Posto Contrato LTDA" in blob
    assert "900" in blob
    assert "Licença mensal" in blob
    assert "fidelidade" in blob.lower()
    assert "setup" in blob.lower()
    assert "fora" in blob.lower()
    assert "deslocamento" in blob.lower()
    _assert_sem_internos(blob)
    assert "margem" not in blob.lower()
    assert "snapshot_custo" not in blob.lower()
    # mensalidade não inclui o setup
    assert "1.500" in blob or "1500" in blob
    assert html["snapshot_itens"]

    lst = client.get("/v1/comercial/contratos", headers=h, params={"negociacao_id": neg_id})
    assert lst.status_code == 200
    assert len(lst.json()) == 1


def test_setup_isento_renderiza_bloco_e_nao_muda_mensalidade(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    neg_id, linha = _negociacao_com_linha(client, h)
    r = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={"linha_id": linha["id"], "setup_isento": True, "setup_valor": "2000.00"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["setup_isento"] is True
    assert float(r.json()["valor_mensalidade"]) == 900
    pdf = client.get(f"/v1/comercial/contratos/{r.json()['id']}/pdf", headers=h)
    blob = pdf.content.decode("utf-8", errors="ignore").lower()
    assert "isento" in blob
    assert "900" in blob


def test_um_contrato_ativo_por_linha_e_historico_pdf(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    _, linha = _negociacao_com_linha(client, h)
    p1 = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={"linha_id": linha["id"], "data_inicio": "2026-01-15"},
    )
    assert p1.status_code == 201, p1.text
    cid = p1.json()["id"]
    assert p1.json()["data_inicio"] == "2026-01-15"
    assert p1.json()["data_fim_fidelidade"] == "2027-01-15"
    hash1 = p1.json()["pdfs"][0]["conteudo_hash"]

    p2 = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={"linha_id": linha["id"], "data_inicio": "2026-02-01"},
    )
    assert p2.status_code == 201, p2.text
    assert p2.json()["id"] == cid
    assert p2.json()["data_inicio"] == "2026-02-01"
    assert len(p2.json()["pdfs"]) == 2
    assert p2.json()["pdfs"][0]["conteudo_hash"] == hash1
    assert p2.json()["pdfs"][1]["conteudo_hash"] != hash1

    pdf_v1 = client.get(
        f"/v1/comercial/contratos/{cid}/pdf",
        headers=h,
        params={"pdf_id": p2.json()["pdfs"][0]["id"]},
    )
    assert pdf_v1.status_code == 200
    assert b"15/01/2026" in pdf_v1.content


def test_assinado_nao_edita_snapshot(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    _, linha = _negociacao_com_linha(client, h)
    c = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    env = client.post(f"/v1/comercial/contratos/{cid}/marcar-enviado", headers=h, json={})
    assert env.status_code == 200
    assert env.json()["status"] == "enviado"
    regen = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert regen.status_code == 400

    sem_pdf = client.post(
        f"/v1/comercial/contratos/{cid}/marcar-assinado",
        headers=h,
        json={"avancar_funil": True},
    )
    assert sem_pdf.status_code == 400
    _anexar_pdf_assinado(client, h, cid)
    ass = client.post(
        f"/v1/comercial/contratos/{cid}/marcar-assinado",
        headers=h,
        json={"avancar_funil": True},
    )
    assert ass.status_code == 200, ass.text
    assert ass.json()["status"] == "assinado"
    assert ass.json()["assinado_em"]
    assert ass.json()["empresa_id"]
    assert ass.json()["tem_pdf_assinado"] is True
    regen2 = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert regen2.status_code == 400

    neg_id = c.json()["negociacao_id"]
    neg = client.get(f"/v1/crm/negociacoes/{neg_id}", headers=h)
    assert neg.json()["estagio_slug"] == "contrato_assinado"


def test_segunda_linha_pode_ter_contrato_proprio(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    lead = client.post("/v1/crm/leads", headers=h, json={"nome": "Rede Dois CNPJ"}).json()
    neg_id = lead["negociacao_ativa_id"]
    client.patch(
        f"/v1/crm/negociacoes/{neg_id}",
        headers=h,
        json={"nome_base_webposto": "base_dois_cnpj"},
    )
    l1 = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={
            "razao_social": "Posto A",
            "cnpj": "12.345.678/0001-95",
            "valor_negociado": "100",
            "dados_fiscais": DADOS_FISCAIS_OK,
        },
    )
    l2 = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={
            "razao_social": "Posto B",
            "cnpj": "98.765.432/0001-10",
            "valor_negociado": "200",
            "dados_fiscais": DADOS_FISCAIS_OK,
        },
    )
    assert l1.status_code == 201 and l2.status_code == 201
    c1 = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": l1.json()["id"]})
    c2 = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": l2.json()["id"]})
    assert c1.status_code == 201 and c2.status_code == 201
    assert c1.json()["id"] != c2.json()["id"]
    lst = client.get("/v1/comercial/contratos", headers=h, params={"negociacao_id": neg_id})
    assert len(lst.json()) == 2


def test_lista_so_minhas_e_interno_nao_vai_no_pdf(client, auth_headers, seed_base):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    _, linha_com = _negociacao_com_linha(client, h_com)
    c_com = client.post("/v1/comercial/contratos", headers=h_com, json={"linha_id": linha_com["id"]})
    assert c_com.status_code == 201, c_com.text

    _, linha_adm = _negociacao_com_linha(client, h_admin)
    c_adm = client.post("/v1/comercial/contratos", headers=h_admin, json={"linha_id": linha_adm["id"]})
    assert c_adm.status_code == 201, c_adm.text

    lst_com = client.get("/v1/comercial/contratos", headers=h_com)
    assert lst_com.status_code == 200
    ids_com = {r["id"] for r in lst_com.json()}
    assert c_com.json()["id"] in ids_com
    assert c_adm.json()["id"] not in ids_com
    assert all(r.get("conteudo_html_snapshot") is None for r in lst_com.json())

    lst_admin = client.get("/v1/comercial/contratos", headers=h_admin)
    ids_admin = {r["id"] for r in lst_admin.json()}
    assert c_com.json()["id"] in ids_admin
    assert c_adm.json()["id"] in ids_admin

    detalhe = client.get(f"/v1/comercial/contratos/{c_com.json()['id']}", headers=h_com).json()
    assert detalhe["interno"] is not None
    assert "total_custo" in detalhe["interno"]
    assert detalhe["interno"]["lucro_bruto"] is not None
    assert detalhe["interno"]["margem_percentual"] is not None
    assert detalhe["responsavel_nome"]
    assert detalhe["dias_restantes_fidelidade"] is not None

    lst_resp = client.get(
        "/v1/comercial/contratos",
        headers=h_admin,
        params={"responsavel_id": seed_base["comercial"].id},
    )
    ids_resp = {r["id"] for r in lst_resp.json()}
    assert c_com.json()["id"] in ids_resp
    assert c_adm.json()["id"] not in ids_resp
    pdf = client.get(f"/v1/comercial/contratos/{c_com.json()['id']}/pdf", headers=h_com)
    _assert_sem_internos(pdf.content)
    assert "margem" not in pdf.content.decode("utf-8", errors="ignore").lower()

    alheio = c_adm.json()["id"]
    assert client.get(f"/v1/comercial/contratos/{alheio}", headers=h_com).status_code == 403
    assert client.get(f"/v1/comercial/contratos/{alheio}/pdf", headers=h_com).status_code == 403
    assert client.post(f"/v1/comercial/contratos/{alheio}/marcar-enviado", headers=h_com, json={}).status_code == 403
    assert client.post(f"/v1/comercial/contratos/{alheio}/cancelar", headers=h_com).status_code == 403
    assert client.post("/v1/comercial/contratos", headers=h_com, json={"linha_id": linha_adm["id"]}).status_code == 403
    assert client.get(f"/v1/comercial/contratos/{alheio}", headers=h_admin).status_code == 200


def test_cancelar_rascunho_e_bloqueia_assinado(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    _, linha = _negociacao_com_linha(client, h)
    c = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    cid = c.json()["id"]
    cancelado = client.post(f"/v1/comercial/contratos/{cid}/cancelar", headers=h)
    assert cancelado.status_code == 200, cancelado.text
    assert cancelado.json()["status"] == "cancelado"
    assert client.post(f"/v1/comercial/contratos/{cid}/cancelar", headers=h).status_code == 400

    novo = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert novo.status_code == 201, novo.text
    nid = novo.json()["id"]
    assert nid != cid
    _anexar_pdf_assinado(client, h, nid)
    ass = client.post(f"/v1/comercial/contratos/{nid}/marcar-assinado", headers=h, json={})
    assert ass.status_code == 200
    assert client.post(f"/v1/comercial/contratos/{nid}/cancelar", headers=h).status_code == 400


def test_versao_do_modelo_fica_gravada_no_contrato(client, auth_headers, seed_base):
    h_admin = auth_headers["admin"]
    h = auth_headers["comercial"]
    tmpl = client.post(
        "/v1/comercial/contrato-templates",
        headers=h_admin,
        json={"nome": "Freeze", "conteudo_html": "<p>v1 {{razao_social}}</p>"},
    ).json()
    assert tmpl["versao"] == 1
    _, linha = _negociacao_com_linha(client, h)
    gerado = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={"linha_id": linha["id"], "template_id": tmpl["id"]},
    )
    assert gerado.status_code == 201, gerado.text
    assert gerado.json()["template_versao"] == 1

    patched = client.patch(
        f"/v1/comercial/contrato-templates/{tmpl['id']}",
        headers=h_admin,
        json={"conteudo_html": "<p>v2 {{cnpj}}</p>"},
    )
    assert patched.json()["versao"] == 2
    frozen = client.get(f"/v1/comercial/contratos/{gerado.json()['id']}", headers=h).json()
    assert frozen["template_versao"] == 1

    regen = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={"linha_id": linha["id"], "template_id": tmpl["id"]},
    )
    assert regen.status_code == 201, regen.text
    assert regen.json()["template_versao"] == 2


def test_gerar_exige_fiscal_e_base_webposto(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    lead = client.post("/v1/crm/leads", headers=h, json={"nome": "Sem Fiscal"}).json()
    neg_id = lead["negociacao_ativa_id"]
    ln = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={"razao_social": "Posto X", "cnpj": "12.345.678/0001-95", "valor_negociado": "10"},
    )
    assert ln.status_code == 201
    r = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": ln.json()["id"]})
    assert r.status_code == 400
    client.patch(f"/v1/crm/negociacoes/{neg_id}", headers=h, json={"nome_base_webposto": "base_x"})
    r2 = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": ln.json()["id"]})
    assert r2.status_code == 400
    client.patch(
        f"/v1/crm/negociacoes/{neg_id}/linhas/{ln.json()['id']}",
        headers=h,
        json={"dados_fiscais": DADOS_FISCAIS_OK},
    )
    ok = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": ln.json()["id"]})
    assert ok.status_code == 201, ok.text
    html = ok.json()["conteudo_html_snapshot"] or ""
    assert "Maria Silva" in html
    assert "base_x" in html


def test_reajuste_politica_e_override(client, auth_headers, seed_base):
    h_admin = auth_headers["admin"]
    h = auth_headers["comercial"]
    assert client.patch(
        "/v1/comercial/contrato-politica",
        headers=h,
        json={"reajuste_percentual": "8.5", "reajuste_rotulo": "IGPM interno"},
    ).status_code == 403
    pol = client.patch(
        "/v1/comercial/contrato-politica",
        headers=h_admin,
        json={"reajuste_percentual": "8.5", "reajuste_rotulo": "IGPM interno"},
    )
    assert pol.status_code == 200, pol.text
    _, linha = _negociacao_com_linha(client, h)
    herdado = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert herdado.status_code == 201, herdado.text
    assert float(herdado.json()["reajuste_percentual"]) == 8.5
    assert "8,50%" in (herdado.json()["conteudo_html_snapshot"] or "")
    assert "IGPM interno" in (herdado.json()["conteudo_html_snapshot"] or "")
    sem = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={"linha_id": linha["id"], "sem_reajuste": True},
    )
    assert sem.status_code == 201
    assert float(sem.json()["reajuste_percentual"]) == 0
    assert "sem reajuste" in (sem.json()["conteudo_html_snapshot"] or "")


def test_conversao_idempotente_mesma_rede_dois_cnpjs(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    lead = client.post("/v1/crm/leads", headers=h, json={"nome": "Rede Conv"}).json()
    neg_id = lead["negociacao_ativa_id"]
    client.patch(f"/v1/crm/negociacoes/{neg_id}", headers=h, json={"nome_base_webposto": "base_conv_unica"})
    l1 = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={
            "razao_social": "Posto A Ltda",
            "cnpj": "12.345.678/0001-95",
            "valor_negociado": "100",
            "dados_fiscais": DADOS_FISCAIS_OK,
        },
    ).json()
    l2 = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={
            "razao_social": "Posto B Ltda",
            "cnpj": "98.765.432/0001-10",
            "valor_negociado": "200",
            "dados_fiscais": DADOS_FISCAIS_OK,
        },
    ).json()
    c1 = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": l1["id"]}).json()
    c2 = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": l2["id"]}).json()
    _anexar_pdf_assinado(client, h, c1["id"])
    _anexar_pdf_assinado(client, h, c2["id"])
    a1 = client.post(f"/v1/comercial/contratos/{c1['id']}/marcar-assinado", headers=h, json={}).json()
    a2 = client.post(f"/v1/comercial/contratos/{c2['id']}/marcar-assinado", headers=h, json={}).json()
    assert a1["empresa_id"] and a2["empresa_id"]
    assert a1["empresa_id"] != a2["empresa_id"]
    e1 = client.get(f"/v1/empresas/{a1['empresa_id']}", headers=auth_headers["admin"]).json()
    e2 = client.get(f"/v1/empresas/{a2['empresa_id']}", headers=auth_headers["admin"]).json()
    assert e1["rede_id"] == e2["rede_id"]
    assert e1["cnpj_cpf"]
    again = client.post(
        f"/v1/comercial/contratos/{c1['id']}/pdf-assinado",
        headers=h,
        files={"arquivo": ("x.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert again.status_code == 400


def test_conversao_copia_contato_e_cria_colaborador(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    lead = client.post(
        "/v1/crm/leads",
        headers=h,
        json={"nome": "Posto Contato", "email": "lead@email.com", "telefone": "34988887777"},
    ).json()
    neg_id = lead["negociacao_ativa_id"]
    client.patch(f"/v1/crm/negociacoes/{neg_id}", headers=h, json={"nome_base_webposto": "base_contato_qa"})
    ln = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={
            "razao_social": "Posto Contato Ltda",
            "cnpj": "12.345.678/0001-95",
            "valor_negociado": "100",
            "dados_fiscais": {
                **DADOS_FISCAIS_OK,
                "email": "empresa@email.com",
                "telefone": "3432221111",
            },
        },
    ).json()
    cid = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": ln["id"]}).json()["id"]
    _anexar_pdf_assinado(client, h, cid)
    ass = client.post(f"/v1/comercial/contratos/{cid}/marcar-assinado", headers=h, json={}).json()
    assert ass["empresa_id"]
    assert ass["rede_id"]
    emp = client.get(f"/v1/empresas/{ass['empresa_id']}", headers=h_admin).json()
    assert emp["email"] == "empresa@email.com"
    assert "".join(c for c in (emp["telefone"] or "") if c.isdigit()).endswith("32221111")
    funcs = client.get(f"/v1/redes/{emp['rede_id']}/funcionarios", headers=h_admin)
    assert funcs.status_code == 200, funcs.text
    items = funcs.json()["items"]
    tels = {"".join(c for c in (f.get("telefone") or "") if c.isdigit()) for f in items}
    emails = {(f.get("email") or "").lower() for f in items}
    assert any(t.endswith("32221111") for t in tels)
    assert "empresa@email.com" in emails


def test_conversao_usa_contato_do_lead_se_linha_nao_tem(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    lead = client.post(
        "/v1/crm/leads",
        headers=h,
        json={"nome": "Lead Fallback", "email": "lead-fallback@email.com", "telefone": "34911112222"},
    ).json()
    neg_id = lead["negociacao_ativa_id"]
    client.patch(f"/v1/crm/negociacoes/{neg_id}", headers=h, json={"nome_base_webposto": "base_lead_fallback"})
    ln = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={
            "razao_social": "Posto Fallback Ltda",
            "cnpj": "98.765.432/0001-10",
            "valor_negociado": "100",
            "dados_fiscais": DADOS_FISCAIS_OK,
        },
    ).json()
    cid = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": ln["id"]}).json()["id"]
    _anexar_pdf_assinado(client, h, cid)
    ass = client.post(f"/v1/comercial/contratos/{cid}/marcar-assinado", headers=h, json={}).json()
    emp = client.get(f"/v1/empresas/{ass['empresa_id']}", headers=h_admin).json()
    assert emp["email"] == "lead-fallback@email.com"
    assert "".join(c for c in (emp["telefone"] or "") if c.isdigit()).endswith("911112222")


def test_bloqueia_edicao_apos_contrato_assinado(client, auth_headers, seed_base):
    h = auth_headers["comercial"]
    neg_id, linha = _negociacao_com_linha(client, h)
    cid = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]}).json()["id"]
    _anexar_pdf_assinado(client, h, cid)
    assert client.post(f"/v1/comercial/contratos/{cid}/marcar-assinado", headers=h, json={}).status_code == 200
    patch_ln = client.patch(
        f"/v1/crm/negociacoes/{neg_id}/linhas/{linha['id']}",
        headers=h,
        json={"valor_negociado": "1"},
    )
    assert patch_ln.status_code == 400
    patch_neg = client.patch(
        f"/v1/crm/negociacoes/{neg_id}",
        headers=h,
        json={"nome_base_webposto": "nome_alterado_apos_assinatura"},
    )
    assert patch_neg.status_code == 400
    deleted = client.delete(f"/v1/crm/negociacoes/{neg_id}/linhas/{linha['id']}", headers=h)
    assert deleted.status_code == 400

