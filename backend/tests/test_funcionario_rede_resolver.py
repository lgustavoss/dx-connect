from app.services.funcionario_rede_resolver import resolver_remetente_por_email


def test_remetente_desconhecido(db_session, seed_base):
    rem = resolver_remetente_por_email(db_session, "desconhecido@example.com")
    assert rem.requer_cadastro is True
    assert rem.empresa_id is None


def test_colaborador_unica_empresa(db_session, seed_base):
    emp = seed_base["empresa"]
    from app.models.funcionario_rede import FuncionarioRede

    f = FuncionarioRede(
        nome="Cliente",
        email="cliente@empresa.test",
        tipo="colaborador",
        ativo=True,
        rede_id=emp.rede_id,
        empresa_id=emp.id,
    )
    db_session.add(f)
    db_session.commit()
    rem = resolver_remetente_por_email(db_session, "cliente@empresa.test")
    assert rem.requer_cadastro is False
    assert rem.empresa_id == emp.id
    assert rem.funcionario_id == f.id
