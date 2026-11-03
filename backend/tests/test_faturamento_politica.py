"""Política de faturamento da instância (#1339) e gatilhos da mensalidade.

Instância no perfil de hoje (data_inicio, dia 10, sem proporcional) precisa
continuar produzindo exatamente as faturas anteriores.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.database import SessionLocal
from app.services.faturamento import vencimento_da_competencia
from tests.test_implantacao import _assinar_contrato


def _comp(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _proximo_mes(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _patch_politica(client, h_admin, **campos):
    r = client.patch("/v1/faturamento/politica", headers=h_admin, json=campos)
    assert r.status_code == 200, r.text
    return r.json()


def test_politica_padrao_e_perfil_atual_continua_igual(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]

    pol = client.get("/v1/faturamento/politica", headers=h_fin)
    assert pol.status_code == 200, pol.text
    assert pol.json() == {
        "dia_vencimento": 10,
        "gatilho": "data_inicio",
        "gatilho_dias": 0,
        "proporcional_primeira_fatura": False,
    }
    assert client.get("/v1/faturamento/politica", headers=h_com).status_code == 403

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = _comp(inicio)

    r = client.post(
        "/v1/faturamento/faturas/gerar-competencia",
        headers=h_admin,
        json={"competencia": comp},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["criadas"] == 1
    assert body["aguardando"] == 0

    faturas = client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": comp}).json()
    fatura = next(f for f in faturas if f["contrato_id"] == cid)
    assert fatura["vencimento"] == vencimento_da_competencia(comp).isoformat()
    assert fatura["valor"] == "900.00"


def test_patch_politica_admin_apenas_e_validacao(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]

    assert client.patch("/v1/faturamento/politica", headers=h_com, json={"dia_vencimento": 15}).status_code == 403
    # Financeiro gera/aprova, mas a configuração da instância é do admin (#1339).
    assert client.patch("/v1/faturamento/politica", headers=h_fin, json={"dia_vencimento": 15}).status_code == 403

    assert client.patch("/v1/faturamento/politica", headers=h_admin, json={"dia_vencimento": 29}).status_code == 422
    assert client.patch("/v1/faturamento/politica", headers=h_admin, json={"dia_vencimento": 0}).status_code == 422
    assert (
        client.patch("/v1/faturamento/politica", headers=h_admin, json={"gatilho": "inventado"}).status_code == 422
    )
    assert (
        client.patch(
            "/v1/faturamento/politica",
            headers=h_admin,
            json={"gatilho": "dias_apos_marco", "gatilho_dias": 30},
        ).status_code
        == 200
    )
    pol = client.get("/v1/faturamento/politica", headers=h_fin).json()
    assert pol["gatilho"] == "dias_apos_marco"
    assert pol["gatilho_dias"] == 30

    ok = _patch_politica(
        client,
        h_admin,
        dia_vencimento=15,
        gatilho="data_inicio",
        gatilho_dias=0,
        proporcional_primeira_fatura=True,
    )
    assert ok["dia_vencimento"] == 15
    assert ok["proporcional_primeira_fatura"] is True


def test_dia_vencimento_vem_da_politica_e_contrato_sobrescreve(client, auth_headers, db_session):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))

    _patch_politica(client, h_admin, dia_vencimento=15)

    from app.models.comercial_contrato import Contrato

    row = db_session.query(Contrato).filter(Contrato.id == cid).one()
    row.dia_vencimento_override = 20
    db_session.commit()

    comp = _comp(inicio)
    r = client.post("/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": comp})
    assert r.status_code == 200, r.text
    fatura = next(
        f
        for f in client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": comp}).json()
        if f["contrato_id"] == cid
    )
    # Override da negociação vence a política da instância.
    assert fatura["vencimento"] == vencimento_da_competencia(comp, dia=20).isoformat()


def test_gatilho_dias_apos_assinatura_espera_o_prazo(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    _patch_politica(client, h_admin, gatilho="dias_apos_assinatura", gatilho_dias=30)

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    competencia_inicio = _comp(inicio)

    r = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": competencia_inicio}
    )
    assert r.status_code == 200, r.text
    if _comp(inicio + timedelta(days=30)) != competencia_inicio:
        assert r.json()["criadas"] == 0
        elegiveis = client.get("/v1/faturamento/contratos-elegiveis", headers=h_admin).json()
        alvo = next(c for c in elegiveis if c["id"] == cid)
        assert alvo["inicio_mensalidade"] == (inicio + timedelta(days=30)).isoformat()
        assert alvo["dia_vencimento"] == 10

        depois = client.post(
            "/v1/faturamento/faturas/gerar-competencia",
            headers=h_admin,
            json={"competencia": _comp(inicio + timedelta(days=30))},
        )
        assert depois.status_code == 200, depois.text
        assert depois.json()["criadas"] == 1


def test_override_de_inicio_do_contrato_manda_na_politica(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))

    from app.models.comercial_contrato import Contrato

    db = SessionLocal()
    try:
        row = db.query(Contrato).filter(Contrato.id == cid).one()
        row.inicio_mensalidade_override = inicio + timedelta(days=45)
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": _comp(inicio)}
    )
    assert r.status_code == 200, r.text
    assert r.json()["criadas"] == 0

    alvo = inicio + timedelta(days=45)
    depois = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": _comp(alvo)}
    )
    assert depois.status_code == 200, depois.text
    assert depois.json()["criadas"] == 1


def test_gatilho_marco_sem_primeira_venda_nao_gera_fatura(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    _patch_politica(client, h_admin, gatilho="dias_apos_marco", gatilho_dias=30)

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = _comp(inicio)

    r = client.post("/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": comp})
    assert r.status_code == 200, r.text
    assert r.json()["criadas"] == 0
    assert r.json()["aguardando"] >= 1

    avulsa = client.post("/v1/faturamento/faturas", headers=h_admin, json={"contrato_id": cid, "competencia": comp})
    assert avulsa.status_code == 400
    assert "primeira venda" in avulsa.json()["detail"].lower()

    elegiveis = client.get("/v1/faturamento/contratos-elegiveis", headers=h_admin).json()
    alvo = next(c for c in elegiveis if c["id"] == cid)
    assert alvo["aguardando_motivo"] == "aguardando_primeira_venda"
    assert alvo["inicio_mensalidade"] is None


def test_gatilho_ticket_implantacao_fechado(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    _patch_politica(client, h_admin, gatilho="ticket_implantacao_fechado", gatilho_dias=0)

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = _comp(inicio)

    r = client.post("/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": comp})
    assert r.status_code == 200, r.text
    assert r.json()["criadas"] == 0
    assert r.json()["aguardando"] >= 1

    from app.models.ticket import Ticket

    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.contrato_id == cid).first()
        assert ticket is not None
        from datetime import datetime, timezone

        ticket.fechado_em = datetime.combine(inicio, datetime.min.time(), tzinfo=timezone.utc)
        db.commit()
    finally:
        db.close()

    depois = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": comp}
    )
    assert depois.status_code == 200, depois.text
    assert depois.json()["criadas"] == 1
