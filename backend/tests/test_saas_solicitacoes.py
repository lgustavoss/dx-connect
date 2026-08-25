"""Fila SaaS de solicitações de produto (#855)."""

from __future__ import annotations

from datetime import date

from app.models.webhook_outbox import WebhookOutbox


def _criar_solicitacao(client, headers, **kw):
    body = {
        "tipo": "sugestao",
        "titulo": "Melhorar filtros do histórico",
        "descricao": "Gostaria de filtrar por período e setor na lista de atendimentos.",
        "versao_contexto": "2026.08.21",
    }
    body.update(kw)
    return client.post("/v1/solicitacoes-melhoria", headers=headers, json=body)


def _cliente(client, headers, slug="duplex-soft"):
    r = client.post(
        "/v1/saas/clientes",
        headers=headers,
        json={
            "nome": "Duplex Soft",
            "slug": slug,
            "status": "trial",
            "data_inicio": str(date.today()),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_fila_saas_404_sem_control_plane(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.get("/v1/saas/solicitacoes", headers=auth_headers["ops"])
    assert r.status_code == 404


def test_fila_saas_403_nao_ops(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    assert client.get("/v1/saas/solicitacoes", headers=auth_headers["admin"]).status_code == 403
    assert client.get("/v1/saas/solicitacoes", headers=auth_headers["a1"]).status_code == 403


def test_criar_na_instancia_copia_direto_no_control_plane(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]

    lista = client.get("/v1/saas/solicitacoes", headers=auth_headers["ops"])
    assert lista.status_code == 200, lista.text
    items = lista.json()["items"]
    assert any(i["origem_solicitacao_id"] == sid and i["instance_slug"] == "local" for i in items)
    item = next(i for i in items if i["origem_solicitacao_id"] == sid)
    assert item["protocolo"].startswith("#S")
    origem = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"])
    assert origem.status_code == 200
    assert origem.json()["protocolo"] == item["protocolo"]
    det = client.get(f"/v1/saas/solicitacoes/{item['id']}", headers=auth_headers["ops"])
    assert det.status_code == 200
    body = det.json()
    assert "filtrar por período" in body["descricao"]
    assert body["autor_nome"]
    assert body["status_rotulo"] == "Recebida"


def test_criar_sem_ingest_config_nao_quebra_pedido_local(
    client, seed_base, auth_headers, monkeypatch, db_session
):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE_INGEST_URL", None)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_INGEST_TOKEN", None)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", None)
    r = _criar_solicitacao(client, auth_headers["a1"])
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert db_session.query(WebhookOutbox).filter(WebhookOutbox.event_type == "saas.solicitacao").count() == 0


def test_criar_enfileira_outbox_quando_ingest_configurado(
    client, seed_base, auth_headers, monkeypatch, db_session
):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    monkeypatch.setattr(
        settings, "SAAS_CONTROL_PLANE_INGEST_URL", "https://api.deskrudder.com.br/v1/saas/ingest/solicitacoes"
    )
    monkeypatch.setattr(settings, "SAAS_INSTANCE_INGEST_TOKEN", "token-secreto")
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "duplex-soft")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    db_session.expire_all()
    row = (
        db_session.query(WebhookOutbox)
        .filter(WebhookOutbox.event_type == "saas.solicitacao")
        .order_by(WebhookOutbox.id.desc())
        .first()
    )
    assert row is not None
    assert str(sid) in (row.dedup_key or "")
    assert "duplex-soft" in (row.payload_json or "")


_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_criar_na_instancia_copia_anexos_no_control_plane(
    client, seed_base, auth_headers, monkeypatch, tmp_path
):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    monkeypatch.setattr(settings, "SOLICITACAO_MEDIA_DIR", str(tmp_path))
    up = client.post(
        "/v1/solicitacoes-melhoria/media",
        headers=auth_headers["a1"],
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline"},
    )
    assert up.status_code == 201, up.text
    anexo = up.json()
    sid = _criar_solicitacao(
        client,
        auth_headers["a1"],
        descricao=f"Passo com print.\n\n![x]({anexo['url']})",
        anexo_ids=[anexo["id"]],
    ).json()["id"]
    lista = client.get("/v1/saas/solicitacoes", headers=auth_headers["ops"])
    item = next(i for i in lista.json()["items"] if i["origem_solicitacao_id"] == sid)
    det = client.get(f"/v1/saas/solicitacoes/{item['id']}", headers=auth_headers["ops"])
    assert det.status_code == 200, det.text
    body = det.json()
    assert len(body["anexos"]) == 1
    assert body["anexos"][0]["papel"] == "inline"
    assert body["anexos"][0]["url"] == anexo["url"]
    media = client.get(anexo["url"])
    assert media.status_code == 200
    assert media.content == _PNG_1X1


def test_criar_enfileira_outbox_media_quando_ha_anexo(
    client, seed_base, auth_headers, monkeypatch, db_session, tmp_path
):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    monkeypatch.setattr(
        settings, "SAAS_CONTROL_PLANE_INGEST_URL", "https://api.deskrudder.com.br/v1/saas/ingest/solicitacoes"
    )
    monkeypatch.setattr(settings, "SAAS_INSTANCE_INGEST_TOKEN", "token-secreto")
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "duplex-soft")
    monkeypatch.setattr(settings, "SOLICITACAO_MEDIA_DIR", str(tmp_path))
    up = client.post(
        "/v1/solicitacoes-melhoria/media",
        headers=auth_headers["a1"],
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline"},
    )
    anexo = up.json()
    sid = _criar_solicitacao(
        client,
        auth_headers["a1"],
        anexo_ids=[anexo["id"]],
        descricao="Com print no texto.",
    ).json()["id"]
    db_session.expire_all()
    media_row = (
        db_session.query(WebhookOutbox)
        .filter(WebhookOutbox.event_type == "saas.solicitacao.media")
        .order_by(WebhookOutbox.id.desc())
        .first()
    )
    assert media_row is not None
    assert str(sid) in (media_row.dedup_key or "")
    assert media_row.target_url.endswith(f"/{sid}/media")
    assert anexo["url"].rsplit("/", 1)[-1] in (media_row.payload_json or "")


def test_ingest_http_media(
    client, seed_base, auth_headers, monkeypatch, tmp_path
):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    monkeypatch.setattr(settings, "SOLICITACAO_MEDIA_DIR", str(tmp_path))
    h = auth_headers["ops"]
    cid = _cliente(client, h)["id"]
    token = client.post(f"/v1/saas/clientes/{cid}/gerar-token-ingest", headers=h).json()["token"]
    storage_key = ("ab" * 16) + ".png"
    payload = {
        "instance_slug": "duplex-soft",
        "origem_solicitacao_id": 99,
        "tipo": "sugestao",
        "titulo": "Print no login",
        "descricao": f"Veja ![print](/v1/solicitacoes-melhoria/media/{storage_key})",
        "status": "aberta",
        "autor_nome": "Ana",
    }
    auth = {"Authorization": f"Bearer {token}"}
    too_soon = client.post(
        "/v1/saas/ingest/solicitacoes/99/media",
        headers=auth,
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline", "storage_key": storage_key},
    )
    assert too_soon.status_code == 404

    assert client.post("/v1/saas/ingest/solicitacoes", json=payload, headers=auth).status_code == 200

    denied = client.post(
        "/v1/saas/ingest/solicitacoes/99/media",
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline", "storage_key": storage_key},
    )
    assert denied.status_code == 401

    ok = client.post(
        "/v1/saas/ingest/solicitacoes/99/media",
        headers=auth,
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline", "storage_key": storage_key},
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["papel"] == "inline"
    url = ok.json()["url"]
    assert storage_key in url

    again = client.post(
        "/v1/saas/ingest/solicitacoes/99/media",
        headers=auth,
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline", "storage_key": storage_key},
    )
    assert again.status_code == 201

    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    saas_id = next(i["id"] for i in lista if i["origem_solicitacao_id"] == 99)
    det = client.get(f"/v1/saas/solicitacoes/{saas_id}", headers=h)
    assert det.status_code == 200
    anexos = det.json()["anexos"]
    assert len(anexos) == 1
    media = client.get(url)
    assert media.status_code == 200
    assert media.content == _PNG_1X1


def test_ingest_http_autenticado(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]
    cid = _cliente(client, h)["id"]
    tok = client.post(f"/v1/saas/clientes/{cid}/gerar-token-ingest", headers=h)
    assert tok.status_code == 200, tok.text
    token = tok.json()["token"]
    assert token
    assert tok.json()["ingest_url"].endswith("/v1/saas/ingest/solicitacoes")

    payload = {
        "instance_slug": "duplex-soft",
        "origem_solicitacao_id": 42,
        "tipo": "problema",
        "titulo": "PDF corta o rodapé",
        "descricao": "No exportar PDF o rodapé fica cortado na última página.",
        "status": "aberta",
        "versao_contexto": "2026.08.22",
        "autor_nome": "Maria",
    }
    denied = client.post("/v1/saas/ingest/solicitacoes", json=payload)
    assert denied.status_code == 401

    bad = client.post(
        "/v1/saas/ingest/solicitacoes",
        json=payload,
        headers={"Authorization": "Bearer token-errado"},
    )
    assert bad.status_code == 401

    ok = client.post(
        "/v1/saas/ingest/solicitacoes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["tipo"] == "problema"
    assert body["cliente_nome"] == "Duplex Soft"
    assert body["protocolo"].startswith("#S")
    first_id = body["id"]
    first_proto = body["protocolo"]

    payload["titulo"] = "PDF corta o rodapé (actualizado)"
    again = client.post(
        "/v1/saas/ingest/solicitacoes",
        json=payload,
        headers={"X-Saas-Instance-Token": token},
    )
    assert again.status_code == 200
    assert again.json()["id"] == first_id
    assert again.json()["protocolo"] == first_proto
    assert "actualizado" in again.json()["titulo"]

    lista = client.get("/v1/saas/solicitacoes?tipo=problema", headers=h)
    assert lista.status_code == 200
    assert any(i["id"] == first_id for i in lista.json()["items"])


def test_ingest_dois_clientes_protocolo_unico(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]
    a = _cliente(client, h, slug="cliente-a")
    b = _cliente(client, h, slug="cliente-b")
    tok_a = client.post(f"/v1/saas/clientes/{a['id']}/gerar-token-ingest", headers=h).json()["token"]
    tok_b = client.post(f"/v1/saas/clientes/{b['id']}/gerar-token-ingest", headers=h).json()["token"]
    base = {
        "tipo": "sugestao",
        "titulo": "Mesmo título nos dois",
        "descricao": "Pedido equivalente em duas instâncias distintas.",
        "status": "aberta",
        "origem_solicitacao_id": 1,
    }
    r1 = client.post(
        "/v1/saas/ingest/solicitacoes",
        json={**base, "instance_slug": "cliente-a"},
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    r2 = client.post(
        "/v1/saas/ingest/solicitacoes",
        json={**base, "instance_slug": "cliente-b"},
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    p1, p2 = r1.json()["protocolo"], r2.json()["protocolo"]
    assert p1.startswith("#S") and p2.startswith("#S")
    assert p1 != p2


def test_ingest_404_sem_control_plane(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.post(
        "/v1/saas/ingest/solicitacoes",
        json={
            "instance_slug": "x",
            "origem_solicitacao_id": 1,
            "tipo": "sugestao",
            "titulo": "Abcdef",
            "descricao": "Descrição com mais de dez caracteres.",
        },
        headers={"Authorization": "Bearer x"},
    )
    assert r.status_code == 404


def test_ops_altera_status_e_cliente_ve_na_instancia(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    h = auth_headers["ops"]
    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    saas_id = next(i["id"] for i in lista if i["origem_solicitacao_id"] == sid)

    r = client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/status",
        headers=h,
        json={"status": "em_analise"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "em_analise"
    assert r.json()["status_rotulo"] == "Em análise"

    minhas = client.get("/v1/solicitacoes-melhoria/minhas", headers=auth_headers["a1"]).json()
    item = next(i for i in minhas if i["id"] == sid)
    assert item["status"] == "em_analise"

    det = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    assert det["status"] == "em_analise"
    assert any(hist["status_novo"] == "em_analise" for hist in det["historico"])


def test_comentario_publico_volta_interno_nao(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    h = auth_headers["ops"]
    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    saas_id = next(i["id"] for i in lista if i["origem_solicitacao_id"] == sid)

    pub = client.post(
        f"/v1/saas/solicitacoes/{saas_id}/comentarios",
        headers=h,
        json={"corpo": "Vamos incluir no próximo lote.", "publico_cliente": True},
    )
    assert pub.status_code == 200, pub.text
    intern = client.post(
        f"/v1/saas/solicitacoes/{saas_id}/comentarios",
        headers=h,
        json={"corpo": "Abrir issue no GitHub depois", "publico_cliente": False},
    )
    assert intern.status_code == 200, intern.text
    corpos_saas = [c["corpo"] for c in intern.json()["comentarios"]]
    assert any("próximo lote" in c for c in corpos_saas)
    assert any("GitHub" in c for c in corpos_saas)

    cliente_view = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    corpos = [c["corpo"] for c in cliente_view["comentarios"]]
    assert any("próximo lote" in c for c in corpos)
    assert not any("GitHub" in c for c in corpos)
    assert cliente_view.get("github_issue_url") in (None, "")


def test_comentario_publico_rejeita_issue_github(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    h = auth_headers["ops"]
    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    saas_id = next(i["id"] for i in lista if i["origem_solicitacao_id"] == sid)

    bad = client.post(
        f"/v1/saas/solicitacoes/{saas_id}/comentarios",
        headers=h,
        json={"corpo": "Pedido aceite. Acompanhamento interno: issue #921.", "publico_cliente": True},
    )
    assert bad.status_code == 400, bad.text

    ok = client.post(
        f"/v1/saas/solicitacoes/{saas_id}/comentarios",
        headers=h,
        json={"corpo": "Acompanhamento interno: issue #921.", "publico_cliente": False},
    )
    assert ok.status_code == 200, ok.text
    cliente_view = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    assert not any("921" in (c["corpo"] or "") for c in cliente_view["comentarios"])


def test_admin_instancia_nao_tria(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    assert (
        client.patch(
            f"/v1/solicitacoes-melhoria/{sid}/status",
            headers=auth_headers["admin"],
            json={"status": "em_analise"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/solicitacoes-melhoria/{sid}/comentarios",
            headers=auth_headers["admin"],
            json={"corpo": "nota", "publico_cliente": True},
        ).status_code
        == 403
    )


def test_sync_get_autenticado(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]
    cid = _cliente(client, h)["id"]
    token = client.post(f"/v1/saas/clientes/{cid}/gerar-token-ingest", headers=h).json()["token"]
    payload = {
        "instance_slug": "duplex-soft",
        "origem_solicitacao_id": 77,
        "tipo": "sugestao",
        "titulo": "Filtro por posto",
        "descricao": "Gostaria de filtrar a lista de tickets por posto.",
        "status": "aberta",
    }
    ingest = client.post(
        "/v1/saas/ingest/solicitacoes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    saas_id = ingest.json()["id"]
    client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/status",
        headers=h,
        json={"status": "planejada"},
    )
    client.post(
        f"/v1/saas/solicitacoes/{saas_id}/comentarios",
        headers=h,
        json={"corpo": "Entrou no roadmap.", "publico_cliente": True},
    )
    client.post(
        f"/v1/saas/solicitacoes/{saas_id}/comentarios",
        headers=h,
        json={"corpo": "nota interna", "publico_cliente": False},
    )

    denied = client.get("/v1/saas/ingest/solicitacoes/sync")
    assert denied.status_code == 401

    sync = client.get(
        "/v1/saas/ingest/solicitacoes/sync",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sync.status_code == 200, sync.text
    items = sync.json()["items"]
    row = next(i for i in items if i["origem_solicitacao_id"] == 77)
    assert row["status"] == "planejada"
    assert row["protocolo"].startswith("#S")
    assert any("roadmap" in c["corpo"] for c in row["comentarios_publicos"])
    assert not any("interna" in c["corpo"] for c in row["comentarios_publicos"])


def test_pull_aplica_triagem_na_instancia(client, seed_base, auth_headers, monkeypatch, db_session):
    from app.config import settings
    from app.services.saas_solicitacao_triagem import process_triagem_pull

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    monkeypatch.setattr(
        settings, "SAAS_CONTROL_PLANE_INGEST_URL", "https://api.deskrudder.com.br/v1/saas/ingest/solicitacoes"
    )
    monkeypatch.setattr(settings, "SAAS_INSTANCE_INGEST_TOKEN", "tok")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    payload = {
        "items": [
            {
                "origem_solicitacao_id": sid,
                "status": "em_desenvolvimento",
                "motivo_nao_desenvolvimento": None,
                "comentarios_publicos": [
                    {
                        "id": 99,
                        "corpo": "Já estamos a implementar.",
                        "autor_nome": "Ops DeskRudder",
                        "created_at": "2026-08-22T15:00:00+00:00",
                    }
                ],
            }
        ]
    }
    monkeypatch.setattr(
        "app.services.saas_solicitacao_triagem._get_json",
        lambda url, token, timeout=20: payload,
    )
    n = process_triagem_pull(db_session)
    db_session.commit()
    assert n == 1
    det = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    assert det["status"] == "em_desenvolvimento"
    assert any("implementar" in c["corpo"] for c in det["comentarios"])
    n2 = process_triagem_pull(db_session)
    db_session.commit()
    det2 = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    assert sum(1 for c in det2["comentarios"] if "implementar" in c["corpo"]) == 1
    assert n2 == 1


def test_mcp_token_lista_status_e_liga_github(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    monkeypatch.setattr(settings, "SAAS_MCP_TOKEN", "mcp-token-local-test")
    sid = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    lista_ops = client.get("/v1/saas/solicitacoes", headers=auth_headers["ops"])
    saas_id = next(i["id"] for i in lista_ops.json()["items"] if i["origem_solicitacao_id"] == sid)
    mcp = {"Authorization": "Bearer mcp-token-local-test"}
    listed = client.get("/v1/saas/solicitacoes", headers=mcp)
    assert listed.status_code == 200, listed.text
    item = next(i for i in listed.json()["items"] if i["id"] == saas_id)
    assert item["protocolo"].startswith("#S")
    busca = client.get("/v1/saas/solicitacoes", headers=mcp, params={"busca": item["protocolo"]})
    assert busca.status_code == 200
    assert any(i["id"] == saas_id for i in busca.json()["items"])
    st = client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/status",
        headers=mcp,
        json={"status": "planejada"},
    )
    assert st.status_code == 200, st.text
    assert st.json()["status"] == "planejada"
    gh = client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/github",
        headers=mcp,
        json={"github_issue_url": "https://github.com/lgustavoss/dx-connect/issues/857"},
    )
    assert gh.status_code == 200, gh.text
    assert gh.json()["github_issue_number"] == 857
    assert "857" in (gh.json()["github_issue_url"] or "")
    assert client.get("/v1/saas/solicitacoes", headers=auth_headers["admin"]).status_code == 403
    assert client.get("/v1/saas/solicitacoes", headers={"Authorization": "Bearer token-errado"}).status_code == 401


def test_mcp_stdio_initialize_e_tools():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "mcp_deskrudder_saas.py"
    spec = importlib.util.spec_from_file_location("mcp_deskrudder_saas", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    init = mod.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "deskrudder-saas"
    assert "português do Brasil" in init["result"]["instructions"]
    listed = mod.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in listed["result"]["tools"]}
    assert {"listar_solicitacoes", "obter_solicitacao", "alterar_status", "comentar_solicitacao", "ligar_issue_github", "vincular_solicitacao", "desvincular_solicitacao"} <= names
    comentar = next(t for t in listed["result"]["tools"] if t["name"] == "comentar_solicitacao")
    assert "português do Brasil" in comentar["description"]


def test_mcp_comentar_sem_flag_fica_interno(monkeypatch):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "mcp_deskrudder_saas.py"
    spec = importlib.util.spec_from_file_location("mcp_deskrudder_saas", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    captured: dict = {}

    def fake_api(method, path, body=None):
        captured["body"] = body
        return 200, {"ok": True}

    monkeypatch.setattr(mod, "_api", fake_api)
    monkeypatch.setattr(mod, "_id_fila", lambda args: 7)
    mod.call_tool("comentar_solicitacao", {"id": 7, "corpo": "nota do agente"})
    assert captured["body"]["publico_cliente"] is False
    mod.call_tool("comentar_solicitacao", {"id": 7, "corpo": "olá", "publico_cliente": True})
    assert captured["body"]["publico_cliente"] is True


def test_vincular_pedidos_iguais_peso_e_nao_vaza_ao_cliente(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]
    a = _cliente(client, h, slug="cliente-a")
    b = _cliente(client, h, slug="cliente-b")
    tok_a = client.post(f"/v1/saas/clientes/{a['id']}/gerar-token-ingest", headers=h).json()["token"]
    tok_b = client.post(f"/v1/saas/clientes/{b['id']}/gerar-token-ingest", headers=h).json()["token"]
    corpo = {
        "tipo": "sugestao",
        "titulo": "Filtro por posto na lista",
        "descricao": "Quero filtrar tickets por posto na listagem principal.",
        "status": "aberta",
        "origem_solicitacao_id": 1,
    }
    r1 = client.post(
        "/v1/saas/ingest/solicitacoes",
        json={**corpo, "instance_slug": "cliente-a"},
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    r2 = client.post(
        "/v1/saas/ingest/solicitacoes",
        json={**corpo, "instance_slug": "cliente-b"},
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert r1.status_code == 200 and r2.status_code == 200
    id1, id2 = r1.json()["id"], r2.json()["id"]
    p1, p2 = r1.json()["protocolo"], r2.json()["protocolo"]

    denied = client.post(
        f"/v1/saas/solicitacoes/{id1}/vinculos",
        headers=auth_headers["a1"],
        json={"solicitacao_id": id2},
    )
    assert denied.status_code == 403

    linked = client.post(
        f"/v1/saas/solicitacoes/{id1}/vinculos",
        headers=h,
        json={"protocolo": p2},
    )
    assert linked.status_code == 200, linked.text
    body = linked.json()
    assert body["peso_clientes"] == 2
    assert body["pedidos_grupo"] == 2
    assert len(body["grupo"]) == 2
    assert p1 in body["texto_github_demanda"] and p2 in body["texto_github_demanda"]

    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    assert any(i["id"] == id1 and i["peso_clientes"] == 2 for i in lista)

    gh = client.patch(
        f"/v1/saas/solicitacoes/{id1}/github",
        headers=h,
        json={"github_issue_url": "https://github.com/lgustavoss/dx-connect/issues/900"},
    )
    assert gh.status_code == 200, gh.text
    outro = client.get(f"/v1/saas/solicitacoes/{id2}", headers=h).json()
    assert outro["github_issue_number"] == 900

    sync = client.get(
        "/v1/saas/ingest/solicitacoes/sync",
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert sync.status_code == 200
    item = next(i for i in sync.json()["items"] if i["origem_solicitacao_id"] == 1)
    assert "grupo" not in item
    assert "texto_github_demanda" not in item
    assert "peso_clientes" not in item

    off = client.post(
        f"/v1/saas/solicitacoes/{id1}/vinculos/{id2}",
        headers=h,
    )
    assert off.status_code == 405 or off.status_code == 404

    gone = client.delete(f"/v1/saas/solicitacoes/{id1}/vinculos/{id2}", headers=h)
    assert gone.status_code == 200, gone.text
    assert gone.json()["peso_clientes"] == 1
    assert len(gone.json()["grupo"]) == 1


def test_fila_filtro_fase_tipo_e_resumo(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    h = auth_headers["ops"]

    sid_sug = _criar_solicitacao(client, auth_headers["a1"]).json()["id"]
    sid_err = _criar_solicitacao(
        client,
        auth_headers["a1"],
        tipo="problema",
        titulo="Erro ao abrir o chat",
        descricao="O chat interno trava ao carregar a lista de conversas.",
    ).json()["id"]

    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    saas_sug = next(i["id"] for i in lista if i["origem_solicitacao_id"] == sid_sug)
    saas_err = next(i["id"] for i in lista if i["origem_solicitacao_id"] == sid_err)

    client.patch(
        f"/v1/saas/solicitacoes/{saas_sug}/status",
        headers=h,
        json={"status": "em_desenvolvimento"},
    )
    client.patch(
        f"/v1/saas/solicitacoes/{saas_err}/status",
        headers=h,
        json={"status": "concluida"},
    )

    aguardando = client.get("/v1/saas/solicitacoes?fase=aguardando", headers=h)
    assert aguardando.status_code == 200
    ids_ag = {i["id"] for i in aguardando.json()["items"]}
    assert saas_sug not in ids_ag
    assert saas_err not in ids_ag

    dev = client.get("/v1/saas/solicitacoes?fase=desenvolvimento", headers=h)
    assert {i["id"] for i in dev.json()["items"]} >= {saas_sug}

    fin = client.get("/v1/saas/solicitacoes?fase=finalizadas", headers=h)
    assert {i["id"] for i in fin.json()["items"]} >= {saas_err}

    so_erro = client.get("/v1/saas/solicitacoes?tipo=problema", headers=h)
    assert all(i["tipo"] == "problema" for i in so_erro.json()["items"])
    assert saas_err in {i["id"] for i in so_erro.json()["items"]}

    resumo = client.get("/v1/saas/solicitacoes/resumo", headers=h)
    assert resumo.status_code == 200, resumo.text
    body = resumo.json()
    assert body["total"] >= 2
    assert body["sugestoes"] >= 1
    assert body["problemas"] >= 1
    assert body["desenvolvimento"] >= 1
    assert body["finalizadas"] >= 1

    bad = client.get("/v1/saas/solicitacoes?fase=xyz", headers=h)
    assert bad.status_code == 400

