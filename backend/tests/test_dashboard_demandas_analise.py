"""Análise operacional de demandas WhatsApp (#594)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.models.whatsapp_chat import WhatsappChat
from app.models.whatsapp_chat_demanda import WhatsappChatDemanda
from app.services.dashboard_chats import clear_dashboard_chats_cache
from app.services.dashboard_demandas_analise import (
    LIMIAR_INSIGHT_DUVIDA,
    LIMIAR_INSIGHT_ERRO,
    LIMIAR_SUGESTAO_OUTROS,
    normalizar_descricao_demanda,
)


def _nat_motivo(db_session, *, nat_slug: str, nat_nome: str, mot_slug: str, mot_nome: str):
    nat = TicketNatureza(nome=nat_nome, slug=nat_slug, ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(
        natureza_id=nat.id, nome=mot_nome, slug=mot_slug, ordem=1, ativo=True
    )
    db_session.add(mot)
    db_session.commit()
    return nat, mot


def _chat(db_session, seed_base, *, empresa_id=None, setor_id=None, suf="x"):
    c = WhatsappChat(
        protocolo=f"W-{suf}-{datetime.now().timestamp()}",
        wa_id=f"5511888{suf}",
        estado="encerrado",
        setor_id=setor_id or seed_base["setor1"].id,
        empresa_id=empresa_id if empresa_id is not None else seed_base["empresa"].id,
        cliente_nome=f"Cliente {suf}",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def _demanda(db_session, chat, nat, mot=None, *, desc=None):
    d = WhatsappChatDemanda(
        chat_id=chat.id,
        natureza_id=nat.id,
        motivo_id=mot.id if mot else None,
        desfecho="resolvido_sessao",
        descricao_curta=desc,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(d)
    db_session.commit()
    return d


def test_normalizar_descricao_demanda():
    assert normalizar_descricao_demanda("  Foo   BAR ") == "foo bar"
    assert normalizar_descricao_demanda("   ") is None


def test_drilldown_e_ranking_por_empresa(client, seed_base, auth_headers, db_session):
    clear_dashboard_chats_cache()
    nat, mot = _nat_motivo(
        db_session, nat_slug="erro", nat_nome="Erro", mot_slug="bug-x", mot_nome="Bug X"
    )
    c1 = _chat(db_session, seed_base, suf="r1")
    c2 = _chat(db_session, seed_base, suf="r2")
    _demanda(db_session, c1, nat, mot)
    _demanda(db_session, c2, nat, mot)

    hoje = date.today().isoformat()
    lista = client.get(
        f"/v1/dashboard/chats/demandas?de={hoje}&ate={hoje}&natureza_id={nat.id}",
        headers=auth_headers["admin"],
    )
    assert lista.status_code == 200
    body = lista.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert {i["chat_id"] for i in body["items"]} == {c1.id, c2.id}

    dash = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}",
        headers=auth_headers["admin"],
    ).json()
    assert dash["demanda_maior"]["id"] == nat.id
    assert dash["demanda_maior"]["total"] == 2
    assert any(e["empresa_id"] == seed_base["empresa"].id and e["total"] >= 2 for e in dash["demandas_por_empresa"])


def test_insights_erro_e_duvida(client, seed_base, auth_headers, db_session):
    clear_dashboard_chats_cache()
    nat_erro, mot_erro = _nat_motivo(
        db_session, nat_slug="erro", nat_nome="Erro", mot_slug="falha", mot_nome="Falha"
    )
    nat_duv, mot_duv = _nat_motivo(
        db_session, nat_slug="duvida", nat_nome="Dúvida", mot_slug="login", mot_nome="Login"
    )
    for i in range(LIMIAR_INSIGHT_ERRO):
        c = _chat(db_session, seed_base, suf=f"e{i}")
        _demanda(db_session, c, nat_erro, mot_erro)
    for i in range(LIMIAR_INSIGHT_DUVIDA):
        c = _chat(db_session, seed_base, suf=f"d{i}")
        _demanda(db_session, c, nat_duv, mot_duv)

    hoje = date.today().isoformat()
    dash = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}",
        headers=auth_headers["admin"],
    ).json()
    tipos = {i["tipo"] for i in dash["insights_demandas"]}
    assert "avaliar_atualizacao" in tipos
    assert "sugerir_treinamento" in tipos


def test_sugestao_outros_aceitar_e_ignorar(client, seed_base, auth_headers, db_session):
    clear_dashboard_chats_cache()
    nat, _ = _nat_motivo(
        db_session, nat_slug="solicitacao", nat_nome="Solicitação", mot_slug="x", mot_nome="X"
    )
    outros = TicketMotivo(
        natureza_id=nat.id, nome="Outros", slug="outros", ordem=99, ativo=True
    )
    db_session.add(outros)
    db_session.commit()

    texto = "Precisa emitir 2ª via do boleto"
    for i in range(LIMIAR_SUGESTAO_OUTROS):
        c = _chat(db_session, seed_base, suf=f"o{i}")
        _demanda(db_session, c, nat, outros, desc=texto if i % 2 == 0 else f"  {texto.upper()}  ")

    hoje = date.today().isoformat()
    dash = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}",
        headers=auth_headers["admin"],
    ).json()
    sugs = dash["sugestoes_motivo_outros"]
    assert len(sugs) >= 1
    sug = next(s for s in sugs if "boleto" in s["texto_normalizado"])
    assert sug["ocorrencias"] >= LIMIAR_SUGESTAO_OUTROS

    aceitar = client.post(
        "/v1/dashboard/chats/demandas/sugestoes-motivo/aceitar",
        json={
            "natureza_id": sug["natureza_id"],
            "texto_normalizado": sug["texto_normalizado"],
            "nome": "2ª via de boleto",
        },
        headers=auth_headers["admin"],
    )
    assert aceitar.status_code == 200
    assert aceitar.json()["nome"] == "2ª via de boleto"
    assert aceitar.json()["natureza_id"] == nat.id

    dash2 = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}",
        headers=auth_headers["admin"],
    ).json()
    assert not any(s["texto_normalizado"] == sug["texto_normalizado"] for s in dash2["sugestoes_motivo_outros"])

    # segunda descrição para ignorar
    texto2 = "Relatório mensal customizado"
    for i in range(LIMIAR_SUGESTAO_OUTROS):
        c = _chat(db_session, seed_base, suf=f"ig{i}")
        _demanda(db_session, c, nat, outros, desc=texto2)

    clear_dashboard_chats_cache()
    dash3 = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}",
        headers=auth_headers["admin"],
    ).json()
    sug2 = next(s for s in dash3["sugestoes_motivo_outros"] if "relatorio" in s["texto_normalizado"])
    ign = client.post(
        "/v1/dashboard/chats/demandas/sugestoes-motivo/ignorar",
        json={
            "natureza_id": sug2["natureza_id"],
            "texto_normalizado": sug2["texto_normalizado"],
            "texto_exemplo": sug2["texto_exemplo"],
        },
        headers=auth_headers["admin"],
    )
    assert ign.status_code == 204

    clear_dashboard_chats_cache()
    dash4 = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}",
        headers=auth_headers["admin"],
    ).json()
    assert not any(s["texto_normalizado"] == sug2["texto_normalizado"] for s in dash4["sugestoes_motivo_outros"])


def test_atendente_nao_aceita_sugestao(client, seed_base, auth_headers, db_session):
    nat, _ = _nat_motivo(
        db_session, nat_slug="solicitacao-a", nat_nome="Sol A", mot_slug="xa", mot_nome="Xa"
    )
    r = client.post(
        "/v1/dashboard/chats/demandas/sugestoes-motivo/aceitar",
        json={"natureza_id": nat.id, "texto_normalizado": "algo"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 403
