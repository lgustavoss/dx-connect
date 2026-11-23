"""Follow-up #1407 — filtros do hub de contatos direto no banco (subqueries).

Garante que a troca de listas materializadas por subqueries não mudou o
resultado: contatos visíveis por rede/empresa (inclusive só via junction)
continuam aparecendo e os de outro tenant continuam fora.
"""

from __future__ import annotations

from app.models import Empresa, Rede, Tenant
from app.models.funcionario_rede import (
    FuncionarioRede,
    FuncionarioRedeEmpresa,
    FuncionarioRedeVinculo,
)


def _criar_rede_empresa(db_session, *, tenant_id: int, nome: str):
    rede = Rede(tenant_id=tenant_id, nome=f"Rede {nome}", ativo=True)
    db_session.add(rede)
    db_session.flush()
    empresa = Empresa(tenant_id=tenant_id, rede_id=rede.id, nome=f"Empresa {nome}", ativo=True)
    db_session.add(empresa)
    db_session.commit()
    return rede, empresa


def _criar_contato_junction(db_session, *, nome: str, email: str, rede, empresa=None) -> FuncionarioRede:
    """Supervisor visível apenas pela junction de rede/empresa (sem campos legados)."""
    f = FuncionarioRede(
        nome=nome,
        email=email,
        tipo="supervisor",
        escopo_empresas="selected",
        ativo=True,
        rede_id=None,
        empresa_id=None,
    )
    db_session.add(f)
    db_session.flush()
    db_session.add(FuncionarioRedeVinculo(funcionario_id=f.id, rede_id=rede.id))
    if empresa is not None:
        db_session.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=empresa.id))
    db_session.commit()
    db_session.refresh(f)
    return f


def _ids(items) -> set[int]:
    return {int(item["id"]) for item in items}


def test_contatos_e_busca_do_hub_isolam_outro_tenant(client, seed_base, auth_headers, db_session):
    db_session.add(Tenant(id=2, nome="Outro Tenant", ativo=True))
    db_session.commit()
    rede_outro, empresa_outro = _criar_rede_empresa(db_session, tenant_id=2, nome="Outro")
    outro = _criar_contato_junction(
        db_session,
        nome="Contato Outro Tenant",
        email="outro@example.com",
        rede=rede_outro,
        empresa=empresa_outro,
    )
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    proprio = _criar_contato_junction(
        db_session,
        nome="Contato Tenant Um",
        email="um@example.com",
        rede=rede1,
        empresa=empresa1,
    )

    contatos = client.get("/v1/whatsapp/chats/contatos", headers=auth_headers["a1"])
    assert contatos.status_code == 200, contatos.text
    ids = _ids(contatos.json()["items"])
    assert proprio.id in ids
    assert outro.id not in ids

    busca = client.get("/v1/whatsapp/chats/funcionarios?busca=Contato", headers=auth_headers["a1"])
    assert busca.status_code == 200, busca.text
    ids = _ids(busca.json())
    assert proprio.id in ids
    assert outro.id not in ids

    similares = client.get(
        "/v1/whatsapp/chats/funcionarios/similares?nome=Contato Outro Tenant",
        headers=auth_headers["a1"],
    )
    assert similares.status_code == 200, similares.text
    assert outro.id not in _ids(similares.json())


def test_hub_encontra_contato_visivel_so_pela_junction(client, seed_base, auth_headers, db_session):
    rede2, empresa2 = _criar_rede_empresa(db_session, tenant_id=1, nome="Secundária")
    func = _criar_contato_junction(
        db_session,
        nome="Supervisor Junction",
        email="junction@example.com",
        rede=rede2,
        empresa=empresa2,
    )

    contatos = client.get("/v1/whatsapp/chats/contatos", headers=auth_headers["a1"])
    assert contatos.status_code == 200, contatos.text
    item = next(i for i in contatos.json()["items"] if i["id"] == func.id)
    assert {rede["id"] for rede in item["redes"]} == {rede2.id}
    assert {emp["id"] for emp in item["empresas"]} == {empresa2.id}

    # Busca por nome da empresa continua achando o supervisor via junction.
    busca = client.get(
        "/v1/whatsapp/chats/contatos?busca=Empresa Secundária",
        headers=auth_headers["a1"],
    )
    assert busca.status_code == 200, busca.text
    assert func.id in _ids(busca.json()["items"])
