"""Menções @user / @all no chat interno (grupos)."""

from __future__ import annotations


def test_mencao_all_e_usuario_em_grupo(client, seed_base, auth_headers, db_session):
    from app.models.chat_interno import TIPO_CONVERSA_GRUPO, ConversaInterna, ConversaInternaParticipante
    from app.models.chat_interno import PAPEL_PARTICIPANTE_ADMIN, PAPEL_PARTICIPANTE_MEMBRO

    admin = seed_base["admin"]
    a1 = seed_base["a1"]
    a2 = seed_base["a2"]

    conv = ConversaInterna(tenant_id=admin.tenant_id, tipo=TIPO_CONVERSA_GRUPO, titulo="Suporte")
    db_session.add(conv)
    db_session.flush()
    for aid, papel in (
        (admin.id, PAPEL_PARTICIPANTE_ADMIN),
        (a1.id, PAPEL_PARTICIPANTE_MEMBRO),
        (a2.id, PAPEL_PARTICIPANTE_MEMBRO),
    ):
        db_session.add(
            ConversaInternaParticipante(conversa_id=conv.id, atendente_id=aid, papel=papel)
        )
    db_session.commit()

    r = client.post(
        f"/v1/chat-interno/conversas/{conv.id}/mensagens",
        headers=auth_headers["admin"],
        json={
            "corpo": f"Oi @{a1.nome}, atenção @all",
            "mencoes": [
                {"tipo": "all"},
                {"tipo": "user", "atendente_id": a1.id},
            ],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    tipos = {m["tipo"] for m in body["mencoes"]}
    assert "all" in tipos
    assert "user" in tipos
    user_m = next(m for m in body["mencoes"] if m["tipo"] == "user")
    assert user_m["atendente_id"] == a1.id
    assert user_m["rotulo"] == a1.nome


def test_mencao_invalida_fora_do_grupo(client, seed_base, auth_headers, db_session):
    from app.models.chat_interno import TIPO_CONVERSA_GRUPO, ConversaInterna, ConversaInternaParticipante
    from app.models.chat_interno import PAPEL_PARTICIPANTE_ADMIN, PAPEL_PARTICIPANTE_MEMBRO

    admin = seed_base["admin"]
    a1 = seed_base["a1"]
    a2 = seed_base["a2"]

    conv = ConversaInterna(tenant_id=admin.tenant_id, tipo=TIPO_CONVERSA_GRUPO, titulo="Pequeno")
    db_session.add(conv)
    db_session.flush()
    for aid, papel in ((admin.id, PAPEL_PARTICIPANTE_ADMIN), (a1.id, PAPEL_PARTICIPANTE_MEMBRO)):
        db_session.add(
            ConversaInternaParticipante(conversa_id=conv.id, atendente_id=aid, papel=papel)
        )
    db_session.commit()

    r = client.post(
        f"/v1/chat-interno/conversas/{conv.id}/mensagens",
        headers=auth_headers["admin"],
        json={
            "corpo": f"Oi @{a2.nome}",
            "mencoes": [{"tipo": "user", "atendente_id": a2.id}],
        },
    )
    assert r.status_code == 400


def test_mencao_derivada_do_corpo_sem_payload(client, seed_base, auth_headers, db_session):
    from app.models.chat_interno import TIPO_CONVERSA_GRUPO, ConversaInterna, ConversaInternaParticipante
    from app.models.chat_interno import PAPEL_PARTICIPANTE_ADMIN, PAPEL_PARTICIPANTE_MEMBRO

    admin = seed_base["admin"]
    a1 = seed_base["a1"]

    conv = ConversaInterna(tenant_id=admin.tenant_id, tipo=TIPO_CONVERSA_GRUPO, titulo="Auto")
    db_session.add(conv)
    db_session.flush()
    for aid, papel in ((admin.id, PAPEL_PARTICIPANTE_ADMIN), (a1.id, PAPEL_PARTICIPANTE_MEMBRO)):
        db_session.add(
            ConversaInternaParticipante(conversa_id=conv.id, atendente_id=aid, papel=papel)
        )
    db_session.commit()

    r = client.post(
        f"/v1/chat-interno/conversas/{conv.id}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": f"@{a1.nome} e @all por favor"},
    )
    assert r.status_code == 201, r.text
    tipos = {m["tipo"] for m in r.json()["mencoes"]}
    assert tipos == {"all", "user"}
