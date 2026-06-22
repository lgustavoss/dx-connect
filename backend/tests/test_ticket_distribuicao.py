"""Testes de distribuição automática de tickets (#257)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Setor, Ticket, TicketHistorico
from app.models.atendente_notificacao import NotificacaoEmailOutbox
from app.models.setor_distribuicao_round_robin import SetorDistribuicaoRoundRobin
from app.services.ticket_distribuicao import (
    CAMPO_HISTORICO_DISTRIBUICAO_AUTOMATICA,
    TEXTO_HISTORICO_DISTRIBUICAO_AUTOMATICA,
    atribuir_ticket_automaticamente,
    processar_distribuicao_timeout,
    tentar_distribuicao_imediata,
)


def _criar_ticket_fila(db, seed_base, *, setor_id=None, fila_desde_at=None):
    setor_id = setor_id or seed_base["setor1"].id
    t = Ticket(
        tenant_id=1,
        protocolo=f"T-TEST-{db.query(Ticket).count() + 1}",
        empresa_id=seed_base["empresa"].id,
        rede_id=seed_base["rede"].id,
        setor_id=setor_id,
        status_id=seed_base["status"].id,
        assunto="Teste fila",
        fila_desde_at=fila_desde_at or datetime.now(timezone.utc),
    )
    db.add(t)
    db.flush()
    return t


def _criar_ticket_aberto_atribuido(db, seed_base, atendente_id, *, setor_id=None):
    setor_id = setor_id or seed_base["setor1"].id
    t = Ticket(
        tenant_id=1,
        protocolo=f"T-LOAD-{db.query(Ticket).count() + 1}",
        empresa_id=seed_base["empresa"].id,
        rede_id=seed_base["rede"].id,
        setor_id=setor_id,
        status_id=seed_base["status"].id,
        assunto="Carga",
        atendente_id=atendente_id,
    )
    db.add(t)
    db.flush()
    return t


def _vincular_ao_setor(db, atendente, setor):
    if setor not in atendente.setores:
        atendente.setores.append(setor)
        db.flush()


def test_put_distribuicao_setor(client, seed_base, auth_headers, db_session):
    setor_id = seed_base["setor1"].id
    r = client.put(
        f"/v1/setores/{setor_id}/distribuicao",
        headers=auth_headers["admin"],
        json={
            "modo": "auto_apos_timeout",
            "timeout_minutos": 15,
            "estrategia": "round_robin",
            "atendentes_elegiveis": None,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["modo"] == "auto_apos_timeout"
    assert body["timeout_minutos"] == 15

    s = db_session.query(Setor).filter(Setor.id == setor_id).first()
    db_session.refresh(s)
    assert s.distribuicao_modo == "auto_apos_timeout"
    assert s.distribuicao_timeout_minutos == 15


def test_distribuicao_imediata_round_robin(client, seed_base, auth_headers, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    setor.distribuicao_estrategia = "round_robin"
    db_session.commit()

    t1 = _criar_ticket_fila(db_session, seed_base)
    t2 = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()

    assert tentar_distribuicao_imediata(db_session, t1) is True
    db_session.commit()
    assert t1.atendente_id == seed_base["a1"].id

    assert tentar_distribuicao_imediata(db_session, t2) is True
    db_session.commit()
    assert t2.atendente_id == seed_base["a1"].id

    state = db_session.query(SetorDistribuicaoRoundRobin).filter(SetorDistribuicaoRoundRobin.setor_id == setor.id).first()
    assert state is not None
    assert state.last_atendente_id == seed_base["a1"].id


def test_distribuicao_nao_atribui_admin(db_session, seed_base):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    admin = seed_base["admin"]
    admin.setores.append(setor)
    db_session.commit()

    ticket = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()

    ok = atribuir_ticket_automaticamente(db_session, ticket, setor)
    db_session.commit()
    assert ok == seed_base["a1"].id
    assert ticket.atendente_id != admin.id


def test_worker_timeout_atribui(client, seed_base, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_apos_timeout"
    setor.distribuicao_timeout_minutos = 5
    db_session.commit()

    antigo = datetime.now(timezone.utc) - timedelta(minutes=10)
    ticket = _criar_ticket_fila(db_session, seed_base, fila_desde_at=antigo)
    db_session.commit()

    n = processar_distribuicao_timeout(db_session, limit=10)
    db_session.commit()
    assert n == 1
    db_session.refresh(ticket)
    assert ticket.atendente_id == seed_base["a1"].id

    hist = (
        db_session.query(TicketHistorico)
        .filter(TicketHistorico.ticket_id == ticket.id, TicketHistorico.campo == "atendente_id")
        .first()
    )
    assert hist is not None
    assert hist.valor_novo == str(seed_base["a1"].id)


def test_atribuicao_automatica_notifica(client, seed_base, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    ticket = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()

    atribuir_ticket_automaticamente(db_session, ticket, setor)
    db_session.commit()

    outbox = (
        db_session.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.ticket_id == ticket.id,
            NotificacaoEmailOutbox.tipo == "ticket_atribuido",
        )
        .first()
    )
    assert outbox is not None


def test_criar_ticket_auto_imediato_via_api(client, seed_base, auth_headers, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": setor.id,
            "assunto": "Novo com auto",
            "descricao": "Corpo",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["atendente_id"] == seed_base["a1"].id


def test_listagem_sem_responsavel_ordenada_por_fila(client, seed_base, auth_headers, db_session):
    """#273: fila sem responsável — mais antigos na fila primeiro."""
    agora = datetime.now(timezone.utc)
    t_antigo = _criar_ticket_fila(
        db_session,
        seed_base,
        fila_desde_at=agora - timedelta(hours=2),
    )
    t_recente = _criar_ticket_fila(
        db_session,
        seed_base,
        fila_desde_at=agora - timedelta(minutes=10),
    )
    db_session.commit()

    r = client.get(
        "/v1/tickets",
        headers=auth_headers["admin"],
        params={"sem_responsavel": True, "situacao": "abertos", "limit": 50},
    )
    assert r.status_code == 200, r.text
    ids = [x["id"] for x in r.json()["items"] if x["id"] in (t_antigo.id, t_recente.id)]
    assert ids == [t_antigo.id, t_recente.id]


