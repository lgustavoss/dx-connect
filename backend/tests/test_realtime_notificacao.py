"""Testes emissão notificacao.contagem (#266)."""

from __future__ import annotations

from app.api.notificacoes import build_notificacao_resumo
from app.services.realtime_emit import emit_notificacao_contagem


def test_build_notificacao_resumo(client, seed_base, db_session):
    r = build_notificacao_resumo(db_session, seed_base["a1"])
    assert r.sem_responsavel_count >= 0
    assert r.total_pendencias == (
        r.sem_responsavel_count
        + r.nao_lidas_count
        + r.wpp_fila_count
        + r.wpp_respostas_count
    )


def test_emit_notificacao_contagem_payload(client, seed_base, db_session, monkeypatch):
    publicados: list[tuple[int, str, dict]] = []

    def fake_publish(atendente_ids, event_type, payload):
        for aid in atendente_ids:
            publicados.append((aid, event_type, payload))

    monkeypatch.setattr("app.services.realtime_emit._publish_to_atendentes", fake_publish)

    emit_notificacao_contagem(db_session, [seed_base["a1"].id])

    assert len(publicados) == 1
    aid, etype, payload = publicados[0]
    assert aid == seed_base["a1"].id
    assert etype == "notificacao.contagem"
    assert "sem_responsavel_count" in payload
    assert "total_pendencias" in payload


def test_marcar_visto_emite_contagem(client, seed_base, auth_headers, db_session, monkeypatch):
    from app.models.ticket import Ticket
    from app.models.status_ticket import StatusTicket

    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-0099",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Visto SSE",
        descricao="x",
        atendente_id=seed_base["a1"].id,
    )
    db_session.add(ticket)
    db_session.commit()

    calls: list[int] = []

    def fake_emit(db, ids):
        calls.extend(ids)

    monkeypatch.setattr("app.services.realtime_emit.emit_notificacao_contagem", fake_emit)

    r = client.post(f"/v1/notificacoes/tickets/{ticket.id}/visto", headers=auth_headers["a1"])
    assert r.status_code == 204
    assert seed_base["a1"].id in calls
