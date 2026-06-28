"""Paridade entre /notificacoes/resumo e /notificacoes/itens (#391)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.api.notificacoes import build_notificacao_itens, build_notificacao_resumo
from app.models.ticket import Ticket, TicketMensagem
from app.models.ticket_read import TicketRead


def _criar_ticket_com_mensagem(db_session, seed_base, *, atendente_id: int, assunto: str = "Teste notif"):
    from app.models.status_ticket import StatusTicket

    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo=f"#T-NOTIF-{assunto[:8]}",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto=assunto,
        descricao="x",
        atendente_id=atendente_id,
    )
    db_session.add(ticket)
    db_session.flush()
    db_session.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=None,
            tipo="publico",
            corpo="Mensagem do cliente",
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    return ticket


def test_resumo_e_itens_parity_atendente(client, seed_base, auth_headers, db_session):
    _criar_ticket_com_mensagem(db_session, seed_base, atendente_id=seed_base["a1"].id)

    r_resumo = client.get("/v1/notificacoes/resumo", headers=auth_headers["a1"])
    assert r_resumo.status_code == 200
    resumo = r_resumo.json()

    r_itens = client.get("/v1/notificacoes/itens", headers=auth_headers["a1"])
    assert r_itens.status_code == 200
    itens = r_itens.json()["itens"]

    assert resumo["nao_lidas_count"] >= 1
    assert any(i["tipo"] == "mensagens_nao_lidas" for i in itens)


def test_admin_nao_conta_nao_lidas_de_outro_responsavel(client, seed_base, auth_headers, db_session):
    """Badge pessoal: admin não acumula não-lidas de tickets de outros atendentes."""
    _criar_ticket_com_mensagem(db_session, seed_base, atendente_id=seed_base["a1"].id, assunto="Do A1")

    resumo_admin = build_notificacao_resumo(db_session, seed_base["admin"])
    assert resumo_admin.nao_lidas_count == 0

    resumo_a1 = build_notificacao_resumo(db_session, seed_base["a1"])
    assert resumo_a1.nao_lidas_count >= 1


def test_itens_link_directo_por_ticket(client, seed_base, auth_headers, db_session, monkeypatch):
    """Cada pendência de não-lida aponta para /tickets/{id}, nunca listagem genérica (#452)."""
    _criar_ticket_com_mensagem(db_session, seed_base, atendente_id=seed_base["a1"].id)

    def fake_unread(db, ticket, atendente_id):
        return 0

    monkeypatch.setattr("app.api.notificacoes._unread_count_for_ticket", fake_unread)

    resumo = build_notificacao_resumo(db_session, seed_base["a1"])
    itens = build_notificacao_itens(db_session, seed_base["a1"], limit=15)

    assert resumo.nao_lidas_count >= 1
    ticket_itens = [i for i in itens if i.tipo == "mensagens_nao_lidas"]
    assert len(ticket_itens) >= 1
    for item in ticket_itens:
        assert item.ticket_id is not None
        assert item.href == f"/tickets/{item.ticket_id}"
        assert "situacao=abertos" not in item.href


def test_varios_tickets_nao_lidos_links_individuais(client, seed_base, auth_headers, db_session):
    t1 = _criar_ticket_com_mensagem(db_session, seed_base, atendente_id=seed_base["a1"].id, assunto="Um")
    t2 = _criar_ticket_com_mensagem(db_session, seed_base, atendente_id=seed_base["a1"].id, assunto="Dois")

    itens = build_notificacao_itens(db_session, seed_base["a1"], limit=15)
    ticket_itens = [i for i in itens if i.tipo == "mensagens_nao_lidas"]
    hrefs = {i.href for i in ticket_itens}
    assert f"/tickets/{t1.id}" in hrefs
    assert f"/tickets/{t2.id}" in hrefs


def test_mensagem_anterior_a_visto_nao_conta(db_session, seed_base):
    from app.models.status_ticket import StatusTicket

    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T-NOTIF-VISTO",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Visto",
        descricao="x",
        atendente_id=seed_base["a1"].id,
    )
    db_session.add(ticket)
    db_session.flush()

    agora = datetime.now(timezone.utc)
    db_session.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=None,
            tipo="publico",
            corpo="Antiga",
            created_at=agora - timedelta(hours=1),
        )
    )
    db_session.add(
        TicketRead(
            atendente_id=seed_base["a1"].id,
            ticket_id=ticket.id,
            last_seen_at=agora,
        )
    )
    db_session.commit()

    resumo = build_notificacao_resumo(db_session, seed_base["a1"])
    assert resumo.nao_lidas_count == 0
