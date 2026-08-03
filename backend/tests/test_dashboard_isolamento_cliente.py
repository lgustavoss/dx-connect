"""Isolamento de análises por rede/empresa (#595)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.models.empresa import Empresa
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.models.whatsapp_chat import WhatsappChat
from app.models.whatsapp_chat_demanda import WhatsappChatDemanda
from app.services.dashboard_chats import clear_dashboard_chats_cache


def test_demandas_filtradas_por_empresa_nao_vazam(client, seed_base, auth_headers, db_session):
    clear_dashboard_chats_cache()
    emp_a = seed_base["empresa"]
    emp_b = Empresa(
        tenant_id=1,
        rede_id=emp_a.rede_id,
        nome="Empresa B isolamento",
        cnpj_cpf="00000000000191",
        ativo=True,
    )
    db_session.add(emp_b)
    db_session.flush()

    nat = TicketNatureza(nome="Iso Nat", slug="iso-nat-595", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="Iso Mot", slug="iso-mot-595", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.commit()

    for emp, suf in ((emp_a, "a"), (emp_b, "b")):
        chat = WhatsappChat(
            protocolo=f"W-iso-{suf}-{datetime.now().timestamp()}",
            wa_id=f"5511777{suf}",
            estado="encerrado",
            setor_id=seed_base["setor1"].id,
            empresa_id=emp.id,
        )
        db_session.add(chat)
        db_session.flush()
        db_session.add(
            WhatsappChatDemanda(
                chat_id=chat.id,
                natureza_id=nat.id,
                motivo_id=mot.id,
                desfecho="resolvido_sessao",
                created_at=datetime.now(timezone.utc),
            )
        )
    db_session.commit()

    hoje = date.today().isoformat()
    r_a = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}&empresa_id={emp_a.id}",
        headers=auth_headers["admin"],
    )
    assert r_a.status_code == 200
    body_a = r_a.json()
    assert body_a["demanda_maior"]["total"] == 1
    assert all(e["empresa_id"] == emp_a.id for e in body_a["demandas_por_empresa"])

    r_b = client.get(
        f"/v1/dashboard/chats?de={hoje}&ate={hoje}&empresa_id={emp_b.id}",
        headers=auth_headers["admin"],
    )
    assert r_b.status_code == 200
    body_b = r_b.json()
    assert body_b["demanda_maior"]["total"] == 1
    assert all(e["empresa_id"] == emp_b.id for e in body_b["demandas_por_empresa"])

    lista = client.get(
        f"/v1/dashboard/chats/demandas?de={hoje}&ate={hoje}&empresa_id={emp_a.id}",
        headers=auth_headers["admin"],
    ).json()
    assert lista["total"] == 1
    assert lista["items"][0]["empresa_id"] == emp_a.id