def test_listagem_ordenar_por_fila_desde_at(client, seed_base, auth_headers, db_session):
    agora = datetime.now(timezone.utc)
    t1 = _criar_ticket_fila(db_session, seed_base, fila_desde_at=agora - timedelta(hours=1))
    t2 = _criar_ticket_fila(db_session, seed_base, fila_desde_at=agora - timedelta(hours=3))
    db_session.commit()

    r = client.get(
        "/v1/tickets",
        headers=auth_headers["admin"],
        params={
            "sem_responsavel": True,
            "situacao": "abertos",
            "ordenar_por": "fila_desde_at",
            "ordem": "desc",
            "limit": 50,
        },
    )
    assert r.status_code == 200, r.text
    ids = [x["id"] for x in r.json()["items"] if x["id"] in (t1.id, t2.id)]
    assert ids == [t1.id, t2.id]


def test_distribuicao_menor_carga_abertos(db_session, seed_base):
    setor = seed_base["setor1"]
    a1, a2 = seed_base["a1"], seed_base["a2"]
    _vincular_ao_setor(db_session, a2, setor)
    setor.distribuicao_modo = "auto_imediato"
    setor.distribuicao_estrategia = "menor_carga_abertos"
    db_session.commit()

    for _ in range(3):
        _criar_ticket_aberto_atribuido(db_session, seed_base, a1.id, setor_id=setor.id)
    _criar_ticket_aberto_atribuido(db_session, seed_base, a1.id, setor_id=seed_base["setor2"].id)
    db_session.commit()

    novo = _criar_ticket_fila(db_session, seed_base, setor_id=setor.id)
    db_session.commit()
    assert tentar_distribuicao_imediata(db_session, novo) is True
    db_session.commit()
    assert novo.atendente_id == a2.id


def test_distribuicao_menor_carga_setor(db_session, seed_base):
    setor = seed_base["setor1"]
    a1, a2 = seed_base["a1"], seed_base["a2"]
    _vincular_ao_setor(db_session, a2, setor)
    setor.distribuicao_modo = "auto_imediato"
    setor.distribuicao_estrategia = "menor_carga_setor"
    db_session.commit()

    for _ in range(2):
        _criar_ticket_aberto_atribuido(db_session, seed_base, a1.id, setor_id=setor.id)
    for _ in range(4):
        _criar_ticket_aberto_atribuido(db_session, seed_base, a2.id, setor_id=seed_base["setor2"].id)
    db_session.commit()

    novo = _criar_ticket_fila(db_session, seed_base, setor_id=setor.id)
    db_session.commit()
    assert tentar_distribuicao_imediata(db_session, novo) is True
    db_session.commit()
    assert novo.atendente_id == a2.id


def test_historico_atribuicao_automatica(db_session, seed_base):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    ticket = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()
    atribuir_ticket_automaticamente(db_session, ticket, setor)
    db_session.commit()

    hist = (
        db_session.query(TicketHistorico)
        .filter(TicketHistorico.ticket_id == ticket.id)
        .order_by(TicketHistorico.id.asc())
        .all()
    )
    campos = [h.campo for h in hist]
    assert "atendente_id" in campos
    assert CAMPO_HISTORICO_DISTRIBUICAO_AUTOMATICA in campos
    auto = next(h for h in hist if h.campo == CAMPO_HISTORICO_DISTRIBUICAO_AUTOMATICA)
    assert auto.valor_novo == TEXTO_HISTORICO_DISTRIBUICAO_AUTOMATICA


def test_distribuicao_exclui_atendente_inativo(db_session, seed_base):
    setor = seed_base["setor1"]
    a1, a2 = seed_base["a1"], seed_base["a2"]
    _vincular_ao_setor(db_session, a2, setor)
    a1.ativo = False
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    ticket = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()
    assert atribuir_ticket_automaticamente(db_session, ticket, setor) == a2.id
    db_session.commit()
    assert ticket.atendente_id == a2.id
