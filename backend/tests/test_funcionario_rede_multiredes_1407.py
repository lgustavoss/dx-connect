"""#1407 — contato vinculado a mais de uma rede (N:N explícito)."""

from __future__ import annotations

import pytest

from app.models import Empresa, Rede, Tenant
from app.models.funcionario_rede import (
    FuncionarioRede,
    FuncionarioRedeVinculo,
)
from app.services.funcionario_escopo import (
    empresa_ids_vinculados,
    rede_id_efetiva,
    redes_efetivas,
    redes_ids_efetivas,
    validar_empresa_ids_na_rede,
)


def _segunda_rede(db_session, *, nome="Rede Secundária"):
    rede = Rede(tenant_id=1, nome=nome, ativo=True)
    db_session.add(rede)
    db_session.flush()
    empresa = Empresa(tenant_id=1, rede_id=rede.id, nome=f"Empresa {nome}", ativo=True)
    db_session.add(empresa)
    db_session.commit()
    return rede, empresa


def _criar_contato(client, auth_headers, payload):
    r = client.post("/v1/funcionarios-rede", json=payload, headers=auth_headers["admin"])
    assert r.status_code == 201, r.text
    return r.json()


def test_criar_contato_com_empresas_de_duas_redes(client, seed_base, auth_headers, db_session):
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    rede2, empresa2 = _segunda_rede(db_session)

    body = _criar_contato(
        client,
        auth_headers,
        {
            "nome": "Contabilidade Multi",
            "email": "multi@example.com",
            "telefone": "5511999887766",
            "tipo": "supervisor",
            "escopo_empresas": "selected",
            "rede_ids": [rede1.id, rede2.id],
            "empresa_ids": [empresa1.id, empresa2.id],
        },
    )

    assert {rede["id"] for rede in body["redes"]} == {rede1.id, rede2.id}
    assert body["rede_id"] == rede1.id
    assert body["rede_nome"] == rede1.nome
    assert set(body["empresa_ids"]) == {empresa1.id, empresa2.id}

    db_session.expire_all()
    vinculos = (
        db_session.query(FuncionarioRedeVinculo)
        .filter(FuncionarioRedeVinculo.funcionario_id == body["id"])
        .all()
    )
    assert {v.rede_id for v in vinculos} == {rede1.id, rede2.id}

    detalhe = client.get(f"/v1/funcionarios-rede/{body['id']}", headers=auth_headers["admin"])
    assert detalhe.status_code == 200
    assert {rede["id"] for rede in detalhe.json()["redes"]} == {rede1.id, rede2.id}
    assert {emp["id"] for emp in detalhe.json()["empresas_vinculo"]} == {empresa1.id, empresa2.id}


def test_listagem_e_filtro_por_rede_consideram_junction(client, seed_base, auth_headers, db_session):
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    rede2, empresa2 = _segunda_rede(db_session)
    body = _criar_contato(
        client,
        auth_headers,
        {
            "nome": "Supervisor Duas Redes",
            "tipo": "supervisor",
            "escopo_empresas": "selected",
            "rede_ids": [rede1.id, rede2.id],
            "empresa_ids": [empresa1.id, empresa2.id],
        },
    )

    for rede_id in (rede1.id, rede2.id):
        r = client.get(f"/v1/funcionarios-rede?rede_id={rede_id}", headers=auth_headers["admin"])
        assert r.status_code == 200, r.text
        item = next((i for i in r.json()["items"] if i["id"] == body["id"]), None)
        assert item is not None, f"contato não apareceu no filtro da rede {rede_id}"
        assert {rede["id"] for rede in item["redes"]} == {rede1.id, rede2.id}


def test_socio_vinculado_a_duas_redes(client, seed_base, auth_headers, db_session):
    rede1 = seed_base["rede"]
    rede2, _ = _segunda_rede(db_session)

    body = _criar_contato(
        client,
        auth_headers,
        {
            "nome": "Sócio Duas Redes",
            "tipo": "socio",
            "escopo_empresas": "all",
            "rede_ids": [rede1.id, rede2.id],
        },
    )

    assert {rede["id"] for rede in body["redes"]} == {rede1.id, rede2.id}
    assert body["rede_id"] == rede1.id
    assert body["empresa_ids"] == []


