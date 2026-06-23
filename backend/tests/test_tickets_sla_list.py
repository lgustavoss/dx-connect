"""Listagem de tickets com SLA resumido e filtros (#281)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.sla_policy import SlaPolicy
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket
from app.services.sla_calculo import sla_estado_resumido


def _ticket_com_sla(db_session, seed_base, *, minutos_decorridos: int, violado: bool = False, sufixo: str = "1"):
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        meta_primeira_resposta_min=100,
        meta_resolucao_min=480,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()
    st = db_session.query(StatusTicket).first()
    now = datetime.now(timezone.utc)
    inicio = now - timedelta(minutes=minutos_decorridos)
    ticket = Ticket(
        tenant_id=1,
        protocolo=f"#T202606-SLA-LIST-{sufixo}",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="SLA listagem",
        sla_policy_id=policy.id,
        sla_meta_primeira_resposta_min=100,
        sla_primeira_resposta_vence_em=inicio + timedelta(minutes=100),
        sla_meta_resolucao_min=480,
        sla_resolucao_vence_em=inicio + timedelta(minutes=480),
        sla_violado=violado,
        created_at=inicio,
    )
    db_session.add(ticket)
    db_session.commit()
    return ticket


def test_sla_estado_resumido_em_risco(db_session, seed_base):
    ticket = _ticket_com_sla(db_session, seed_base, minutos_decorridos=85)
    assert sla_estado_resumido(ticket) == "em_risco"


def test_lista_expoe_sla_estado(client, seed_base, auth_headers, db_session):
    ticket = _ticket_com_sla(db_session, seed_base, minutos_decorridos=85)
    r = client.get("/v1/tickets", headers=auth_headers["admin"])
    assert r.status_code == 200
    row = next(i for i in r.json()["items"] if i["id"] == ticket.id)
    assert row["sla_estado"] == "em_risco"


def test_filtro_sla_violado(client, seed_base, auth_headers, db_session):
    ok = _ticket_com_sla(db_session, seed_base, minutos_decorridos=30, violado=False, sufixo="ok")
    bad = _ticket_com_sla(db_session, seed_base, minutos_decorridos=120, violado=True, sufixo="bad")
    bad.sla_violado = True
    db_session.commit()

    r = client.get("/v1/tickets", headers=auth_headers["admin"], params={"sla_violado": True})
    assert r.status_code == 200
    ids = {i["id"] for i in r.json()["items"]}
    assert bad.id in ids
    assert ok.id not in ids
