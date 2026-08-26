"""Solicitações de melhoria — Release Notes (#799 / #800–#807)."""

from __future__ import annotations


def _criar(client, headers, **kw):
    body = {
        "tipo": "sugestao",
        "titulo": "Melhorar filtros do histórico",
        "descricao": "Gostaria de filtrar por período e setor na lista de atendimentos.",
        "versao_contexto": "2026.08.21",
    }
    body.update(kw)
    return client.post("/v1/solicitacoes-melhoria", headers=headers, json=body)


def test_criar_e_listar_minhas(client, seed_base, auth_headers):
    r = _criar(client, auth_headers["a1"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "aberta"
    assert data["status_rotulo"] == "Recebida"
    assert data["github_issue_url"] is None
    assert "mensagem_status" in data
    assert data.get("protocolo") in (None, "") or str(data.get("protocolo")).startswith("#S")

    lista = client.get("/v1/solicitacoes-melhoria/minhas", headers=auth_headers["a1"])
    assert lista.status_code == 200
    assert any(i["id"] == data["id"] for i in lista.json())


def test_status_so_admin_e_motivo_obrigatorio(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = _criar(client, auth_headers["a1"]).json()["id"]

    denied = client.patch(
        f"/v1/solicitacoes-melhoria/{sid}/status",
        headers=auth_headers["a1"],
        json={"status": "em_analise"},
    )
    assert denied.status_code == 403

    admin_denied = client.patch(
        f"/v1/solicitacoes-melhoria/{sid}/status",
        headers=auth_headers["admin"],
        json={
            "status": "nao_sera_desenvolvida",
            "motivo_nao_desenvolvimento": "Fora do roadmap deste trimestre.",
        },
    )
    assert admin_denied.status_code == 403

    lista = client.get("/v1/saas/solicitacoes", headers=auth_headers["ops"])
    assert lista.status_code == 200, lista.text
    saas_id = next(i["id"] for i in lista.json()["items"] if i["origem_solicitacao_id"] == sid)

    bad = client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/status",
        headers=auth_headers["ops"],
        json={"status": "nao_sera_desenvolvida"},
    )
    assert bad.status_code == 400

    ok = client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/status",
        headers=auth_headers["ops"],
        json={
            "status": "nao_sera_desenvolvida",
            "motivo_nao_desenvolvimento": "Fora do roadmap deste trimestre.",
        },
    )
    assert ok.status_code == 200, ok.text
    body = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    assert body["status"] == "nao_sera_desenvolvida"
    assert "Fora do roadmap" in (body["motivo_nao_desenvolvimento"] or "")
    assert any(h["status_novo"] == "nao_sera_desenvolvida" for h in body["historico"])


def test_comentarios_publico_vs_interno(client, seed_base, auth_headers):
    sid = _criar(client, auth_headers["a1"]).json()["id"]

    # Cliente não cria nota interna
    r403 = client.post(
        f"/v1/solicitacoes-melhoria/{sid}/comentarios",
        headers=auth_headers["a1"],
        json={"corpo": "segredo", "publico_cliente": False},
    )
    assert r403.status_code == 403

    pub = client.post(
        f"/v1/solicitacoes-melhoria/{sid}/comentarios",
        headers=auth_headers["a1"],
        json={"corpo": "Posso dar mais detalhes se precisarem.", "publico_cliente": True},
    )
    assert pub.status_code == 200

    admin_c = client.post(
        f"/v1/solicitacoes-melhoria/{sid}/comentarios",
        headers=auth_headers["admin"],
        json={"corpo": "Nota interna de triagem", "publico_cliente": False},
    )
    assert admin_c.status_code == 403

    cliente_view = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    corpos = [c["corpo"] for c in cliente_view["comentarios"]]
    assert "Posso dar mais detalhes" in "".join(corpos)
    assert "Nota interna" not in "".join(corpos)

    admin_view = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["admin"]).json()
    assert "Nota interna" not in "".join(c["corpo"] for c in admin_view["comentarios"])


def test_a2_nao_comenta_solicitacao_de_a1(client, seed_base, auth_headers):
    sid = _criar(client, auth_headers["a1"]).json()["id"]
    # Mesma org (tenant) — pode ler, mas só autor responde
    r = client.post(
        f"/v1/solicitacoes-melhoria/{sid}/comentarios",
        headers=auth_headers["a2"],
        json={"corpo": "Eu também quero isto", "publico_cliente": True},
    )
    assert r.status_code == 403