def test_atualizar_remove_e_mantem_vinculos_de_rede(client, seed_base, auth_headers, db_session):
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    rede2, empresa2 = _segunda_rede(db_session)
    body = _criar_contato(
        client,
        auth_headers,
        {
            "nome": "Colaborador Duas Redes",
            "tipo": "colaborador",
            "escopo_empresas": "selected",
            "rede_ids": [rede1.id, rede2.id],
            "empresa_ids": [empresa1.id, empresa2.id],
        },
    )
    assert body["empresa_id"] is None

    # Trocar as redes sem revisar as empresas das redes antigas é rejeitado.
    r = client.patch(
        f"/v1/funcionarios-rede/{body['id']}",
        json={"rede_ids": [rede2.id]},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 400
    assert "redes vinculadas" in r.json()["detail"].lower()

    # Com as empresas coerentes, o vínculo passa a ser só a rede 2.
    r = client.patch(
        f"/v1/funcionarios-rede/{body['id']}",
        json={"rede_ids": [rede2.id], "empresa_ids": [empresa2.id]},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 200, r.text
    atualizado = r.json()
    assert [rede["id"] for rede in atualizado["redes"]] == [rede2.id]
    assert atualizado["rede_id"] == rede2.id
    assert atualizado["empresa_ids"] == [empresa2.id]

    # Volta para a rede 1.
    r = client.patch(
        f"/v1/funcionarios-rede/{body['id']}",
        json={"rede_ids": [rede1.id], "empresa_ids": [empresa1.id]},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 200, r.text
    assert [rede["id"] for rede in r.json()["redes"]] == [rede1.id]
    assert r.json()["empresa_ids"] == [empresa1.id]

    # Junction reflete o back-and-forth.
    db_session.expire_all()
    vinculos = (
        db_session.query(FuncionarioRedeVinculo)
        .filter(FuncionarioRedeVinculo.funcionario_id == body["id"])
        .all()
    )
    assert {v.rede_id for v in vinculos} == {rede1.id}


def test_rejeita_rede_de_outro_tenant(client, seed_base, auth_headers, db_session):
    rede1 = seed_base["rede"]
    outro_tenant = Tenant(id=2, nome="Outro Tenant", ativo=True)
    rede_outro = Rede(tenant_id=2, nome="Rede de Outro Tenant", ativo=True)
    db_session.add_all([outro_tenant, rede_outro])
    db_session.commit()

    r = client.post(
        "/v1/funcionarios-rede",
        json={
            "nome": "Contato Tenant Errado",
            "tipo": "socio",
            "escopo_empresas": "all",
            "rede_ids": [rede1.id, rede_outro.id],
        },
        headers=auth_headers["admin"],
    )
    assert r.status_code == 400
    assert "tenant" in r.json()["detail"].lower()


def test_compat_payload_antigo_rede_id_simples(client, seed_base, auth_headers):
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    body = _criar_contato(
        client,
        auth_headers,
        {
            "nome": "Contato Legado",
            "tipo": "colaborador",
            "escopo_empresas": "selected",
            "rede_id": rede1.id,
            "empresa_ids": [empresa1.id],
        },
    )
    assert [rede["id"] for rede in body["redes"]] == [rede1.id]
    assert body["rede_id"] == rede1.id
    assert body["rede_nome"] == rede1.nome


def test_service_redes_efetivas_junction_e_fallback_legado(db_session, seed_base):
    rede1 = seed_base["rede"]
    rede2, empresa2 = _segunda_rede(db_session)

    f = FuncionarioRede(
        nome="Sócio Antigo",
        email="socio.antigo@test.local",
        tipo="socio",
        escopo_empresas="all",
        ativo=True,
        rede_id=rede1.id,
    )
    db_session.add(f)
    db_session.flush()
    db_session.add(FuncionarioRedeVinculo(funcionario_id=f.id, rede_id=rede1.id))
    db_session.add(FuncionarioRedeVinculo(funcionario_id=f.id, rede_id=rede2.id))
    db_session.commit()

    assert redes_ids_efetivas(db_session, f) == [rede1.id, rede2.id]
    assert [rede.id for rede in redes_efetivas(db_session, f)] == [rede1.id, rede2.id]
    assert rede_id_efetiva(db_session, f) == rede1.id
    assert {seed_base["empresa"].id, empresa2.id} <= empresa_ids_vinculados(db_session, f)

    # Sem junction: deriva do campo legado (compatibilidade).
    legado = FuncionarioRede(
        nome="Supervisor Legado",
        tipo="supervisor",
        escopo_empresas="selected",
        ativo=True,
        rede_id=rede2.id,
    )
    db_session.add(legado)
    db_session.commit()
    assert redes_ids_efetivas(db_session, legado) == [rede2.id]
    assert rede_id_efetiva(db_session, legado) == rede2.id


def test_validar_empresa_ids_aceita_qualquer_rede_vinculada(db_session, seed_base):
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    rede2, empresa2 = _segunda_rede(db_session)

    validar_empresa_ids_na_rede(db_session, [rede1.id, rede2.id], [empresa1.id, empresa2.id])
    with pytest.raises(ValueError):
        validar_empresa_ids_na_rede(db_session, [rede1.id], [empresa2.id])
    with pytest.raises(ValueError):
        validar_empresa_ids_na_rede(db_session, [], [empresa1.id])


def test_listagem_por_rede_mostra_contato_multirede(client, seed_base, auth_headers, db_session):
    """#1407: GET /redes/{id}/funcionarios considera o vínculo N:N, não só a rede legada."""
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    rede2, empresa2 = _segunda_rede(db_session)
    body = _criar_contato(
        client,
        auth_headers,
        {
            "nome": "Contato Rede Dois Primeiro",
            "email": "rede2-first@example.com",
            "telefone": "5511988776655",
            "tipo": "supervisor",
            "escopo_empresas": "selected",
            # Primeira rede (legado) é a rede2; o vínculo N:N também inclui a rede1.
            "rede_ids": [rede2.id, rede1.id],
            "empresa_ids": [empresa2.id, empresa1.id],
        },
    )
    assert body["rede_id"] == rede2.id

    r = client.get(f"/v1/redes/{rede1.id}/funcionarios", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text
    itens = {item["id"]: item for item in r.json()["items"]}
    assert body["id"] in itens, "contato multi-rede deve aparecer na listagem da rede não-legada"
    assert {rede["id"] for rede in itens[body["id"]]["redes"]} == {rede1.id, rede2.id}


def test_whatsapp_contatos_e_busca_expoem_todas_as_redes(client, seed_base, auth_headers, db_session):
    rede1, empresa1 = seed_base["rede"], seed_base["empresa"]
    rede2, empresa2 = _segunda_rede(db_session)
    body = _criar_contato(
        client,
        auth_headers,
        {
            "nome": "Contato Whats Multi",
            "telefone": "5511977665544",
            "tipo": "supervisor",
            "escopo_empresas": "selected",
            "rede_ids": [rede1.id, rede2.id],
            "empresa_ids": [empresa1.id, empresa2.id],
        },
    )

    contatos = client.get(
        "/v1/whatsapp/chats/contatos?busca=Whats Multi",
        headers=auth_headers["a1"],
    )
    assert contatos.status_code == 200, contatos.text
    item = next(i for i in contatos.json()["items"] if i["id"] == body["id"])
    assert {rede["id"] for rede in item["redes"]} == {rede1.id, rede2.id}
    assert item["rede_id"] == rede1.id
    assert {emp["id"] for emp in item["empresas"]} == {empresa1.id, empresa2.id}

    busca = client.get(
        "/v1/whatsapp/chats/funcionarios?busca=Whats Multi",
        headers=auth_headers["a1"],
    )
    assert busca.status_code == 200, busca.text
    hit = next(i for i in busca.json() if i["id"] == body["id"])
    assert {rede["id"] for rede in hit["redes"]} == {rede1.id, rede2.id}
