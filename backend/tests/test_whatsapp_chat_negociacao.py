"""Vínculo do chat com a negociação do CRM (#1182 / #S202610-0006)."""

from tests.test_comercial_contrato import DADOS_FISCAIS_OK
from tests.test_whatsapp_chats import _chat_ativo


def _negociacao_aberta(client, h, *, nome: str = "Posto Sem CNPJ") -> tuple[int, int]:
    lead = client.post("/v1/crm/leads", headers=h, json={"nome": nome, "telefone": "11988887777"})
    assert lead.status_code == 201, lead.text
    neg_id = lead.json()["negociacao_ativa_id"]
    base = client.patch(
        f"/v1/crm/negociacoes/{neg_id}",
        headers=h,
        json={"nome_base_webposto": "Rede Sem Cnpj"},
    )
    assert base.status_code == 200, base.text
    linha = client.post(
        f"/v1/crm/negociacoes/{neg_id}/linhas",
        headers=h,
        json={
            "razao_social": "Posto Sem CNPJ LTDA",
            "cnpj": "12.345.678/0001-95",
            "valor_negociado": "100.00",
            "item_ids": [],
        },
    )
    assert linha.status_code == 201, linha.text
    return neg_id, linha.json()["id"]


def test_vincula_chat_a_negociacao_aberta(client, seed_base, auth_headers):
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511988776655", msg_id="crm-vinc-1")
    neg_id, _linha = _negociacao_aberta(client, auth_headers["admin"])

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-negociacao",
        headers=auth_headers["admin"],
        json={"negociacao_id": neg_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["negociacao_id"] == neg_id
    assert body["negociacao_lead_nome"] == "Posto Sem CNPJ"
    assert body["funcionario_rede_id"] is None

    detalhe = client.get(f"/v1/crm/negociacoes/{neg_id}", headers=auth_headers["admin"])
    assert detalhe.status_code == 200
    assert [c["id"] for c in detalhe.json()["chats"]] == [cid]


def test_atendente_sem_crm_nao_vincula(client, seed_base, auth_headers):
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511988776656", msg_id="crm-vinc-2")
    neg_id, _linha = _negociacao_aberta(client, auth_headers["admin"], nome="Outro Posto")
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-negociacao",
        headers=auth_headers["a1"],
        json={"negociacao_id": neg_id},
    )
    assert r.status_code == 403


def test_recusa_negociacao_perdida(client, seed_base, auth_headers):
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511988776657", msg_id="crm-vinc-3")
    neg_id, _linha = _negociacao_aberta(client, auth_headers["admin"], nome="Posto Perdido")
    mov = client.post(
        f"/v1/crm/negociacoes/{neg_id}/mover-estagio",
        headers=auth_headers["admin"],
        json={"estagio_slug": "perdido"},
    )
    assert mov.status_code == 200, mov.text
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-negociacao",
        headers=auth_headers["admin"],
        json={"negociacao_id": neg_id},
    )
    assert r.status_code == 400
    assert "aberto" in r.json()["detail"].lower()


def test_empresa_unica_repassa_contato(client, seed_base, auth_headers, monkeypatch):
    emitidos: list[int] = []

    def _registrar(db, chat, *, estado_anterior=None):
        emitidos.append(chat.id)

    monkeypatch.setattr("app.services.realtime_emit.emit_chat_fila_from_model", _registrar)
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511988776658", msg_id="crm-vinc-4")
    neg_id, linha_id = _negociacao_aberta(client, auth_headers["admin"], nome="Posto Que Fecha")
    vinc = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-negociacao",
        headers=auth_headers["admin"],
        json={"negociacao_id": neg_id},
    )
    assert vinc.status_code == 200, vinc.text

    emp = client.put(
        f"/v1/comercial/contratos/linhas/{linha_id}/empresa",
        headers=auth_headers["admin"],
        json=DADOS_FISCAIS_OK,
    )
    assert emp.status_code == 200, emp.text

    chat = client.get(f"/v1/whatsapp/chats/{cid}", headers=auth_headers["admin"])
    assert chat.status_code == 200
    body = chat.json()
    assert body["empresa_id"] == emp.json()["id"]
    assert body["funcionario_rede_id"]
    assert body["negociacao_id"] == neg_id
    assert cid in emitidos


def test_duas_empresas_nao_escolhem_sozinhas(client, seed_base, auth_headers, db_session):
    from app.models.crm import CrmNegociacaoCnpjLinha
    from app.models.empresa import Empresa
    from app.models.whatsapp_chat import WhatsappChat
    from app.services.whatsapp_chat_negociacao import repassar_chats_da_negociacao

    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511988776659", msg_id="crm-vinc-5")
    neg_id, linha_id = _negociacao_aberta(client, auth_headers["admin"], nome="Posto Duas")
    vinc = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-negociacao",
        headers=auth_headers["admin"],
        json={"negociacao_id": neg_id},
    )
    assert vinc.status_code == 200, vinc.text

    emp_a = seed_base["empresa"]
    emp_b = Empresa(tenant_id=emp_a.tenant_id, rede_id=emp_a.rede_id, nome="Segunda Empresa", ativo=True)
    db_session.add(emp_b)
    db_session.flush()
    linha = db_session.get(CrmNegociacaoCnpjLinha, linha_id)
    linha.empresa_id = emp_a.id
    db_session.add(
        CrmNegociacaoCnpjLinha(
            negociacao_id=neg_id,
            empresa_id=emp_b.id,
            razao_social="Segunda",
            valor_negociado=0,
            item_ids=[],
            ordem=1,
        )
    )
    db_session.flush()
    repassar_chats_da_negociacao(db_session, neg_id, seed_base["admin"])
    chat = db_session.get(WhatsappChat, cid)
    assert chat.empresa_id is None
    assert chat.funcionario_rede_id is None
    assert chat.negociacao_id == neg_id