def test_status_final_bloqueia_resposta_cliente(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    sid = _criar(client, auth_headers["a1"]).json()["id"]
    h = auth_headers["ops"]
    lista = client.get("/v1/saas/solicitacoes", headers=h).json()["items"]
    saas_id = next(i["id"] for i in lista if i["origem_solicitacao_id"] == sid)
    for st in ("em_analise", "planejada"):
        r = client.patch(
            f"/v1/saas/solicitacoes/{saas_id}/status",
            headers=h,
            json={"status": st},
        )
        assert r.status_code == 200, r.text
    client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/github",
        headers=h,
        json={"github_issue_url": "https://github.com/lgustavoss/dx-connect/issues/9101"},
    )
    impl = client.post(f"/v1/saas/solicitacoes/{saas_id}/implementar", headers=h, json={})
    assert impl.status_code == 200, impl.text
    r_status = client.patch(
        f"/v1/saas/solicitacoes/{saas_id}/status",
        headers=h,
        json={"status": "concluida"},
    )
    assert r_status.status_code == 200, r_status.text
    r = client.post(
        f"/v1/solicitacoes-melhoria/{sid}/comentarios",
        headers=auth_headers["a1"],
        json={"corpo": "Obrigado!", "publico_cliente": True},
    )
    assert r.status_code == 400


def test_github_sem_config_503(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "GITHUB_TOKEN", None)
    monkeypatch.setattr(settings, "GITHUB_REPO_SUGESTOES", None)
    sid = _criar(client, auth_headers["a1"]).json()["id"]
    r = client.post(f"/v1/solicitacoes-melhoria/{sid}/github", headers=auth_headers["admin"])
    assert r.status_code == 503


def test_admin_lista_filtra(client, seed_base, auth_headers):
    _criar(client, auth_headers["a1"], tipo="problema", titulo="Bug no PDF export")
    r = client.get("/v1/solicitacoes-melhoria/admin?tipo=problema", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert all(i["tipo"] == "problema" for i in r.json())
    denied = client.get("/v1/solicitacoes-melhoria/admin", headers=auth_headers["a1"])
    assert denied.status_code == 403


_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_upload_imagem_inline_criar_e_servir(client, seed_base, auth_headers, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "SOLICITACAO_MEDIA_DIR", str(tmp_path))
    up = client.post(
        "/v1/solicitacoes-melhoria/media",
        headers=auth_headers["a1"],
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline"},
    )
    assert up.status_code == 201, up.text
    anexo = up.json()
    assert anexo["papel"] == "inline"
    assert anexo["url"].startswith("/v1/solicitacoes-melhoria/media/")

    criado = _criar(
        client,
        auth_headers["a1"],
        descricao=f"Passo 1: ecrã inicial.\n\n![print]({anexo['url']})\n\nPasso 2: erro.",
        anexo_ids=[anexo["id"]],
    )
    assert criado.status_code == 200, criado.text
    body = criado.json()
    assert len(body["anexos"]) == 1
    assert "print" in body["descricao"]

    media = client.get(anexo["url"])
    assert media.status_code == 200
    assert media.content == _PNG_1X1


def test_upload_pdf_anexo(client, seed_base, auth_headers, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "SOLICITACAO_MEDIA_DIR", str(tmp_path))
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    up = client.post(
        "/v1/solicitacoes-melhoria/media",
        headers=auth_headers["a1"],
        files={"file": ("relatorio.pdf", pdf, "application/pdf")},
        data={"papel": "anexo"},
    )
    assert up.status_code == 201, up.text
    assert up.json()["papel"] == "anexo"
    media = client.get(up.json()["url"])
    assert media.status_code == 200
    assert media.headers["content-type"].startswith("application/pdf")


def test_upload_exe_rejeitado(client, seed_base, auth_headers, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "SOLICITACAO_MEDIA_DIR", str(tmp_path))
    r = client.post(
        "/v1/solicitacoes-melhoria/media",
        headers=auth_headers["a1"],
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/x-msdownload")},
        data={"papel": "anexo"},
    )
    assert r.status_code == 400


def test_upload_pdf_como_inline_rejeitado(client, seed_base, auth_headers, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "SOLICITACAO_MEDIA_DIR", str(tmp_path))
    pdf = b"%PDF-1.4\n%%EOF\n"
    r = client.post(
        "/v1/solicitacoes-melhoria/media",
        headers=auth_headers["a1"],
        files={"file": ("doc.pdf", pdf, "application/pdf")},
        data={"papel": "inline"},
    )
    assert r.status_code == 400


def test_upload_media_exige_auth(client, seed_base):
    r = client.post(
        "/v1/solicitacoes-melhoria/media",
        files={"file": ("print.png", _PNG_1X1, "image/png")},
        data={"papel": "inline"},
    )
    assert r.status_code == 401
