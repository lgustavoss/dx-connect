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

    lista = client.get("/v1/solicitacoes-melhoria/minhas", headers=auth_headers["a1"])
    assert lista.status_code == 200
    assert any(i["id"] == data["id"] for i in lista.json())


def test_status_so_admin_e_motivo_obrigatorio(client, seed_base, auth_headers):
    sid = _criar(client, auth_headers["a1"]).json()["id"]

    denied = client.patch(
        f"/v1/solicitacoes-melhoria/{sid}/status",
        headers=auth_headers["a1"],
        json={"status": "em_analise"},
    )
    assert denied.status_code == 403

    bad = client.patch(
        f"/v1/solicitacoes-melhoria/{sid}/status",
        headers=auth_headers["admin"],
        json={"status": "nao_sera_desenvolvida"},
    )
    assert bad.status_code == 400

    ok = client.patch(
        f"/v1/solicitacoes-melhoria/{sid}/status",
        headers=auth_headers["admin"],
        json={
            "status": "nao_sera_desenvolvida",
            "motivo_nao_desenvolvimento": "Fora do roadmap deste trimestre.",
        },
    )
    assert ok.status_code == 200
    body = ok.json()
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
    assert admin_c.status_code == 200

    cliente_view = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["a1"]).json()
    corpos = [c["corpo"] for c in cliente_view["comentarios"]]
    assert "Posso dar mais detalhes" in "".join(corpos)
    assert "Nota interna" not in "".join(corpos)

    admin_view = client.get(f"/v1/solicitacoes-melhoria/{sid}", headers=auth_headers["admin"]).json()
    assert any("Nota interna" in c["corpo"] for c in admin_view["comentarios"])


def test_a2_nao_comenta_solicitacao_de_a1(client, seed_base, auth_headers):
    sid = _criar(client, auth_headers["a1"]).json()["id"]
    # Mesma org (tenant) — pode ler, mas só autor responde
    r = client.post(
        f"/v1/solicitacoes-melhoria/{sid}/comentarios",
        headers=auth_headers["a2"],
        json={"corpo": "Eu também quero isto", "publico_cliente": True},
    )
    assert r.status_code == 403


def test_status_final_bloqueia_resposta_cliente(client, seed_base, auth_headers):
    sid = _criar(client, auth_headers["a1"]).json()["id"]
    client.patch(
        f"/v1/solicitacoes-melhoria/{sid}/status",
        headers=auth_headers["admin"],
        json={"status": "concluida"},
    )
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
