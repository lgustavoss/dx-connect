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


def test_kb_api_publica_sem_auth(client, auth_headers, db_session):
    cat = client.post("/v1/kb/categories", headers=auth_headers["admin"], json={"nome": "Público", "ordem": 0}).json()
    art = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={
            "titulo": "Manual visível",
            "category_id": cat["id"],
            "conteudo_markdown": "Conteúdo público de teste",
        },
    ).json()
    client.post(f"/v1/kb/articles/{art['id']}/publish", headers=auth_headers["admin"])

    r = client.get("/v1/kb/public/categories")
    assert r.status_code == 200, r.text
    assert r.headers.get("cache-control") == "public, max-age=60"
    assert any(c["nome"] == "Público" for c in r.json())

    r = client.get("/v1/kb/public/articles", params={"busca": "visível"})
    assert r.status_code == 200
    assert len(r.json()) >= 1

    slug = art["slug"]
    r = client.get(f"/v1/kb/public/articles/{slug}")
    assert r.status_code == 200
    assert r.json()["titulo"] == "Manual visível"

    r = client.get("/v1/kb/public/articles/inexistente-xyz")
    assert r.status_code == 404


def test_kb_subcategoria_um_nivel(client, auth_headers):
    pai = client.post("/v1/kb/categories", headers=auth_headers["admin"], json={"nome": "Geral", "ordem": 0}).json()
    sub = client.post(
        "/v1/kb/categories",
        headers=auth_headers["admin"],
        json={"nome": "Tickets", "parent_id": pai["id"], "ordem": 1},
    )
    assert sub.status_code == 201, sub.text
    assert sub.json()["parent_id"] == pai["id"]
    assert sub.json()["parent_nome"] == "Geral"

    r = client.get("/v1/kb/categories", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    sub_list = next(c for c in r.json() if c["id"] == sub.json()["id"])
    assert sub_list["parent_nome"] == "Geral"

    r = client.post(
        "/v1/kb/categories",
        headers=auth_headers["admin"],
        json={"nome": "Nível 3", "parent_id": sub.json()["id"]},
    )
    assert r.status_code == 400

    art = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Guia", "category_id": sub.json()["id"], "conteudo_markdown": "texto"},
    ).json()
    client.post(f"/v1/kb/articles/{art['id']}/publish", headers=auth_headers["admin"])
    r = client.get(f"/v1/kb/articles/publicados/{art['id']}", headers=auth_headers["a1"])
    assert r.json()["category_nome"] == "Geral › Tickets"


def test_kb_excluir_categoria_com_subcategorias_bloqueado(client, auth_headers):
    pai = client.post("/v1/kb/categories", headers=auth_headers["admin"], json={"nome": "Pai"}).json()
    client.post(
        "/v1/kb/categories",
        headers=auth_headers["admin"],
        json={"nome": "Filha", "parent_id": pai["id"]},
    )
    r = client.delete(f"/v1/kb/categories/{pai['id']}", headers=auth_headers["admin"])
    assert r.status_code == 400


def test_kb_interno_only_excluido_api_publica(client, auth_headers):
    art = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={
            "titulo": "Manual interno",
            "conteudo_markdown": "segredo interno",
            "interno_only": True,
        },
    ).json()
    client.post(f"/v1/kb/articles/{art['id']}/publish", headers=auth_headers["admin"])

    r = client.get("/v1/kb/public/articles", params={"busca": "interno"})
    assert all(item["slug"] != art["slug"] for item in r.json())

    r = client.get(f"/v1/kb/public/articles/{art['slug']}")
    assert r.status_code == 404

    r = client.get("/v1/kb/articles/consulta", headers=auth_headers["a1"], params={"busca": "interno"})
    assert any(item["slug"] == art["slug"] for item in r.json())


def test_kb_arquivado_nao_edita(client, auth_headers):
    art = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Para arquivar", "conteudo_markdown": "x"},
    ).json()
    client.post(f"/v1/kb/articles/{art['id']}/archive", headers=auth_headers["admin"])
    r = client.patch(
        f"/v1/kb/articles/{art['id']}",
        headers=auth_headers["admin"],
        json={"titulo": "Alterado"},
    )
    assert r.status_code == 400


def test_kb_reordenar_categorias(client, auth_headers):
    a = client.post("/v1/kb/categories", headers=auth_headers["admin"], json={"nome": "A", "ordem": 0}).json()
    b = client.post("/v1/kb/categories", headers=auth_headers["admin"], json={"nome": "B", "ordem": 1}).json()
    r = client.put(
        "/v1/kb/categories/reorder",
        headers=auth_headers["admin"],
        json={"items": [{"id": b["id"], "ordem": 0}, {"id": a["id"], "ordem": 1}]},
    )
    assert r.status_code == 200, r.text
    nomes = [c["nome"] for c in r.json() if c["id"] in (a["id"], b["id"])]
    assert nomes.index("B") < nomes.index("A")


def test_kb_versoes_artigo(client, auth_headers):
    art = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Versões", "conteudo_markdown": "v1"},
    ).json()
    client.patch(
        f"/v1/kb/articles/{art['id']}",
        headers=auth_headers["admin"],
        json={"conteudo_markdown": "v2"},
    )
    r = client.get(f"/v1/kb/articles/{art['id']}/versions", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert len(r.json()) >= 2
    vid = r.json()[0]["id"]
    r2 = client.get(f"/v1/kb/articles/{art['id']}/versions/{vid}", headers=auth_headers["admin"])
    assert r2.status_code == 200
    assert r2.json()["conteudo_markdown"]


def test_kb_upload_imagem(client, auth_headers):
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = client.post(
        "/v1/kb/images",
        headers=auth_headers["admin"],
        files={"file": ("test.png", png, "image/png")},
    )
    assert r.status_code == 201, r.text
    filename = r.json()["filename"]
    r2 = client.get(f"/v1/kb/images/{filename}")
    assert r2.status_code == 200
