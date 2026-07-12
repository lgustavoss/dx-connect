"""Notificações do chat interno no sino (IC-03)."""

from __future__ import annotations

from app.api.notificacoes import build_notificacao_itens, build_notificacao_resumo
from app.services import chat_interno as chat_svc


def _enviar_direta(db_session, seed_base, remetente, destino, corpo: str):
    conversa = chat_svc.obter_ou_criar_conversa_direta(db_session, 1, remetente.id, destino.id)
    chat_svc.enviar_mensagem(db_session, conversa, remetente, corpo)
    db_session.commit()
    return conversa


def test_resumo_inclui_chat_interno_nao_lidas(db_session, seed_base):
    _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Ping")

    resumo_admin = build_notificacao_resumo(db_session, seed_base["admin"])
    assert resumo_admin.chat_interno_nao_lidas_count == 1
    assert resumo_admin.total_pendencias >= 1

    resumo_a1 = build_notificacao_resumo(db_session, seed_base["a1"])
    assert resumo_a1.chat_interno_nao_lidas_count == 0


def test_itens_chat_interno_link_conversa(db_session, seed_base):
    conversa = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Olá")

    itens = build_notificacao_itens(db_session, seed_base["admin"], limit=15)
    chat_itens = [i for i in itens if i.tipo == "chat_interno"]
    assert len(chat_itens) >= 1
    item = chat_itens[0]
    assert item.conversa_id == conversa.id
    assert item.href == f"/chat/interno/{conversa.id}"
    assert item.count >= 1


def test_visto_zera_contador_chat_interno(client, seed_base, auth_headers, db_session):
    conversa = _enviar_direta(db_session, seed_base, seed_base["a1"], seed_base["admin"], "Teste visto")

    resumo_antes = build_notificacao_resumo(db_session, seed_base["admin"])
    assert resumo_antes.chat_interno_nao_lidas_count == 1

    r = client.post(
        f"/v1/chat-interno/conversas/{conversa.id}/visto",
        headers=auth_headers["admin"],
    )
    assert r.status_code == 204

    resumo_depois = build_notificacao_resumo(db_session, seed_base["admin"])
    assert resumo_depois.chat_interno_nao_lidas_count == 0
