import pytest

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
