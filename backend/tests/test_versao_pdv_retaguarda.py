import pytest

from app.config import settings
from app.models.empresa_pdv import EmpresaPdv, PdvRotulo, PdvTipoAcessoRemoto
from app.models.rustdesk_peer import RustdeskPeer
from app.services import rustdesk_peers as rustdesk_svc


@pytest.fixture(autouse=True)
def _agente_desligado(monkeypatch):
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_URL", None)
    monkeypatch.setattr(settings, "RUSTDESK_AGENT_TOKEN", None)
    monkeypatch.setattr(rustdesk_svc, "_ultimo_sync_mono", 0.0)


def test_empresa_e_rede_guardam_versao(client, auth_headers, seed_base):
    emp = seed_base["empresa"]
    rede = seed_base["rede"]
    h = auth_headers["admin"]

    r = client.patch(f"/v1/redes/{rede.id}", headers=h, json={"versao_retaguarda": "  8.1  "})
    assert r.status_code == 200, r.text
    assert r.json()["versao_retaguarda"] == "8.1"

    e = client.patch(f"/v1/empresas/{emp.id}", headers=h, json={"versao_pdv": "4.2.1"})
    assert e.status_code == 200, e.text
    assert e.json()["versao_pdv"] == "4.2.1"

    lista = client.get("/v1/redes", headers=h)
    assert lista.status_code == 200, lista.text
    item = next(x for x in lista.json()["items"] if x["id"] == rede.id)
    assert item["versao_retaguarda"] == "8.1"

    vazio = client.patch(f"/v1/empresas/{emp.id}", headers=h, json={"versao_pdv": "   "})
    assert vazio.status_code == 200, vazio.text
    assert vazio.json()["versao_pdv"] is None

    login = client.patch(
        f"/v1/redes/{rede.id}",
        headers=h,
        json={"login_retaguarda": "  duplex  "},
    )
    assert login.status_code == 200, login.text
    assert login.json()["login_retaguarda"] == "  duplex  "


def test_versao_acima_do_limite_e_sem_permissao(client, auth_headers, seed_base):
    emp = seed_base["empresa"]
    rede = seed_base["rede"]
    h = auth_headers["admin"]
    longo = "x" * 81

    pdv = client.patch(f"/v1/empresas/{emp.id}", headers=h, json={"versao_pdv": longo})
    assert pdv.status_code == 422, pdv.text

    ret = client.patch(f"/v1/redes/{rede.id}", headers=h, json={"versao_retaguarda": longo})
    assert ret.status_code == 422, ret.text

    a1 = auth_headers["a1"]
    assert (
        client.patch(f"/v1/empresas/{emp.id}", headers=a1, json={"versao_pdv": "1.0"}).status_code
        == 403
    )
    assert (
        client.patch(
            f"/v1/redes/{rede.id}", headers=a1, json={"versao_retaguarda": "1.0"}
        ).status_code
        == 403
    )
    assert client.patch("/v1/empresas/999999", headers=h, json={"versao_pdv": "1.0"}).status_code == 404
    assert client.patch("/v1/redes/999999", headers=h, json={"versao_retaguarda": "1.0"}).status_code == 404


def test_ticket_pdvs_e_acesso_remoto_mostram_versao(client, auth_headers, seed_base, db_session):
    emp = seed_base["empresa"]
    rede = seed_base["rede"]
    h = auth_headers["admin"]
    emp.versao_pdv = "10.0.2"
    rede.versao_retaguarda = "2024.08"
    rot = PdvRotulo(nome="Caixa", ativo=True, ordem_exibicao=1)
    tipo = PdvTipoAcessoRemoto(nome="DeskRudder", ativo=True, ordem_exibicao=1)
    db_session.add_all([rot, tipo])
    db_session.flush()
    db_session.add(
        EmpresaPdv(
            empresa_id=emp.id,
            codigo="001",
            rotulo_id=rot.id,
            papel="principal",
            tipo_acesso_remoto_id=tipo.id,
            acesso_remoto_id="123456789",
            ativo=True,
        )
    )
    db_session.add(RustdeskPeer(rustdesk_id="123456789", ip="10.1.1.1"))
    db_session.commit()

    ticket = client.post(
        "/v1/tickets",
        headers=h,
        json={"empresa_id": emp.id, "setor_id": seed_base["setor1"].id, "assunto": "PDV lento"},
    )
    assert ticket.status_code == 201, ticket.text
    corpo = ticket.json()
    assert corpo["versao_pdv"] == "10.0.2"
    assert corpo["versao_retaguarda"] == "2024.08"

    detalhe = client.get(f"/v1/tickets/{corpo['id']}", headers=h)
    assert detalhe.status_code == 200, detalhe.text
    assert detalhe.json()["versao_pdv"] == "10.0.2"
    assert detalhe.json()["versao_retaguarda"] == "2024.08"

    coord = client.post(
        "/v1/tickets",
        headers=h,
        json={"rede_id": rede.id, "setor_id": seed_base["setor1"].id, "assunto": "Comunicado da rede"},
    )
    assert coord.status_code == 201, coord.text
    assert coord.json()["versao_pdv"] is None
    assert coord.json()["versao_retaguarda"] == "2024.08"

    pdvs = client.get(f"/v1/empresas/{emp.id}/pdvs", headers=h)
    assert pdvs.status_code == 200, pdvs.text
    assert pdvs.json()["versao_pdv"] == "10.0.2"

    frota = client.get("/v1/rustdesk/peers", headers=h)
    assert frota.status_code == 200, frota.text
    ligado = next(x for x in frota.json()["items"] if x["rustdesk_id"] == "123456789")
    assert {v["versao_pdv"] for v in ligado["vinculos"]} == {"10.0.2"}
