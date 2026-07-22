"""Testes de similaridade de nome (#593)."""

from __future__ import annotations

from app.services.funcionario_nome_similar import (
    LIMIAR_SIMILARIDADE,
    normalizar_nome,
    ranquear_similares,
    score_nomes,
)


def test_normalizar_remove_acentos():
    assert normalizar_nome("Luís Gustavo") == "luis gustavo"
    assert normalizar_nome("  Maria   Silva ") == "maria silva"


def test_score_acentos_e_typo_leve():
    assert score_nomes("Luis Gustavo", "Luís Gustavo") >= LIMIAR_SIMILARIDADE
    assert score_nomes("Maria Silva", "Maria Silvs") >= LIMIAR_SIMILARIDADE
    assert score_nomes("João Pedro", "Carlos Alberto") < LIMIAR_SIMILARIDADE


def test_ranquear_top_e_limiar():
    candidatos = [
        (1, "Luis Gustavo Santos"),
        (2, "Luís Gustavo"),
        (3, "Ana Paula"),
        (4, "Carlos"),
    ]
    ranked = ranquear_similares("Luis Gustavo", candidatos, limit=5)
    ids = [r[0] for r in ranked]
    assert 2 in ids
    assert 1 in ids
    assert 3 not in ids
    assert ranked[0][2] >= ranked[-1][2]


def test_api_similares_whatsapp(client, seed_base, auth_headers, db_session):
    from app.models.funcionario_rede import FuncionarioRede
    from tests.test_whatsapp_chats import _criar_funcionario_colaborador

    func = _criar_funcionario_colaborador(
        db_session,
        seed_base,
        nome="Luís Gustavo",
        email="luis.g@test.local",
    )
    inativo = _criar_funcionario_colaborador(
        db_session,
        seed_base,
        nome="Luis Gustavo Inativo",
        email="luis.inativo@test.local",
    )
    row = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == inativo["id"]).first()
    assert row is not None
    row.ativo = False
    db_session.commit()

    r = client.get(
        "/v1/whatsapp/chats/funcionarios/similares?nome=Luis%20Gustavo",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    ids = [x["id"] for x in rows]
    assert func["id"] in ids
    assert inativo["id"] not in ids
    hit = next(x for x in rows if x["id"] == func["id"])
    assert hit["similaridade"] is not None
    assert hit["similaridade"] >= LIMIAR_SIMILARIDADE
    assert hit["rede_nome"] == seed_base["rede"].nome

    distinto = client.get(
        "/v1/whatsapp/chats/funcionarios/similares?nome=Zzzzz%20Xxxxx",
        headers=auth_headers["a1"],
    )
    assert distinto.status_code == 200
    assert distinto.json() == []
