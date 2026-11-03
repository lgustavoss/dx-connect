"""Busca de empresas por CNPJ no picker do ticket (#S202611-0001 / #1369).

O CNPJ é gravado só com dígitos, então o termo formatado (com pontos, barra e
traço) precisa casar por dígitos — tanto para quem tem `empresas.ver` (modelo
completo) quanto para o atendente (resumo, sem CNPJ no payload).
"""
from __future__ import annotations


def _criar_empresa(db_session, rede_id: int, nome: str, cnpj: str):
    from app.models import Empresa

    e = Empresa(tenant_id=1, rede_id=rede_id, nome=nome, cnpj_cpf=cnpj, ativo=True)
    db_session.add(e)
    db_session.commit()
    return e


def _abrir_ticket(client, headers, empresa_id: int, setor_id: int) -> None:
    r = client.post(
        "/v1/tickets",
        headers=headers,
        json={"empresa_id": empresa_id, "setor_id": setor_id, "assunto": "Busca CNPJ", "descricao": "D"},
    )
    assert r.status_code == 201, r.text


def test_busca_por_cnpj_formatado_e_por_digitos(client, seed_base, auth_headers, db_session):
    alvo = _criar_empresa(db_session, seed_base["rede"].id, "Alvo CNPJ", "65305802000170")
    _criar_empresa(db_session, seed_base["rede"].id, "Outra Empresa", "11222333000181")
    h = auth_headers["admin"]

    for termo in ("65.305.802/0001-70", "65305802000170", "305.802"):
        r = client.get("/v1/empresas", headers=h, params={"busca": termo})
        assert r.status_code == 200, r.text
        ids = [x["id"] for x in r.json()["items"]]
        assert alvo.id in ids, f"busca {termo!r} não encontrou a empresa"
        assert len(ids) == 1, f"busca {termo!r} trouxe ruído: {ids}"

    # Busca por texto continua funcionando (com letras não entra o ramo de dígitos)
    r = client.get("/v1/empresas", headers=h, params={"busca": "Alvo"})
    assert [x["id"] for x in r.json()["items"]] == [alvo.id]


def test_atendente_busca_por_cnpj_sem_receber_o_documento(client, seed_base, auth_headers, db_session):
    """Quem não tem `empresas.ver` acha pelo CNPJ, mas o resumo continua sem CNPJ."""
    alvo = _criar_empresa(db_session, seed_base["rede"].id, "Alvo Atendente", "65305802000170")
    _abrir_ticket(client, auth_headers["admin"], alvo.id, seed_base["setor1"].id)

    h_a1 = auth_headers["a1"]
    sem_busca = client.get("/v1/empresas", headers=h_a1)
    assert sem_busca.status_code == 200
    assert alvo.id in [x["id"] for x in sem_busca.json()["items"]]
    assert all("cnpj_cpf" not in x for x in sem_busca.json()["items"]), "resumo do atendente não expõe CNPJ"

    r = client.get("/v1/empresas", headers=h_a1, params={"busca": "65.305.802/0001-70"})
    assert r.status_code == 200, r.text
    ids = [x["id"] for x in r.json()["items"]]
    assert alvo.id in ids
    assert all("cnpj_cpf" not in x for x in r.json()["items"]), "busca não pode vazar o CNPJ no resumo"
