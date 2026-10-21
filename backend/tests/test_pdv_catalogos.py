import pytest

from app.models.empresa_pdv import EmpresaPdv, EmpresaPdvAcessoRemoto, PdvRotulo, PdvTipoAcessoRemoto


@pytest.fixture
def rotulo_caixa(db_session):
    rot = PdvRotulo(nome="Caixa", ativo=True, ordem_exibicao=1)
    db_session.add(rot)
    db_session.commit()
    return rot


def test_desativar_rotulo_em_uso_retorna_409(client, auth_headers, seed_base, rotulo_caixa, db_session):
    emp = seed_base["empresa"]
    db_session.add(
        EmpresaPdv(
            empresa_id=emp.id,
            codigo="001",
            rotulo_id=rotulo_caixa.id,
            papel="principal",
            ativo=True,
        )
    )
    db_session.add(
        EmpresaPdv(
            empresa_id=emp.id,
            codigo="002",
            rotulo_id=rotulo_caixa.id,
            papel="auxiliar",
            ativo=False,
        )
    )
    db_session.commit()

    r = client.patch(
        f"/v1/pdv-rotulos/{rotulo_caixa.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert r.status_code == 409, r.text
    assert "2 PDVs" in r.json()["detail"]
    db_session.refresh(rotulo_caixa)
    assert rotulo_caixa.ativo is True


def test_desativar_rotulo_sem_pdv_ok(client, auth_headers, rotulo_caixa, db_session):
    r = client.patch(
        f"/v1/pdv-rotulos/{rotulo_caixa.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ativo"] is False
    db_session.refresh(rotulo_caixa)
    assert rotulo_caixa.ativo is False


def test_renomear_rotulo_em_uso_ok(client, auth_headers, seed_base, rotulo_caixa, db_session):
    emp = seed_base["empresa"]
    db_session.add(
        EmpresaPdv(
            empresa_id=emp.id,
            codigo="001",
            rotulo_id=rotulo_caixa.id,
            papel="principal",
            ativo=True,
        )
    )
    db_session.commit()

    r = client.patch(
        f"/v1/pdv-rotulos/{rotulo_caixa.id}",
        headers=auth_headers["admin"],
        json={"nome": "Caixa principal"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "Caixa principal"
    assert r.json()["ativo"] is True


def test_criar_pdv_recusa_rotulo_inativo(client, auth_headers, seed_base, rotulo_caixa):
    desliga = client.patch(
        f"/v1/pdv-rotulos/{rotulo_caixa.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert desliga.status_code == 200, desliga.text

    r = client.post(
        f"/v1/empresas/{seed_base['empresa'].id}/pdvs",
        headers=auth_headers["admin"],
        json={"codigo": "009", "rotulo_id": rotulo_caixa.id, "papel": "principal"},
    )
    assert r.status_code == 400, r.text
    assert "inativo" in r.json()["detail"].lower()


@pytest.fixture
def tipo_anydesk(db_session):
    tipo = PdvTipoAcessoRemoto(nome="AnyDesk", ativo=True, ordem_exibicao=1)
    db_session.add(tipo)
    db_session.commit()
    return tipo


def test_desativar_tipo_acesso_em_uso_retorna_409(client, auth_headers, seed_base, rotulo_caixa, tipo_anydesk, db_session):
    emp = seed_base["empresa"]
    pdv = EmpresaPdv(
        empresa_id=emp.id,
        codigo="001",
        rotulo_id=rotulo_caixa.id,
        papel="principal",
        ativo=True,
        tipo_acesso_remoto_id=tipo_anydesk.id,
    )
    db_session.add(pdv)
    db_session.flush()
    db_session.add(
        EmpresaPdvAcessoRemoto(
            pdv_id=pdv.id,
            tipo_acesso_remoto_id=tipo_anydesk.id,
            ordem_exibicao=0,
        )
    )
    db_session.commit()

    r = client.patch(
        f"/v1/pdv-tipos-acesso-remoto/{tipo_anydesk.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert r.status_code == 409, r.text
    assert "1 PDV" in r.json()["detail"]
    db_session.refresh(tipo_anydesk)
    assert tipo_anydesk.ativo is True


def test_desativar_tipo_acesso_sem_pdv_ok(client, auth_headers, tipo_anydesk, db_session):
    r = client.patch(
        f"/v1/pdv-tipos-acesso-remoto/{tipo_anydesk.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ativo"] is False
    db_session.refresh(tipo_anydesk)
    assert tipo_anydesk.ativo is False
