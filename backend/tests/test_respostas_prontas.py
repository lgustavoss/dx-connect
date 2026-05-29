"""Respostas prontas (#113)."""

from app.models.resposta_pronta import RespostaPronta


def test_admin_crud_e_disponiveis(client, auth_headers, seed_base):
    create = client.post(
        "/v1/respostas-prontas",
        headers=auth_headers["admin"],
        json={
            "titulo": "Pedir versão",
            "corpo": "Por favor informe a versão do sistema.",
            "setor_id": None,
            "ordem": 1,
            "ativo": True,
        },
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]

    setor = client.post(
        "/v1/respostas-prontas",
        headers=auth_headers["admin"],
        json={
            "titulo": "Suporte NF",
            "corpo": "Envie o XML da nota fiscal.",
            "setor_id": seed_base["setor1"].id,
            "ordem": 2,
            "ativo": True,
        },
    )
    assert setor.status_code == 201

    lista = client.get("/v1/respostas-prontas", headers=auth_headers["admin"])
    assert lista.status_code == 200
    assert lista.json()["total"] >= 2

    disp = client.get(
        f"/v1/respostas-prontas/disponiveis?setor_id={seed_base['setor1'].id}",
        headers=auth_headers["admin"],
    )
    assert disp.status_code == 200
    titulos = {r["titulo"] for r in disp.json()}
    assert "Pedir versão" in titulos
    assert "Suporte NF" in titulos

    outro = client.get(
        f"/v1/respostas-prontas/disponiveis?setor_id={seed_base['setor2'].id}",
        headers=auth_headers["admin"],
    )
    assert outro.status_code == 200
    titulos2 = {r["titulo"] for r in outro.json()}
    assert "Pedir versão" in titulos2
    assert "Suporte NF" not in titulos2

    patch = client.patch(
        f"/v1/respostas-prontas/{rid}",
        headers=auth_headers["admin"],
        json={"corpo": "Informe versão e build."},
    )
    assert patch.status_code == 200
    assert patch.json()["corpo"] == "Informe versão e build."

    delete = client.delete(f"/v1/respostas-prontas/{rid}", headers=auth_headers["admin"])
    assert delete.status_code == 204


def test_disponiveis_respeita_ativo(client, auth_headers, seed_base, db_session):
    row = RespostaPronta(
        tenant_id=seed_base["tenant"].id,
        setor_id=None,
        titulo="Inativa",
        corpo="Não deve aparecer",
        ordem=0,
        ativo=False,
    )
    db_session.add(row)
    db_session.commit()

    res = client.get(
        f"/v1/respostas-prontas/disponiveis?setor_id={seed_base['setor1'].id}",
        headers=auth_headers["admin"],
    )
    assert res.status_code == 200
    assert all(r["titulo"] != "Inativa" for r in res.json())
