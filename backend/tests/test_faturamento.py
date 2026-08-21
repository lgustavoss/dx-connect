"""Fatura interna e aprovação do financeiro (#326 / #363 / #364)."""

from __future__ import annotations

from datetime import date

from app.database import SessionLocal
from app.services.faturamento import processar_faturamento_mensal, vencimento_da_competencia
from tests.test_implantacao import _assinar_contrato


def test_vencimento_dia_10_mes_seguinte():
    assert vencimento_da_competencia("2026-08") == date(2026, 9, 10)
    assert vencimento_da_competencia("2026-12") == date(2027, 1, 10)


def test_rbac_faturamento(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_a1 = auth_headers["a1"]
    h_a2 = auth_headers["a2"]
    h_admin = auth_headers["admin"]
    assert client.get("/v1/faturamento/faturas", headers=h_com).status_code == 403
    assert client.get("/v1/faturamento/faturas", headers=h_a1).status_code == 403
    assert client.get("/v1/faturamento/faturas", headers=h_a2).status_code == 200
    assert client.get("/v1/faturamento/faturas", headers=h_admin).status_code == 200
    me_a2 = client.get("/v1/atendentes/me", headers=h_a2)
    assert me_a2.status_code == 200
    assert me_a2.json()["e_financeiro"] is True
    me_a1 = client.get("/v1/atendentes/me", headers=h_a1)
    assert me_a1.json()["e_financeiro"] is False
    me_admin = client.get("/v1/atendentes/me", headers=h_admin)
    assert me_admin.json()["e_financeiro"] is True

    assert client.post(
        "/v1/faturamento/faturas/99999/aprovar",
        headers=h_a1,
    ).status_code == 403
    assert client.post(
        "/v1/faturamento/faturas/99999/aprovar",
        headers=h_a2,
    ).status_code == 404
    assert client.post(
        "/v1/faturamento/faturas",
        headers=h_a2,
        json={"contrato_id": 99999, "competencia": "2026-08"},
    ).status_code == 404


def test_gerar_aprovar_rejeitar_e_job_idempotente(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    empresa_id = contrato["empresa_id"]
    assert empresa_id

    patch_nf = client.patch(
        f"/v1/empresas/{empresa_id}",
        headers=h_admin,
        json={"emite_nfse": False},
    )
    assert patch_nf.status_code == 200, patch_nf.text
    assert patch_nf.json()["emite_nfse"] is False

    g = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": "2026-08"},
    )
    assert g.status_code == 201, g.text
    fatura = g.json()
    assert fatura["status"] == "aguardando_aprovacao"
    assert fatura["competencia"] == "2026-08"
    assert fatura["emite_nfse"] is False
    assert float(fatura["valor"]) == 900.0
    assert fatura["vencimento"] == "2026-09-10"
    fid = fatura["id"]

    dup = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": "2026-08"},
    )
    assert dup.status_code == 200
    assert dup.json()["id"] == fid

    curto = client.post(
        f"/v1/faturamento/faturas/{fid}/rejeitar",
        headers=h_fin,
        json={"motivo": "ab"},
    )
    assert curto.status_code == 422

    rejeita = client.post(
        f"/v1/faturamento/faturas/{fid}/rejeitar",
        headers=h_fin,
        json={"motivo": "Valor conferido no contrato está desatualizado"},
    )
    assert rejeita.status_code == 200, rejeita.text
    assert rejeita.json()["status"] == "rejeitada"

    db = SessionLocal()
    try:
        processar_faturamento_mensal(db)
        db.commit()
    finally:
        db.close()
    ainda = client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": "2026-08"})
    assert any(x["id"] == fid and x["status"] == "rejeitada" for x in ainda.json())

    lote = client.post(
        "/v1/faturamento/faturas/gerar-competencia",
        headers=h_admin,
        json={"competencia": "2026-08"},
    )
    assert lote.status_code == 200, lote.text
    assert lote.json()["reabertas"] >= 1
    reaberta = client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": "2026-08"})
    assert any(x["id"] == fid and x["status"] == "aguardando_aprovacao" for x in reaberta.json())

    regen = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": "2026-08"},
    )
    assert regen.status_code == 200
    assert regen.json()["id"] == fid
    assert regen.json()["status"] == "aguardando_aprovacao"
    assert regen.json()["rejeicao_motivo"] is None

    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    assert aprova.status_code == 200, aprova.text
    assert aprova.json()["status"] == "aprovada"
    assert aprova.json()["aprovada_por_id"]

    recusa_aprovada = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": "2026-08"},
    )
    assert recusa_aprovada.status_code == 400

    job = client.post(
        "/v1/faturamento/faturas/gerar-competencia",
        headers=h_admin,
        json={"competencia": "2026-08"},
    )
    assert job.status_code == 200, job.text
    assert job.json()["criadas"] == 0
    assert job.json()["existentes"] >= 1

    db = SessionLocal()
    try:
        n = processar_faturamento_mensal(db)
        db.commit()
        assert n >= 0
    finally:
        db.close()

    lst = client.get("/v1/faturamento/faturas", headers=h_fin, params={"status": "aprovada"})
    assert lst.status_code == 200
    assert any(x["id"] == fid for x in lst.json())

    elig = client.get("/v1/faturamento/contratos-elegiveis", headers=h_fin)
    assert elig.status_code == 200
    assert any(x["id"] == cid for x in elig.json())
