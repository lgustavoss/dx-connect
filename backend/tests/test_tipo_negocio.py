from app.models import TipoNegocio


def test_desativar_tipo_negocio_em_uso_retorna_409(client, auth_headers, seed_base, db_session):
    tipo = TipoNegocio(nome="Posto", ativo=True)
    db_session.add(tipo)
    db_session.flush()
    emp = seed_base["empresa"]
    emp.tipo_negocio_id = tipo.id
    db_session.commit()

    r = client.patch(
        f"/v1/tipos-negocio/{tipo.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert r.status_code == 409, r.text
    assert "1 empresa ativa" in r.json()["detail"]
    db_session.refresh(tipo)
    assert tipo.ativo is True


def test_desativar_tipo_negocio_so_empresa_inativa_ok(client, auth_headers, seed_base, db_session):
    tipo = TipoNegocio(nome="Revenda", ativo=True)
    db_session.add(tipo)
    db_session.flush()
    emp = seed_base["empresa"]
    emp.tipo_negocio_id = tipo.id
    emp.ativo = False
    db_session.commit()

    r = client.patch(
        f"/v1/tipos-negocio/{tipo.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ativo"] is False


def test_desativar_tipo_negocio_sem_empresa_ok(client, auth_headers, db_session):
    tipo = TipoNegocio(nome="Conveniência", ativo=True)
    db_session.add(tipo)
    db_session.commit()

    r = client.patch(
        f"/v1/tipos-negocio/{tipo.id}",
        headers=auth_headers["admin"],
        json={"ativo": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ativo"] is False
