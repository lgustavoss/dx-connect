"""Base de conhecimento (#293, #294)."""

from __future__ import annotations

from app.models import AuditLog, KbArticle, KbArticleMotivoLink, KbArticleVersion, KbCategory


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


def test_kb_public_branding_com_logo(client, auth_headers, db_session):
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    client.post(
        "/v1/settings/empresa-sistema/logo",
        headers=auth_headers["admin"],
        files={"file": ("logo.png", png, "image/png")},
    )
    r = client.get("/v1/kb/public/branding")
    assert r.status_code == 200
    assert r.json()["logo_url"] == "/v1/kb/public/logo"
    r2 = client.get("/v1/kb/public/logo")
    assert r2.status_code == 200


def test_kb_portal_settings_admin(client, auth_headers, db_session):
    r = client.get("/v1/kb/portal-settings", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    assert r.json()["cor_header"] == "#0B2D4A"

    r = client.put(
        "/v1/kb/portal-settings",
        headers=auth_headers["admin"],
        json={
            "portal_titulo": "Ajuda ACME",
            "cor_header": "#112233",
            "cor_primaria": "#AABBCC",
            "cor_texto_header": "#FFFFFF",
            "cor_texto_corpo": "#222222",
            "cor_fundo": "#EEEEEE",
            "cor_link": "#0055AA",
            "texto_boas_vindas": "Bem-vindo à central de ajuda.",
            "exibir_marca_deskrudder": False,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["portal_titulo"] == "Ajuda ACME"
    assert body["cor_header"] == "#112233"

    r = client.get("/v1/kb/public/branding")
    assert r.status_code == 200
    pub = r.json()
    assert pub["portal_titulo"] == "Ajuda ACME"
    assert pub["cor_header"] == "#112233"
    assert pub["cor_link"] == "#0055AA"
    assert pub["texto_boas_vindas"] == "Bem-vindo à central de ajuda."
    assert pub["exibir_marca_deskrudder"] is False

    r403 = client.get("/v1/kb/portal-settings", headers=auth_headers["a1"])
    assert r403.status_code == 403


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

    r = client.get("/v1/kb/public/branding")
    assert r.status_code == 200, r.text
    branding = r.json()
    assert "nome_exibicao" in branding
    assert branding.get("logo_url") is None or branding["logo_url"].endswith("/kb/public/logo")

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


def _seed_classificacao_kb(db_session):
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza

    nat = TicketNatureza(nome="Erro KB", slug="erro-kb-test", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="PDV KB", slug="pdv-kb-test", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.commit()
    return nat, mot


def test_kb_sugestoes_por_motivo_e_natureza(client, auth_headers, db_session):
    nat, mot = _seed_classificacao_kb(db_session)

    art_mot = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Guia PDV", "conteudo_markdown": "passos pdv"},
    ).json()
    art_nat = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Guia Erro geral", "conteudo_markdown": "passos erro"},
    ).json()
    art_rascunho = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Rascunho PDV", "conteudo_markdown": "não publicado"},
    ).json()

    for aid in (art_mot["id"], art_nat["id"]):
        client.post(f"/v1/kb/articles/{aid}/publish", headers=auth_headers["admin"])

    r = client.put(
        f"/v1/kb/articles/{art_mot['id']}/motivo-links",
        headers=auth_headers["admin"],
        json={"links": [{"motivo_id": mot.id, "ordem": 0}]},
    )
    assert r.status_code == 200, r.text

    r = client.put(
        f"/v1/kb/articles/{art_nat['id']}/motivo-links",
        headers=auth_headers["admin"],
        json={"links": [{"natureza_id": nat.id, "ordem": 0}]},
    )
    assert r.status_code == 200, r.text

    r = client.put(
        f"/v1/kb/articles/{art_rascunho['id']}/motivo-links",
        headers=auth_headers["admin"],
        json={"links": [{"motivo_id": mot.id, "ordem": 0}]},
    )
    assert r.status_code == 200

    r = client.get("/v1/kb/suggestions", headers=auth_headers["a1"], params={"motivo_id": mot.id})
    assert r.status_code == 200, r.text
    titulos = [x["titulo"] for x in r.json()]
    assert "Guia PDV" in titulos
    assert "Guia Erro geral" in titulos
    assert "Rascunho PDV" not in titulos
    assert len(titulos) <= 5

    r = client.get("/v1/kb/suggestions", headers=auth_headers["a1"], params={"natureza_id": nat.id})
    assert r.status_code == 200
    assert any(x["titulo"] == "Guia Erro geral" for x in r.json())

    interno = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Interno PDV", "conteudo_markdown": "x", "interno_only": True},
    ).json()
    client.post(f"/v1/kb/articles/{interno['id']}/publish", headers=auth_headers["admin"])
    client.put(
        f"/v1/kb/articles/{interno['id']}/motivo-links",
        headers=auth_headers["admin"],
        json={"links": [{"motivo_id": mot.id, "ordem": 0}]},
    )

    r = client.get("/v1/kb/public/suggestions", params={"motivo_id": mot.id})
    assert r.status_code == 200
    assert all(x["titulo"] != "Interno PDV" for x in r.json())

    r = client.get("/v1/kb/suggestions", headers=auth_headers["a1"], params={"motivo_id": mot.id})
    assert any(x["titulo"] == "Interno PDV" for x in r.json())

    links = db_session.query(KbArticleMotivoLink).filter(KbArticleMotivoLink.article_id == art_mot["id"]).all()
    assert len(links) == 1
    assert links[0].motivo_id == mot.id


def test_kb_feedback_artigo_publico(client, auth_headers, db_session):
    art = client.post(
        "/v1/kb/articles",
        headers=auth_headers["admin"],
        json={"titulo": "Manual com feedback", "conteudo_markdown": "Conteúdo"},
    ).json()
    client.post(f"/v1/kb/articles/{art['id']}/publish", headers=auth_headers["admin"])
    slug = art["slug"]

    r = client.post(f"/v1/kb/public/articles/{slug}/feedback", json={"util": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["util"] is True
    assert body["ja_avaliado"] is False
    assert body["feedback_util_count"] == 1
    assert body["feedback_nao_util_count"] == 0

    r_dup = client.post(f"/v1/kb/public/articles/{slug}/feedback", json={"util": False})
    assert r_dup.status_code == 200, r_dup.text
    dup = r_dup.json()
    assert dup["ja_avaliado"] is True
    assert dup["util"] is True
    assert dup["feedback_util_count"] == 1

    r_admin = client.get(f"/v1/kb/articles/{art['id']}", headers=auth_headers["admin"])
    assert r_admin.status_code == 200
    admin = r_admin.json()
    assert admin["feedback_util_count"] == 1
    assert admin["feedback_nao_util_count"] == 0

    client.put(
        "/v1/kb/portal-settings",
        headers=auth_headers["admin"],
        json={"feedback_habilitado": False},
    )
    r_off = client.post(f"/v1/kb/public/articles/{slug}/feedback", json={"util": True})
    assert r_off.status_code == 403

    client.put(
        "/v1/kb/portal-settings",
        headers=auth_headers["admin"],
        json={"feedback_habilitado": True},
    )
    r_brand = client.get("/v1/kb/public/branding")
    assert r_brand.status_code == 200
    assert r_brand.json()["feedback_habilitado"] is True

    r404 = client.post("/v1/kb/public/articles/slug-inexistente/feedback", json={"util": True})
    assert r404.status_code == 404
