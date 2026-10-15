import pytest

from app.models import Empresa, Rede, Ticket
from app.models.empresa_pdv import EmpresaPdv, PdvRotulo, PdvTipoAcessoRemoto
from app.services.empresa_pdv_rules import validar_papel_principal_auxiliar
from app.services.secret_box import decrypt_str, encrypt_str


@pytest.fixture
def pdv_catalogo(db_session):
    rot = PdvRotulo(nome="Caixa", ativo=True, ordem_exibicao=1)
    tipo = PdvTipoAcessoRemoto(nome="AnyDesk", ativo=True, ordem_exibicao=1)
    db_session.add_all([rot, tipo])
    db_session.commit()
    return {"rotulo": rot, "tipo": tipo}


def test_validacao_auxiliar_exige_principal(db_session, seed_base, pdv_catalogo):
    emp = seed_base["empresa"]
    db_session.add(
        EmpresaPdv(
            empresa_id=emp.id,
            codigo="001",
            rotulo_id=pdv_catalogo["rotulo"].id,
            papel="auxiliar",
            ativo=True,
        )
    )
    db_session.commit()
    with pytest.raises(ValueError, match="principal"):
        validar_papel_principal_auxiliar(db_session, emp.id)


def test_principal_e_auxiliar_ok(db_session, seed_base, pdv_catalogo):
    emp = seed_base["empresa"]
    db_session.add_all(
        [
            EmpresaPdv(
                empresa_id=emp.id,
                codigo="001",
                rotulo_id=pdv_catalogo["rotulo"].id,
                papel="principal",
                ativo=True,
            ),
            EmpresaPdv(
                empresa_id=emp.id,
                codigo="002",
                rotulo_id=pdv_catalogo["rotulo"].id,
                papel="auxiliar",
                ativo=True,
            ),
        ]
    )
    db_session.commit()
    validar_papel_principal_auxiliar(db_session, emp.id)


def test_ver_empresa_nao_libera_pdv_e_atendimento_ve(client, auth_headers, seed_base, pdv_catalogo, db_session):
    emp = seed_base["empresa"]
    criado = client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "009",
            "rotulo_id": pdv_catalogo["rotulo"].id,
            "papel": "principal",
            "acesso_remoto_id": "123456789",
            "acesso_remoto_senha": "senha-do-posto",
        },
    )
    assert criado.status_code == 201, criado.text
    pdv_id = criado.json()["id"]

    def atribuir(codigos: list[str], nome: str) -> None:
        grupo = client.post(
            "/v1/permissao-grupos",
            headers=auth_headers["admin"],
            json={"nome": nome, "permissoes": codigos},
        )
        assert grupo.status_code == 201, grupo.text
        patch = client.patch(
            f"/v1/atendentes/{seed_base['a1'].id}",
            headers=auth_headers["admin"],
            json={"grupo_ids": [grupo.json()["id"]]},
        )
        assert patch.status_code == 200, patch.text

    h = auth_headers["a1"]
    atribuir(["empresas.ver"], "Só empresa")
    assert client.get(f"/v1/empresas/{emp.id}/pdvs", headers=h).status_code == 403
    assert client.get(f"/v1/empresas/{emp.id}/pdvs/{pdv_id}/credencial", headers=h).status_code == 403

    atribuir(["operacional"], "Atendimento vê PDV")
    assert client.get(f"/v1/empresas/{emp.id}/pdvs", headers=h).status_code == 404
    assert client.get(f"/v1/empresas/{emp.id}/pdvs/{pdv_id}/credencial", headers=h).status_code == 404

    db_session.add(
        Ticket(
            tenant_id=1,
            protocolo="T-PDV-ESCOPO",
            empresa_id=emp.id,
            rede_id=emp.rede_id,
            setor_id=seed_base["setor1"].id,
            status_id=seed_base["status"].id,
            assunto="Acesso remoto",
        )
    )
    rede_fora = Rede(tenant_id=1, nome="Rede sem ticket", ativo=True)
    db_session.add(rede_fora)
    db_session.flush()
    fora = Empresa(tenant_id=1, rede_id=rede_fora.id, nome="Posto de outra rede", ativo=True)
    db_session.add(fora)
    db_session.commit()
    criado_fora = client.post(
        f"/v1/empresas/{fora.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "001",
            "rotulo_id": pdv_catalogo["rotulo"].id,
            "papel": "principal",
            "acesso_remoto_id": "999",
            "acesso_remoto_senha": "nao-deve-vazar",
        },
    )
    assert criado_fora.status_code == 201, criado_fora.text

    lista = client.get(f"/v1/empresas/{emp.id}/pdvs", headers=h)
    assert lista.status_code == 200, lista.text
    assert lista.json()["empresa_nome"] == emp.nome
    assert lista.json()["items"][0]["acesso_remoto_id"] == "123456789"
    cred = client.get(f"/v1/empresas/{emp.id}/pdvs/{pdv_id}/credencial", headers=h)
    assert cred.status_code == 200, cred.text
    assert cred.json()["acesso_remoto_senha"] == "senha-do-posto"
    assert client.get(f"/v1/empresas/{fora.id}/pdvs", headers=h).status_code == 404
    assert (
        client.get(
            f"/v1/empresas/{fora.id}/pdvs/{criado_fora.json()['id']}/credencial",
            headers=h,
        ).status_code
        == 404
    )
    assert client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=h,
        json={"codigo": "010", "rotulo_id": pdv_catalogo["rotulo"].id, "papel": "auxiliar"},
    ).status_code == 403


