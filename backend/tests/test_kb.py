"""Base de conhecimento (#293, #294)."""

from __future__ import annotations

from app.models import AuditLog, KbArticle, KbArticleVersion, KbCategory


def test_kb_categoria_artigo_crud_publish(client, auth_headers, db_session):
    r = client.post(
        "/v1/kb/categories",
        headers=auth_headers["admin"],
        json={"nome": "Operação", "ordem": 1},
    )
    assert r.status_code == 201, r.text
    cat = r.json()

    r = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={
            "titulo": "Como abrir ticket",
            "category_id": cat["id"],
            "conteudo_markdown": "# Passo a passo\n\n1. Clique em novo ticket.",
        },
    )
    assert r.status_code == 201, r.text
    art = r.json()
    assert art["status"] == "rascunho"

    r = client.post(f"/v1/kb/articles/{art['id']}/publish", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "publicado"

    r = client.get("/v1/kb/articles/consulta", headers=auth_headers["a1"], params={"busca": "ticket"})
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r = client.get(f"/v1/kb/articles/publicados/{art['id']}", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert "Passo a passo" in r.json()["conteudo_markdown"]

    r_draft = client.get("/v1/kb/articles/consulta", headers=auth_headers["a1"], params={"busca": "rascunho"})
    assert all(item["status"] == "publicado" for item in r_draft.json())

    versao = db_session.query(KbArticleVersion).filter(KbArticleVersion.article_id == art["id"]).count()
    assert versao >= 2

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "kb_article", AuditLog.action == "publish")
        .first()
    )
    assert audit is not None


def test_kb_rascunho_invisivel_consulta(client, auth_headers, db_session):
    r = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Somente rascunho interno", "conteudo_markdown": "secreto"},
    )
    assert r.status_code == 201
    art_id = r.json()["id"]

    r = client.get("/v1/kb/articles/publicados/{0}".format(art_id), headers=auth_headers["a1"])
    assert r.status_code == 404


def test_kb_excluir_categoria_desvincula_artigos(client, auth_headers, db_session):
    cat = client.post("/v1/kb/categories", headers=auth_headers["admin"], json={"nome": "Temp"}).json()
    art = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Art", "category_id": cat["id"], "conteudo_markdown": "x"},
    ).json()
    r = client.delete(f"/v1/kb/categories/{cat['id']}", headers=auth_headers["admin"])
    assert r.status_code == 204
    row = db_session.query(KbArticle).filter(KbArticle.id == art["id"]).first()
    assert row.category_id is None


def test_atendente_403_kb_admin(client, auth_headers):
    r = client.get("/v1/kb/articles", headers=auth_headers["a1"])
    assert r.status_code == 403
