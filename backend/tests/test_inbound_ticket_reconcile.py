"""Testes de reconciliação de tickets inbound (#388)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import Ticket
from app.models.email_inbound_received import EmailInboundReceived
from app.models.funcionario_rede import FuncionarioRede
from app.services.inbound_ticket_reconcile import reconciliar_tickets_pendentes_por_email


def _criar_ticket_inbound_pendente(db_session, seed_base, *, email: str):
    t = Ticket(
        tenant_id=1,
        protocolo=f"IN{datetime.now().timestamp()}",
        empresa_id=None,
        rede_id=None,
        setor_id=seed_base["setor1"].id,
        status_id=seed_base["status"].id,
        assunto="Triagem inbound teste",
        aberto_por_id=None,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(t)
    db_session.flush()
    db_session.add(
        EmailInboundReceived(
            message_id_normalized=f"inbound-{datetime.now().timestamp()}@test",
            ticket_id=t.id,
            from_address=f"Cliente Teste <{email}>",
        )
    )
    db_session.commit()
    db_session.refresh(t)
    return t


def test_reconciliar_apos_cadastro_funcionario(db_session, seed_base):
    email = "novo.cliente@empresa.test"
    ticket = _criar_ticket_inbound_pendente(db_session, seed_base, email=email)
    emp = seed_base["empresa"]

    f = FuncionarioRede(
        nome="Cliente Teste",
        email=email,
        tipo="colaborador",
        ativo=True,
        rede_id=emp.rede_id,
        empresa_id=emp.id,
    )
    db_session.add(f)
    db_session.commit()

    alterados = reconciliar_tickets_pendentes_por_email(db_session, email)
    db_session.commit()
    db_session.refresh(ticket)

    assert alterados == 1
    assert ticket.aberto_por_id == f.id
    assert ticket.rede_id == emp.rede_id
    assert ticket.empresa_id == emp.id


def test_patch_empresa_outra_rede_rejeitado(client, seed_base, auth_headers, db_session):
    from app.models.empresa import Empresa
    from app.models.rede import Rede

    email = "outro.cliente@empresa.test"
    ticket = _criar_ticket_inbound_pendente(db_session, seed_base, email=email)
    emp = seed_base["empresa"]

    f = FuncionarioRede(
        nome="Cliente Outro",
        email=email,
        tipo="colaborador",
        ativo=True,
        rede_id=emp.rede_id,
        empresa_id=emp.id,
    )
    db_session.add(f)
    db_session.commit()
    reconciliar_tickets_pendentes_por_email(db_session, email)
    db_session.commit()

    rede2 = Rede(tenant_id=1, nome="Rede B", ativo=True)
    db_session.add(rede2)
    db_session.flush()
    empresa2 = Empresa(tenant_id=1, rede_id=rede2.id, nome="Empresa B", ativo=True)
    db_session.add(empresa2)
    db_session.commit()

    r = client.patch(
        f"/v1/tickets/{ticket.id}",
        headers=auth_headers["admin"],
        json={"empresa_id": empresa2.id},
    )
    assert r.status_code == 400


def test_ticket_expoe_solicitante(client, seed_base, auth_headers, db_session):
    email = "solicitante@empresa.test"
    ticket = _criar_ticket_inbound_pendente(db_session, seed_base, email=email)

    r = client.get(f"/v1/tickets/{ticket.id}", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["solicitante"] is not None
    assert body["solicitante"]["email"] == email
    assert body["solicitante"]["cadastrado"] is False