def test_criptografia_senha_pdv():
    raw = "senha-secreta-123"
    cifrada = encrypt_str(raw)
    assert cifrada != raw
    assert decrypt_str(cifrada) == raw


def test_api_listar_pdvs_sem_senha(client, auth_headers, seed_base, pdv_catalogo):
    emp = seed_base["empresa"]
    client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "001",
            "rotulo_id": pdv_catalogo["rotulo"].id,
            "papel": "principal",
            "acesso_remoto_senha": "minha-senha",
        },
    )
    r = client.get(f"/v1/empresas/{emp.id}/pdvs", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["tem_senha_remota"] is True
    assert "acesso_remoto_senha" not in item


def test_api_revelar_credencial_admin(client, auth_headers, seed_base, pdv_catalogo):
    emp = seed_base["empresa"]
    criado = client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "002",
            "rotulo_id": pdv_catalogo["rotulo"].id,
            "papel": "principal",
            "acesso_remoto_senha": "revelar-me",
        },
    )
    pdv_id = criado.json()["id"]
    r = client.get(f"/v1/empresas/{emp.id}/pdvs/{pdv_id}/credencial", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert r.json()["acesso_remoto_senha"] == "revelar-me"


def test_api_atualizar_codigo_pdv(client, auth_headers, seed_base, pdv_catalogo):
    emp = seed_base["empresa"]
    criado = client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "001",
            "rotulo_id": pdv_catalogo["rotulo"].id,
            "papel": "principal",
        },
    )
    assert criado.status_code == 201, criado.text
    pdv_id = criado.json()["id"]

    r = client.patch(
        f"/v1/empresas/{emp.id}/pdvs/{pdv_id}",
        headers=auth_headers["admin"],
        json={"codigo": "010"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["codigo"] == "010"

    client.post(
        f"/v1/empresas/{emp.id}/pdvs",
        headers=auth_headers["admin"],
        json={
            "codigo": "002",
            "rotulo_id": pdv_catalogo["rotulo"].id,
            "papel": "auxiliar",
        },
    )
    conflito = client.patch(
        f"/v1/empresas/{emp.id}/pdvs/{pdv_id}",
        headers=auth_headers["admin"],
        json={"codigo": "002"},
    )
    assert conflito.status_code == 400
    assert "código" in conflito.json()["detail"].lower()
