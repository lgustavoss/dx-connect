import pytest

from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa
from app.services.funcionario_escopo import (
    empresa_ids_vinculados,
    escopo_efetivo,
    funcionario_visivel_na_empresa,
)


def test_escopo_all_ve_todas_empresas_ativas(db_session, seed_base):
    rede = seed_base["rede"]
    emp = seed_base["empresa"]
    f = FuncionarioRede(
        nome="Z Rede",
        email="z@rede.test",
        tipo="socio",
        escopo_empresas="all",
        ativo=True,
        rede_id=rede.id,
    )
    db_session.add(f)
    db_session.commit()
    assert escopo_efetivo(f) == "all"
    ids = empresa_ids_vinculados(db_session, f)
    assert emp.id in ids
    assert funcionario_visivel_na_empresa(db_session, f, emp.id)


def test_escopo_selected_uma_empresa(db_session, seed_base):
    emp = seed_base["empresa"]
    f = FuncionarioRede(
        nome="Colab",
        email="colab@emp.test",
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=emp.rede_id,
        empresa_id=emp.id,
    )
    db_session.add(f)
    db_session.flush()
    db_session.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=emp.id))
    db_session.commit()
    ids = empresa_ids_vinculados(db_session, f)
    assert ids == {emp.id}


def test_escopo_selected_varias_empresas(db_session, seed_base):
    from app.models.empresa import Empresa

    rede = seed_base["rede"]
    emp1 = seed_base["empresa"]
    emp2 = Empresa(tenant_id=emp1.tenant_id, rede_id=rede.id, nome="Empresa B", ativo=True)
    db_session.add(emp2)
    db_session.commit()
    f = FuncionarioRede(
        nome="Super",
        email="super@rede.test",
        tipo="supervisor",
        escopo_empresas="selected",
        ativo=True,
        rede_id=rede.id,
    )
    db_session.add(f)
    db_session.flush()
    for eid in (emp1.id, emp2.id):
        db_session.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=eid))
    db_session.commit()
    ids = empresa_ids_vinculados(db_session, f)
    assert ids == {emp1.id, emp2.id}
    assert funcionario_visivel_na_empresa(db_session, f, emp2.id)
