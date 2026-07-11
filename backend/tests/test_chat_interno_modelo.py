from app.services.chat_interno import (
    ChatInternoErro,
    contar_nao_lidas,
    marcar_visto,
    obter_ou_criar_canal_setor,
    obter_ou_criar_conversa_direta,
    pode_acessar_conversa,
)


def test_obter_ou_criar_conversa_direta_reutiliza_par(db_session, seed_base):
    a1 = seed_base["a1"]
    admin = seed_base["admin"]

    c1 = obter_ou_criar_conversa_direta(db_session, 1, a1.id, admin.id)
    db_session.commit()

    c2 = obter_ou_criar_conversa_direta(db_session, 1, admin.id, a1.id)
    db_session.commit()

    assert c1.id == c2.id


def test_obter_ou_criar_conversa_direta_nao_permite_self(db_session, seed_base):
    a1 = seed_base["a1"]
    try:
        obter_ou_criar_conversa_direta(db_session, 1, a1.id, a1.id)
        assert False, "deveria falhar"
    except ChatInternoErro as exc:
        assert "consigo mesmo" in str(exc).lower()


def test_obter_ou_criar_canal_setor_unico(db_session, seed_base):
    setor1 = seed_base["setor1"]
    setor2 = seed_base["setor2"]

    c1 = obter_ou_criar_canal_setor(db_session, 1, setor1.id)
    c2 = obter_ou_criar_canal_setor(db_session, 1, setor1.id)
    c3 = obter_ou_criar_canal_setor(db_session, 1, setor2.id)
    db_session.commit()

    assert c1.id == c2.id
    assert c3.id != c1.id
    assert c1.tipo == "setor"
    assert c1.setor_id == setor1.id


def test_contar_nao_lidas_e_marcar_visto(db_session, seed_base):
    from app.models.chat_interno import ConversaInterna
    from app.services.chat_interno import enviar_mensagem

    a1 = seed_base["a1"]
    a2 = seed_base["a2"]
    conversa = obter_ou_criar_conversa_direta(db_session, 1, a1.id, a2.id)
    db_session.commit()

    enviar_mensagem(db_session, conversa, a1, "Olá")
    db_session.commit()
    conversa = db_session.get(ConversaInterna, conversa.id)

    assert contar_nao_lidas(db_session, conversa, a2.id) == 1
    assert contar_nao_lidas(db_session, conversa, a1.id) == 0

    marcar_visto(db_session, conversa, a2)
    db_session.commit()

    assert contar_nao_lidas(db_session, conversa, a2.id) == 0


def test_pode_acessar_conversa_direta_apenas_participantes(db_session, seed_base):
    a1 = seed_base["a1"]
    a2 = seed_base["a2"]
    admin = seed_base["admin"]
    conversa = obter_ou_criar_conversa_direta(db_session, 1, a1.id, a2.id)
    db_session.commit()

    assert pode_acessar_conversa(db_session, a1, conversa)
    assert pode_acessar_conversa(db_session, a2, conversa)
    assert not pode_acessar_conversa(db_session, admin, conversa)
