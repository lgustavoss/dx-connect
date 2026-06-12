from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.models.email_inbound_received import EmailInboundReceived
from app.models import StatusTicket
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.models.ticket import Ticket
from app.models.ticket_avaliacao import TicketAvaliacao, TicketCsatInvite
from app.models.whatsapp_chat import WhatsappChat


def _status_fechado(db_session) -> StatusTicket:
    st = db_session.query(StatusTicket).filter(StatusTicket.slug == "fechado").first()
    if st:
        return st
    st = StatusTicket(nome="Fechado", slug="fechado", ordem=99, ativo=True)
    db_session.add(st)
    db_session.commit()
    db_session.refresh(st)
    return st


def _seed_motivo(db_session) -> TicketMotivo:
    n = TicketNatureza(nome="Erro CSAT", slug="erro-csat", ordem=10, ativo=True)
    db_session.add(n)
    db_session.flush()
    m = TicketMotivo(natureza_id=n.id, nome="Teste CSAT", slug="teste-csat", ordem=10, ativo=True)
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


def _fechar_ticket(client, auth_headers, tid: int, status_fechado: StatusTicket, motivo: TicketMotivo):
    r = client.patch(
        f"/v1/tickets/{tid}",
        headers=auth_headers["admin"],
        json={"status_id": status_fechado.id, "motivo_id": motivo.id},
    )
    assert r.status_code == 200, r.text
    return r


def _criar_ticket(client, seed_base, auth_headers):
    ticket = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Ticket CSAT teste",
            "descricao": "Teste",
        },
    )
    assert ticket.status_code == 201
    return ticket.json()["id"]


def test_csat_convite_ao_fechar_ticket_com_email(client, seed_base, auth_headers, db_session, monkeypatch):
    sent = []

    def fake_send(db, *, to_addr, subject, body, in_reply_to=None):
        sent.append({"to": to_addr, "subject": subject, "body": body})
        return "<out-mid@test>"

    monkeypatch.setattr("app.services.ticket_csat.enviar_mensagem_texto_sistema", fake_send)

    tid = _criar_ticket(client, seed_base, auth_headers)
    db_session.add(
        EmailInboundReceived(
            message_id_normalized="csat-inbound-1",
            ticket_id=tid,
            from_address="Cliente Teste <cliente.csat@test.local>",
            subject="Ticket CSAT teste",
        )
    )
    db_session.commit()

    status_fechado = _status_fechado(db_session)
    motivo = _seed_motivo(db_session)
    _fechar_ticket(client, auth_headers, tid, status_fechado, motivo)

    invite = db_session.query(TicketCsatInvite).filter(TicketCsatInvite.ticket_id == tid).first()
    assert invite is not None
    assert len(sent) == 1
    assert "cliente.csat@test.local" in sent[0]["to"]


def test_csat_sem_email_nao_cria_convite(client, seed_base, auth_headers, db_session):
    tid = _criar_ticket(client, seed_base, auth_headers)
    status_fechado = _status_fechado(db_session)
    motivo = _seed_motivo(db_session)
    _fechar_ticket(client, auth_headers, tid, status_fechado, motivo)
    invite = db_session.query(TicketCsatInvite).filter(TicketCsatInvite.ticket_id == tid).first()
    assert invite is None


def test_csat_publico_registrar_nota(client, seed_base, auth_headers, db_session):
    tid = _criar_ticket(client, seed_base, auth_headers)
    db_session.add(
        EmailInboundReceived(
            message_id_normalized="csat-pub-in",
            ticket_id=tid,
            from_address="cliente.pub@test.local",
            subject="Assunto",
        )
    )
    ticket = db_session.query(Ticket).filter(Ticket.id == tid).first()
    ticket.fechado_em = datetime.now(timezone.utc)
    db_session.commit()

    raw = secrets.token_urlsafe(32)
    invite = TicketCsatInvite(
        ticket_id=tid,
        atendente_id=seed_base["a1"].id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(invite)
    db_session.commit()

    get_r = client.get(f"/v1/public/csat/tickets/{raw}")
    assert get_r.status_code == 200
    assert get_r.json()["status"] == "pendente"

    post_r = client.post(
        f"/v1/public/csat/tickets/{raw}",
        json={"nota": 5, "comentario": "Ótimo atendimento"},
    )
    assert post_r.status_code == 200
    assert post_r.json()["status"] == "respondido"
    assert post_r.json()["nota"] == 5

    aval = db_session.query(TicketAvaliacao).filter(TicketAvaliacao.ticket_id == tid).first()
    assert aval is not None
    assert aval.nota == 5


def test_csat_link_dev_sem_email(client, seed_base, auth_headers, db_session):
    tid = _criar_ticket(client, seed_base, auth_headers)
    status_fechado = _status_fechado(db_session)
    motivo = _seed_motivo(db_session)
    _fechar_ticket(client, auth_headers, tid, status_fechado, motivo)

    r = client.post(f"/v1/tickets/{tid}/csat/link-dev", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["link"].startswith("http")
    assert "token=" in body["link"]

    token = body["link"].split("token=")[-1]
    post_r = client.post(f"/v1/public/csat/tickets/{token}", json={"nota": 3})
    assert post_r.status_code == 200
    assert post_r.json()["nota"] == 3


def test_metricas_avaliacoes_atendente(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    tid = _criar_ticket(client, seed_base, auth_headers)
    db_session.add(
        WhatsappChat(
            protocolo="WPP-CSAT-1",
            wa_id="5511999000001",
            estado="encerrado",
            atendente_id=a1.id,
            avaliacao_nota=5,
        )
    )
    db_session.add(
        TicketAvaliacao(
            ticket_id=tid,
            atendente_id=a1.id,
            nota=3,
        )
    )
    db_session.commit()

    r = client.get(f"/v1/atendentes/{a1.id}/avaliacoes", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["whatsapp"]["total"] == 1
    assert body["tickets"]["total"] == 1
    assert body["geral"]["total"] == 2
