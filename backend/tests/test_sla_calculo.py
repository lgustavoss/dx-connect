"""Testes cálculo SLA e horário comercial (#278)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.business_calendar import CalendarConfig, add_business_minutes, business_minutes_between
from app.models.business_calendar import BusinessCalendar
from app.models.sla_policy import SlaPolicy
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketHistorico, TicketMensagem
from app.services.sla_calculo import (
    SlaMetaEstado,
    avaliar_meta,
    build_ticket_sla_read,
    mensagem_conta_primeira_resposta,
    processar_sla_tickets_abertos,
    registrar_primeira_resposta_se_necessario,
)
from app.services.sla_policy import aplicar_sla_snapshot_ao_ticket


def _horario_comercial_semana() -> str:
    dia = {"ativo": True, "inicio": "09:00", "fim": "18:00"}
    return json.dumps(
        {
            "seg": dia,
            "ter": dia,
            "qua": dia,
            "qui": dia,
            "sex": dia,
            "sab": {"ativo": False},
            "dom": {"ativo": False},
        }
    )


def test_add_business_minutes_sexta_18h_pausa_ate_segunda():
    config = CalendarConfig(
        timezone_name="America/Sao_Paulo",
        horario_semana_json=_horario_comercial_semana(),
    )
    tz = ZoneInfo("America/Sao_Paulo")
    # 2026-06-19 é sexta-feira
    start = datetime(2026, 6, 19, 18, 0, tzinfo=tz)
    result = add_business_minutes(start, 60, config)
    expected = datetime(2026, 6, 22, 10, 0, tzinfo=tz)
    assert result.astimezone(tz) == expected


def test_business_minutes_between_respeita_fim_de_semana():
    config = CalendarConfig(
        timezone_name="America/Sao_Paulo",
        horario_semana_json=_horario_comercial_semana(),
    )
    tz = ZoneInfo("America/Sao_Paulo")
    start = datetime(2026, 6, 19, 17, 0, tzinfo=tz)
    end = datetime(2026, 6, 22, 10, 0, tzinfo=tz)
    # 1h sexta (17-18) + 1h segunda (9-10)
    assert business_minutes_between(start, end, config) == 120


def test_snapshot_com_calendario_comercial(db_session, seed_base):
    cal = BusinessCalendar(
        tenant_id=1,
        nome="Comercial",
        horario_semana_json=_horario_comercial_semana(),
        horario_timezone="America/Sao_Paulo",
    )
    db_session.add(cal)
    db_session.flush()
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade="alta",
        business_calendar_id=cal.id,
        meta_primeira_resposta_min=60,
        meta_resolucao_min=480,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()

    from app.models.status_ticket import StatusTicket

    st = db_session.query(StatusTicket).first()
    tz = ZoneInfo("America/Sao_Paulo")
    base = datetime(2026, 6, 19, 18, 0, tzinfo=tz)
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA2",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="SLA calendário",
        prioridade="alta",
        created_at=base.astimezone(timezone.utc),
    )
    db_session.add(ticket)
    db_session.flush()
    aplicar_sla_snapshot_ao_ticket(db_session, ticket, base_time=base.astimezone(timezone.utc))
    assert ticket.sla_primeira_resposta_vence_em is not None
    vence = ticket.sla_primeira_resposta_vence_em.astimezone(tz)
    assert vence == datetime(2026, 6, 22, 10, 0, tzinfo=tz)


def test_prioridade_alta_usa_policy_especifica(db_session, seed_base):
    padrao = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade=None,
        meta_primeira_resposta_min=120,
        meta_resolucao_min=600,
        ativo=True,
    )
    alta = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade="alta",
        meta_primeira_resposta_min=15,
        meta_resolucao_min=60,
        ativo=True,
    )
    db_session.add_all([padrao, alta])
    db_session.flush()

    from app.models.status_ticket import StatusTicket

    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA3",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Prioridade alta",
        prioridade="alta",
    )
    db_session.add(ticket)
    db_session.flush()
    aplicar_sla_snapshot_ao_ticket(db_session, ticket)
    assert ticket.sla_meta_primeira_resposta_min == 15


def test_avaliar_meta_em_risco_e_violado():
    inicio = datetime(2026, 6, 23, 10, 0, tzinfo=timezone.utc)
    vence = inicio + timedelta(minutes=100)
    estado, pct = avaliar_meta(
        inicio=inicio,
        vence_em=vence,
        cumprido_em=None,
        meta_min=100,
        now=inicio + timedelta(minutes=85),
        calendar=None,
    )
    assert estado == SlaMetaEstado.em_risco
    assert pct is not None and pct >= 80

    estado2, _ = avaliar_meta(
        inicio=inicio,
        vence_em=vence,
        cumprido_em=None,
        meta_min=100,
        now=inicio + timedelta(minutes=101),
        calendar=None,
    )
    assert estado2 == SlaMetaEstado.violado


def test_mensagem_publica_marca_primeira_resposta(client, seed_base, auth_headers, db_session):
    from app.models.status_ticket import StatusTicket

    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade=None,
        meta_primeira_resposta_min=60,
        meta_resolucao_min=240,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()
    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA-MSG",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Sem resposta ainda",
        descricao="x",
    )
    db_session.add(ticket)
    db_session.flush()
    aplicar_sla_snapshot_ao_ticket(db_session, ticket)
    db_session.commit()

    r2 = client.post(
        f"/v1/tickets/{ticket.id}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "Olá, estamos analisando.", "tipo": "publico"},
    )
    assert r2.status_code == 201, r2.text

    r3 = client.get(f"/v1/tickets/{ticket.id}/sla", headers=auth_headers["admin"])
    assert r3.status_code == 200, r3.text
    body = r3.json()
    assert body["primeira_resposta"]["estado"] == "cumprido"
    assert body["primeira_resposta"]["cumprido_em"] is not None


def test_get_ticket_sla_endpoint(client, seed_base, auth_headers, db_session):
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade=None,
        meta_primeira_resposta_min=30,
        meta_resolucao_min=120,
        ativo=True,
    )
    db_session.add(policy)
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "SLA API",
            "descricao": "x",
        },
    )
    tid = r.json()["id"]
    r_sla = client.get(f"/v1/tickets/{tid}/sla", headers=auth_headers["admin"])
    assert r_sla.status_code == 200
    assert r_sla.json()["ticket_id"] == tid
    assert r_sla.json()["primeira_resposta"]["meta_minutos"] == 30


def test_worker_marca_violado(db_session, seed_base):
    from app.models.status_ticket import StatusTicket

    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        meta_primeira_resposta_min=30,
        meta_resolucao_min=120,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()
    st = db_session.query(StatusTicket).first()
    inicio = datetime.now(timezone.utc) - timedelta(hours=2)
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA4",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Violado",
        sla_policy_id=policy.id,
        sla_meta_primeira_resposta_min=30,
        sla_primeira_resposta_vence_em=inicio + timedelta(minutes=30),
        sla_violado=False,
        created_at=inicio,
    )
    db_session.add(ticket)
    db_session.commit()

    n = processar_sla_tickets_abertos(db_session)
    db_session.commit()
    db_session.refresh(ticket)
    assert n >= 1
    assert ticket.sla_violado is True


def test_mensagem_conta_primeira_resposta():
    m_pub = TicketMensagem(ticket_id=1, atendente_id=1, tipo="publico", corpo="x")
    m_int = TicketMensagem(ticket_id=1, atendente_id=1, tipo="interno", corpo="x")
    assert mensagem_conta_primeira_resposta(m_pub) is True
    assert mensagem_conta_primeira_resposta(m_int) is False


def _status_pausa_cliente(db_session):
    st = db_session.query(StatusTicket).filter(StatusTicket.slug == "aguardando_cliente").first()
    if st is None:
        st = StatusTicket(nome="Aguardando cliente", slug="aguardando_cliente", ordem=3, ativo=True)
        db_session.add(st)
        db_session.flush()
    st.pausa_sla = True
    db_session.commit()
    return st


def _status_em_atendimento(db_session):
    st = db_session.query(StatusTicket).filter(StatusTicket.slug == "em_atendimento").first()
    if st is None:
        st = StatusTicket(nome="Em atendimento", slug="em_atendimento", ordem=2, ativo=True)
        db_session.add(st)
        db_session.commit()
    return st


def test_sla_pausa_por_status_congela_contagem(db_session, seed_base):
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        meta_resolucao_min=60,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()
    st_ativo = _status_em_atendimento(db_session)
    st_pausa = _status_pausa_cliente(db_session)

    inicio = datetime(2026, 6, 23, 10, 0, tzinfo=timezone.utc)
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA-PAUSA",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st_ativo.id,
        assunto="Pausa SLA",
        sla_policy_id=policy.id,
        sla_meta_resolucao_min=60,
        sla_resolucao_vence_em=inicio + timedelta(minutes=60),
        created_at=inicio,
    )
    db_session.add(ticket)
    db_session.flush()

    pausa_em = inicio + timedelta(minutes=30)
    db_session.add(
        TicketHistorico(
            ticket_id=ticket.id,
            campo="status_id",
            valor_antigo=str(st_ativo.id),
            valor_novo=str(st_pausa.id),
            created_at=pausa_em,
        )
    )
    ticket.status_id = st_pausa.id
    db_session.commit()

    now = inicio + timedelta(minutes=100)
    dados = build_ticket_sla_read(db_session, ticket, now=now)
    assert dados["pausado_agora"] is True
    assert dados["minutos_pausados"] == 70
    assert dados["resolucao"]["estado"] == "dentro"


def test_sla_retomada_viola_apos_minutos_efetivos(db_session, seed_base):
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        meta_resolucao_min=60,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()
    st_ativo = _status_em_atendimento(db_session)
    st_pausa = _status_pausa_cliente(db_session)

    inicio = datetime(2026, 6, 23, 10, 0, tzinfo=timezone.utc)
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA-RET",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st_ativo.id,
        assunto="Retomada SLA",
        sla_policy_id=policy.id,
        sla_meta_resolucao_min=60,
        sla_resolucao_vence_em=inicio + timedelta(minutes=60),
        sla_violado=False,
        created_at=inicio,
    )
    db_session.add(ticket)
    db_session.flush()

    pausa_em = inicio + timedelta(minutes=20)
    retoma_em = inicio + timedelta(minutes=50)
    db_session.add(
        TicketHistorico(
            ticket_id=ticket.id,
            campo="status_id",
            valor_antigo=str(st_ativo.id),
            valor_novo=str(st_pausa.id),
            created_at=pausa_em,
        )
    )
    db_session.add(
        TicketHistorico(
            ticket_id=ticket.id,
            campo="status_id",
            valor_antigo=str(st_pausa.id),
            valor_novo=str(st_ativo.id),
            created_at=retoma_em,
        )
    )
    ticket.status_id = st_ativo.id
    db_session.commit()

    now = inicio + timedelta(minutes=90)
    dados = build_ticket_sla_read(db_session, ticket, now=now)
    assert dados["pausado_agora"] is False
    assert dados["minutos_pausados"] == 30
    assert dados["resolucao"]["estado"] == "violado"


def test_get_ticket_sla_reflete_pausa(client, seed_base, auth_headers, db_session):
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        meta_resolucao_min=120,
        ativo=True,
    )
    db_session.add(policy)
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "SLA pausa API",
            "descricao": "x",
        },
    )
    tid = r.json()["id"]
    st_pausa = _status_pausa_cliente(db_session)
    client.patch(
        f"/v1/tickets/{tid}",
        headers=auth_headers["admin"],
        json={"status_id": st_pausa.id},
    )

    r_sla = client.get(f"/v1/tickets/{tid}/sla", headers=auth_headers["admin"])
    assert r_sla.status_code == 200
    body = r_sla.json()
    assert body["pausado_agora"] is True
    assert body["minutos_pausados"] >= 0


def test_worker_respeita_pausa_sla(db_session, seed_base):
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        meta_resolucao_min=30,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()
    st_pausa = _status_pausa_cliente(db_session)
    st_ativo = _status_em_atendimento(db_session)

    inicio = datetime.now(timezone.utc) - timedelta(hours=2)
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA-WK",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st_pausa.id,
        assunto="Worker pausa",
        sla_policy_id=policy.id,
        sla_meta_resolucao_min=30,
        sla_resolucao_vence_em=inicio + timedelta(minutes=30),
        sla_violado=False,
        created_at=inicio,
    )
    db_session.add(ticket)
    db_session.flush()
    db_session.add(
        TicketHistorico(
            ticket_id=ticket.id,
            campo="status_id",
            valor_antigo=str(st_ativo.id),
            valor_novo=str(st_pausa.id),
            created_at=inicio + timedelta(minutes=5),
        )
    )
    db_session.commit()

    processar_sla_tickets_abertos(db_session)
    db_session.commit()
    db_session.refresh(ticket)
    assert ticket.sla_violado is False
