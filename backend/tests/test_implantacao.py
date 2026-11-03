"""Implantação via ticket e checklist (#325 / #358–#361)."""

from __future__ import annotations

from app.models import StatusTicket
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from tests.test_comercial_contrato import _anexar_pdf_assinado, _negociacao_com_linha


def _assinar_contrato(client, h):
    _, linha = _negociacao_com_linha(client, h)
    c = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    _anexar_pdf_assinado(client, h, cid)
    ass = client.post(
        f"/v1/comercial/contratos/{cid}/marcar-assinado",
        headers=h,
        json={"abrir_ticket_implantacao": True},
    )
    assert ass.status_code == 200, ass.text
    return ass.json()


def test_comercial_le_template_admin_escreve(client, auth_headers):
    h_admin = auth_headers["admin"]
    h_com = auth_headers["comercial"]
    h_at = auth_headers["a1"]

    lst = client.get("/v1/comercial/implantacao-templates", headers=h_com)
    assert lst.status_code == 200, lst.text
    assert len(lst.json()) >= 1
    chaves = {i.get("chave") for t in lst.json() for i in t["itens"]}
    assert "cadastrar_pdvs" in chaves

    assert client.post(
        "/v1/comercial/implantacao-templates",
        headers=h_com,
        json={"nome": "X", "itens": [{"titulo": "A", "ordem": 1, "obrigatorio": True}]},
    ).status_code == 403
    assert client.post(
        "/v1/comercial/implantacao-templates",
        headers=h_at,
        json={"nome": "X", "itens": [{"titulo": "A", "ordem": 1, "obrigatorio": True}]},
    ).status_code == 403

    tid = lst.json()[0]["id"]
    patch = client.patch(
        f"/v1/comercial/implantacao-templates/{tid}",
        headers=h_admin,
        json={
            "nome": "Implantação padrão",
            "itens": [
                {"titulo": "Docs", "ordem": 1, "obrigatorio": True},
                {"titulo": "PDVs", "ordem": 2, "obrigatorio": True, "chave": "cadastrar_pdvs"},
            ],
        },
    )
    assert patch.status_code == 200, patch.text
    assert len(patch.json()["itens"]) == 2
    assert patch.json()["versao"] >= 2

    created = client.post(
        "/v1/comercial/implantacao-templates",
        headers=h_admin,
        json={
            "nome": "Checklist extra",
            "itens": [{"titulo": "Kickoff", "ordem": 1, "obrigatorio": True}],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["nome"] == "Checklist extra"


def test_marcar_assinado_abre_ticket_idempotente(client, auth_headers):
    h = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    body = _assinar_contrato(client, h)
    assert body["status"] == "assinado"
    tid = body["implantacao_ticket_id"]
    assert tid
    assert body["implantacao_ticket_protocolo"]

    t = client.get(f"/v1/tickets/{tid}", headers=h_admin)
    assert t.status_code == 200, t.text
    assert t.json()["contrato_id"] == body["id"]
    assert t.json()["assunto"].startswith("Implantação")

    chk = client.get(f"/v1/tickets/{tid}/checklist", headers=h_admin)
    assert chk.status_code == 200, chk.text
    data = chk.json()
    assert data["aplicavel"] is True
    assert data["contrato_id"] == body["id"]
    assert len(data["itens"]) >= 1
    assert data["progresso_pct"] == 0

    # reprocessar assinatura não duplica
    again = client.post(f"/v1/comercial/contratos/{body['id']}/marcar-assinado", headers=h, json={})
    assert again.status_code == 400
    body2 = client.get(f"/v1/comercial/contratos/{body['id']}", headers=h).json()
    assert body2["implantacao_ticket_id"] == tid


def test_ticket_so_abre_quando_pedido(client, auth_headers):
    h = auth_headers["comercial"]
    _, linha = _negociacao_com_linha(client, h)
    primeiro = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert primeiro.status_code == 201, primeiro.text
    cid = primeiro.json()["id"]
    _anexar_pdf_assinado(client, h, cid)
    sem = client.post(f"/v1/comercial/contratos/{cid}/marcar-assinado", headers=h, json={})
    assert sem.status_code == 200, sem.text
    assert sem.json()["implantacao_ticket_id"] is None

    aditivo = client.post("/v1/comercial/contratos", headers=h, json={"linha_id": linha["id"]})
    assert aditivo.status_code == 201, aditivo.text
    aid = aditivo.json()["id"]
    assert aid != cid
    _anexar_pdf_assinado(client, h, aid, referencia="prot-aditivo")
    com = client.post(
        f"/v1/comercial/contratos/{aid}/marcar-assinado",
        headers=h,
        json={"abrir_ticket_implantacao": True},
    )
    assert com.status_code == 200, com.text
    assert com.json()["implantacao_ticket_id"]
    assert com.json()["implantacao_ticket_id"] != sem.json()["implantacao_ticket_id"]
    antigo = client.get(f"/v1/comercial/contratos/{cid}", headers=h).json()
    assert antigo["status"] == "assinado"
    assert antigo["implantacao_ticket_id"] is None


def test_checklist_rbac_e_fechar_bloqueado(client, auth_headers, seed_base, db_session):
    h_com = auth_headers["comercial"]
    h_a1 = auth_headers["a1"]
    h_a2 = auth_headers["a2"]
    h_admin = auth_headers["admin"]
    body = _assinar_contrato(client, h_com)
    tid = body["implantacao_ticket_id"]

    assert client.get(f"/v1/tickets/{tid}/checklist", headers=h_a2).status_code == 403
    assert client.get(f"/v1/tickets/{tid}/checklist", headers=h_com).status_code == 403

    chk = client.get(f"/v1/tickets/{tid}/checklist", headers=h_a1)
    assert chk.status_code == 200, chk.text
    item = chk.json()["itens"][0]
    patched = client.patch(
        f"/v1/tickets/{tid}/checklist/itens/{item['id']}",
        headers=h_a1,
        json={"concluido": True, "observacao": "ok"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["itens"][0]["concluido"] is True
    assert patched.json()["progresso_pct"] > 0

    fechado = db_session.query(StatusTicket).filter(StatusTicket.slug == "fechado").first()
    if not fechado:
        fechado = StatusTicket(nome="Fechado", slug="fechado", ordem=99, ativo=True)
        db_session.add(fechado)
        db_session.commit()
        db_session.refresh(fechado)

    close = client.patch(
        f"/v1/tickets/{tid}",
        headers=h_admin,
        json={"status_id": fechado.id},
    )
    assert close.status_code == 400, close.text
    assert "obrigatório" in close.json()["detail"].lower() or "implantação" in close.json()["detail"].lower()

    for it in patched.json()["itens"]:
        if it["obrigatorio"] and not it["concluido"]:
            r = client.patch(
                f"/v1/tickets/{tid}/checklist/itens/{it['id']}",
                headers=h_admin,
                json={"concluido": True},
            )
            assert r.status_code == 200, r.text

    chk2 = client.get(f"/v1/tickets/{tid}/checklist", headers=h_admin).json()
    assert chk2["itens_obrigatorios_pendentes"] == 0
    assert "cadastrar_pdvs" in {i.get("chave") for i in chk2["itens"]}
    # A abertura do ticket cria os stubs de PDV da linha do contrato (#1323).
    assert chk2["pdvs_necessarios"] == 1
    assert chk2["pdvs_ativos"] == 1

    nat = TicketNatureza(nome="Implantação", slug="implantacao_test", ordem=80, ativo=True)
    db_session.add(nat)
    db_session.flush()
    motivo = TicketMotivo(natureza_id=nat.id, nome="Go-live", slug="go_live", ordem=1, ativo=True)
    db_session.add(motivo)
    db_session.commit()
    db_session.refresh(motivo)

    ok_close = client.patch(
        f"/v1/tickets/{tid}",
        headers=h_admin,
        json={"status_id": fechado.id, "motivo_id": motivo.id},
    )
    assert ok_close.status_code == 200, ok_close.text
    assert ok_close.json()["fechado_em"]

    item_id = chk2["itens"][0]["id"]
    assert (
        client.patch(
            f"/v1/tickets/{tid}/checklist/itens/{item_id}",
            headers=h_a1,
            json={"observacao": "depois de fechar"},
        ).status_code
        == 403
    )
    admin_patch = client.patch(
        f"/v1/tickets/{tid}/checklist/itens/{item_id}",
        headers=h_admin,
        json={"observacao": "ajuste admin"},
    )
    assert admin_patch.status_code == 200, admin_patch.text
    marcado = next(i for i in admin_patch.json()["itens"] if i["id"] == item_id)
    assert marcado["observacao"] == "ajuste admin"


def test_abertura_cria_stubs_pdv_e_move_funil(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_a1 = auth_headers["a1"]
    h_admin = auth_headers["admin"]
    body = _assinar_contrato(client, h_com)
    tid = body["implantacao_ticket_id"]
    emp_id = body["empresa_id"]

    chk = client.get(f"/v1/tickets/{tid}/checklist", headers=h_a1)
    assert chk.status_code == 200, chk.text
    assert chk.json()["pdvs_necessarios"] == 1
    assert chk.json()["pdvs_ativos"] == 1

    pdvs = client.get(f"/v1/empresas/{emp_id}/pdvs", headers=h_admin)
    assert pdvs.status_code == 200, pdvs.text
    assert "PDV-1" in {p["codigo"] for p in pdvs.json()["items"]}

    neg = client.get(f"/v1/crm/negociacoes/{body['negociacao_id']}", headers=h_com)
    assert neg.status_code == 200
    assert neg.json()["estagio_slug"] == "implantacao"


def test_item_cadastrar_pdvs_exige_cadastro_ou_desvio(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_a1 = auth_headers["a1"]

    neg_id, linha = _negociacao_com_linha(client, h_com)
    c = client.post("/v1/comercial/contratos", headers=h_com, json={"linha_id": linha["id"]})
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    _anexar_pdf_assinado(client, h_com, cid)
    ass = client.post(
        f"/v1/comercial/contratos/{cid}/marcar-assinado",
        headers=h_com,
        json={"abrir_ticket_implantacao": True},
    )
    assert ass.status_code == 200, ass.text
    tid = ass.json()["implantacao_ticket_id"]

    # A implantação descobre que o cliente tem 2 PDVs: a linha passa a exigir 2.
    up = client.patch(
        f"/v1/crm/negociacoes/{neg_id}/linhas/{linha['id']}",
        headers=h_com,
        json={"quantidade_pdvs": 2},
    )
    assert up.status_code == 200, up.text

    chk = client.get(f"/v1/tickets/{tid}/checklist", headers=h_a1).json()
    assert chk["pdvs_necessarios"] == 2
    assert chk["pdvs_ativos"] == 1
    item = next(i for i in chk["itens"] if i.get("chave") == "cadastrar_pdvs")

    sem_desvio = client.patch(
        f"/v1/tickets/{tid}/checklist/itens/{item['id']}",
        headers=h_a1,
        json={"concluido": True},
    )
    assert sem_desvio.status_code == 400, sem_desvio.text
    assert "PDV" in sem_desvio.json()["detail"]

    com_desvio = client.patch(
        f"/v1/tickets/{tid}/checklist/itens/{item['id']}",
        headers=h_a1,
        json={"concluido": True, "observacao": "Cliente tem 1 PDV; o 2º entra no próximo mês."},
    )
    assert com_desvio.status_code == 200, com_desvio.text


def test_portal_nao_ve_ticket_de_implantacao(client, db_session, seed_base, auth_headers):
    from tests.test_portal_cliente import _criar_funcionario, _portal_headers

    h_com = auth_headers["comercial"]
    body = _assinar_contrato(client, h_com)
    tid = body["implantacao_ticket_id"]

    supervisor = _criar_funcionario(db_session, seed_base, tipo="supervisor", email="impl.sup@example.com")
    socio = _criar_funcionario(db_session, seed_base, tipo="socio", email="impl.so@example.com")

    ids_sup = {
        x["id"] for x in client.get("/v1/portal/tickets", headers=_portal_headers(supervisor)).json()["items"]
    }
    assert tid not in ids_sup
    assert client.get(f"/v1/portal/tickets/{tid}", headers=_portal_headers(supervisor)).status_code == 404
    assert client.get(f"/v1/portal/tickets/{tid}", headers=_portal_headers(socio)).status_code == 404
