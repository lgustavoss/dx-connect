"""Chat interno — janela de edição, apagar para mim e limpar conversa."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import chat_interno as chat_svc


def _enviar_direta(db_session, seed_base, remetente, destino, corpo: str):
    conversa = chat_svc.obter_ou_criar_conversa_direta(db_session, 1, remetente.id, destino.id)
    mensagem = chat_svc.enviar_mensagem(db_session, conversa, remetente, corpo)
    db_session.commit()
    return conversa, mensagem


def test_editar_mensagem_autor(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Original")

    r = client.patch(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}",
        headers=auth_headers["a1"],
        json={"corpo": "Corrigido"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["corpo"] == "Corrigido"
    assert data["editada"] is True
    assert data["pode_editar"] is True


def test_editar_mensagem_403_outro_atendente(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Original")

    r = client.patch(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}",
        headers=auth_headers["a2"],
        json={"corpo": "Tentativa"},
    )
    assert r.status_code == 403


def test_admin_nao_edita_mensagem_alheia(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Original")

    r = client.patch(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}",
        headers=auth_headers["admin"],
        json={"corpo": "Admin corrigiu"},
    )
    assert r.status_code == 403


def test_editar_bloqueado_apos_janela(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Original")
    mensagem.created_at = datetime.now(timezone.utc) - timedelta(minutes=6)
    db_session.commit()

    r = client.patch(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}",
        headers=auth_headers["a1"],
        json={"corpo": "Tarde"},
    )
    assert r.status_code == 400


def test_apagar_mensagem_para_todos(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Apagar isso")

    r = client.delete(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}?escopo=todos",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    data = r.json()
    assert data["apagada"] is True
    assert data["corpo"] == chat_svc.CORPO_MENSAGEM_APAGADA

    r_admin = client.get(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens",
        headers=auth_headers["admin"],
    )
    assert r_admin.json()["items"][0]["apagada"] is True


def test_apagar_para_mim_oculta_somente_autor(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Só para mim")

    r = client.delete(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}?escopo=para_mim",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 204

    r_a1 = client.get(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens",
        headers=auth_headers["a1"],
    )
    assert r_a1.json()["total"] == 0

    r_admin = client.get(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens",
        headers=auth_headers["admin"],
    )
    assert r_admin.json()["total"] == 1
    assert r_admin.json()["items"][0]["corpo"] == "Só para mim"


def test_apagar_para_todos_bloqueado_apos_janela(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Velha")
    mensagem.created_at = datetime.now(timezone.utc) - timedelta(minutes=6)
    db_session.commit()

    r = client.delete(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}?escopo=todos",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 400

    r_ok = client.delete(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}?escopo=para_mim",
        headers=auth_headers["a1"],
    )
    assert r_ok.status_code == 204


def test_limpar_conversa_somente_para_quem_limpou(client, seed_base, auth_headers, db_session):
    conversa, _ = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Msg 1")
    chat_svc.enviar_mensagem(db_session, conversa, seed_base["admin"], "Msg 2")
    db_session.commit()

    r = client.post(
        f"/v1/chat-interno/conversas/{conversa.id}/limpar",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 204

    r_a1 = client.get(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens",
        headers=auth_headers["a1"],
    )
    assert r_a1.json()["total"] == 0

    r_admin = client.get(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens",
        headers=auth_headers["admin"],
    )
    assert r_admin.json()["total"] == 2

    r_inbox_a1 = client.get("/v1/chat-interno/conversas", headers=auth_headers["a1"])
    assert all(c["id"] != conversa.id for c in r_inbox_a1.json())

    r_inbox_admin = client.get("/v1/chat-interno/conversas", headers=auth_headers["admin"])
    assert any(c["id"] == conversa.id for c in r_inbox_admin.json())


def test_reacao_toggle_e_remover(client, seed_base, auth_headers, db_session):
    conversa, mensagem = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Reagir")

    r1 = client.put(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}/reacoes",
        headers=auth_headers["admin"],
        json={"emoji": "👍"},
    )
    assert r1.status_code == 200

    r_del = client.delete(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}?escopo=todos",
        headers=auth_headers["a1"],
    )
    assert r_del.status_code == 200

    r = client.put(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}/reacoes",
        headers=auth_headers["admin"],
        json={"emoji": "👍"},
    )
    assert r.status_code == 400


def test_apagar_mensagem_midia_bloqueia_download(client, seed_base, auth_headers, db_session):
    conversa = chat_svc.obter_ou_criar_conversa_direta(db_session, 1, seed_base["a1"].id, seed_base["admin"].id)
    mensagem = chat_svc.enviar_mensagem(db_session, conversa, seed_base["a1"], "texto placeholder")
    mensagem.tipo_midia = chat_svc.TIPO_MENSAGEM_IMAGEM
    mensagem.storage_key = "fake/key"
    db_session.commit()

    r_del = client.delete(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}?escopo=todos",
        headers=auth_headers["a1"],
    )
    assert r_del.status_code == 200

    r_dl = client.get(
        f"/v1/chat-interno/conversas/{conversa.id}/mensagens/{mensagem.id}/download",
        headers=auth_headers["admin"],
    )
    assert r_dl.status_code == 404
