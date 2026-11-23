"""Política de faturamento da instância (#1339) e gatilhos da mensalidade.

Instância no perfil de hoje (data_inicio, dia 10, sem proporcional) precisa
continuar produzindo exatamente as faturas anteriores.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.services.faturamento import processar_faturamento_mensal, vencimento_da_competencia
from tests.test_comercial_contrato import _anexar_pdf_assinado, _negociacao_com_linha
from tests.test_implantacao import _assinar_contrato


def _hoje_sp() -> date:
    """Hoje no fuso da instância — espelha `_hoje()` do faturamento.

    `date.today()` usa o fuso do runner (UTC no CI): entre 21h e 24h de São
    Paulo a data UTC já é outra e os testes de gatilho/setup quebravam sem
    nenhuma mudança de produto (flakiness de virada de dia).
    """
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def _assinar_contrato_com_setup(client, h, *, setup_valor: str = "1500.00", setup_isento: bool = False):
    _, linha = _negociacao_com_linha(client, h)
    c = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={
            "linha_id": linha["id"],
            "setup_valor": None if setup_isento else setup_valor,
            "setup_isento": setup_isento,
        },
    )
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    _anexar_pdf_assinado(client, h, cid)
    ass = client.post(
        f"/v1/comercial/contratos/{cid}/marcar-assinado",
        headers=h,
        json={"abrir_ticket_implantacao": True},
    )
    assert ass.status_code == 200, ass.text
    return ass.json()


def _titulos(client, h, **params):
    r = client.get("/v1/faturamento/titulos", headers=h, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _comp(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _anexar_boleto(client, h, fatura_id: int) -> None:
    """Baixa exige boleto anexado (#1387)."""
    r = client.post(
        f"/v1/faturamento/faturas/{fatura_id}/anexos",
        headers=h,
        files={"file": ("boleto.pdf", b"%PDF-1.4 teste", "application/pdf")},
        data={"tipo": "boleto"},
    )
    assert r.status_code == 201, r.text


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


def test_data_primeira_venda_manual_gera_competencia_e_audita(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    h_fin = auth_headers["a2"]
    h_at = auth_headers["a1"]
    _patch_politica(client, h_admin, gatilho="dias_apos_marco", gatilho_dias=30)

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]

    assert (
        client.patch(f"/v1/comercial/contratos/{cid}/cobranca", headers=h_at, json={"primeira_venda_pdv": "2026-01-15"}).status_code
        == 403
    )
    futuro = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"primeira_venda_pdv": "2099-01-01"},
    )
    assert futuro.status_code == 400

    r = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"primeira_venda_pdv": "2026-01-15"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["primeira_venda_pdv"] == "2026-01-15"
    assert body["primeira_venda_pdv_por_id"]
    assert body["primeira_venda_pdv_por_nome"] == "Comercial"
    assert body["primeira_venda_pdv_em"]
    assert body["inicio_mensalidade_efetivo"] == "2026-02-14"  # 30 dias após o marco
    assert body["aguardando_motivo"] is None

    # Financeiro também informa a data (RBAC de faturamento.gerar/setor).
    ok_fin = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_fin,
        json={"primeira_venda_pdv": "2026-01-16"},
    )
    assert ok_fin.status_code == 200, ok_fin.text
    assert ok_fin.json()["inicio_mensalidade_efetivo"] == "2026-02-15"

    gerar = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": "2026-02"}
    )
    assert gerar.status_code == 200, gerar.text
    assert gerar.json()["criadas"] == 1

    from app.models.audit_log import AuditLog

    db = SessionLocal()
    try:
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "comercial_contrato", AuditLog.entity_id == cid)
            .all()
        )
        assert any((log.payload_json or {}).get("cobranca", {}).get("primeira_venda_pdv") == "2026-01-16" for log in logs)
    finally:
        db.close()


def test_primeira_fatura_proporcional_com_periodo_coberto(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    h_fin = auth_headers["a2"]
    _patch_politica(client, h_admin, gatilho="data_inicio", proporcional_primeira_fatura=True)

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    r = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"inicio_mensalidade_override": "2026-03-18"},
    )
    assert r.status_code == 200, r.text

    gerar = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": "2026-03"}
    )
    assert gerar.status_code == 200, gerar.text
    assert gerar.json()["criadas"] == 1

    fatura = next(
        f
        for f in client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": "2026-03"}).json()
        if f["contrato_id"] == cid
    )
    # 18/03 até 09/04 = 23 dias; ciclo 10/03–10/04 = 31 dias; 900 * 23/31 = 667,74.
    assert fatura["valor"] == "667.74"
    assert fatura["vencimento"] == "2026-04-10"
    assert fatura["periodo_inicio"] == "2026-03-18"
    assert fatura["periodo_fim"] == "2026-04-09"

    seguinte = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": "2026-04"}
    )
    assert seguinte.status_code == 200, seguinte.text
    assert seguinte.json()["criadas"] == 1
    fatura_cheia = next(
        f
        for f in client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": "2026-04"}).json()
        if f["contrato_id"] == cid
    )
    assert fatura_cheia["valor"] == "900.00"
    assert fatura_cheia["vencimento"] == "2026-05-10"
    assert fatura_cheia["periodo_inicio"] == "2026-04-10"
    assert fatura_cheia["periodo_fim"] == "2026-05-09"


def test_proporcional_inicio_no_proprio_dia_d_e_fatura_cheia(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    h_fin = auth_headers["a2"]
    _patch_politica(client, h_admin, gatilho="data_inicio", proporcional_primeira_fatura=True)

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"inicio_mensalidade_override": "2026-03-10"},
    )
    gerar = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": "2026-03"}
    )
    assert gerar.status_code == 200, gerar.text
    fatura = next(
        f
        for f in client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": "2026-03"}).json()
        if f["contrato_id"] == cid
    )
    assert fatura["valor"] == "900.00"
    assert fatura["periodo_inicio"] == "2026-03-10"
    assert fatura["periodo_fim"] == "2026-04-09"


def test_flag_desligada_primeira_fatura_cheia_mesmo_no_meio_do_ciclo(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_admin = auth_headers["admin"]
    h_fin = auth_headers["a2"]
    _patch_politica(client, h_admin, gatilho="data_inicio", proporcional_primeira_fatura=False)

    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"inicio_mensalidade_override": "2026-03-18"},
    )
    gerar = client.post(
        "/v1/faturamento/faturas/gerar-competencia", headers=h_admin, json={"competencia": "2026-03"}
    )
    assert gerar.status_code == 200, gerar.text
    fatura = next(
        f
        for f in client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": "2026-03"}).json()
        if f["contrato_id"] == cid
    )
    assert fatura["valor"] == "900.00"


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


def test_setup_vira_titulo_no_momento_assinatura_e_nao_duplica(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]
    contrato = _assinar_contrato_com_setup(client, h_com)
    cid = contrato["id"]

    # Sem momento definido, o setup continua só no PDF (compatível com o comportamento anterior).
    assert _titulos(client, h_fin) == []

    r = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"setup_momento": "assinatura"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["setup_momento"] == "assinatura"

    titulos = _titulos(client, h_fin)
    setup = [t for t in titulos if t["contrato_id"] == cid and t["tipo"] == "implantacao"]
    assert len(setup) == 1
    assert setup[0]["fatura_id"] is None
    assert setup[0]["valor"] == "1500.00"
    assert setup[0]["status"] in {"aberto", "vencido"}

    # Reabrir o momento, gerar a competência e rodar o job não duplicam o título.
    client.patch(f"/v1/comercial/contratos/{cid}/cobranca", headers=h_com, json={"setup_momento": "assinatura"})
    client.post(
        "/v1/faturamento/faturas/gerar-competencia",
        headers=h_admin,
        json={"competencia": _comp(_hoje_sp())},
    )
    db = SessionLocal()
    try:
        processar_faturamento_mensal(db)
        db.commit()
    finally:
        db.close()
    setup = [t for t in _titulos(client, h_fin) if t["contrato_id"] == cid and t["tipo"] == "implantacao"]
    assert len(setup) == 1


def test_setup_isento_nao_vira_titulo(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato_com_setup(client, h_com, setup_isento=True)
    cid = contrato["id"]
    r = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"setup_momento": "assinatura"},
    )
    assert r.status_code == 200, r.text
    assert [t for t in _titulos(client, h_fin) if t["tipo"] == "implantacao"] == []


def test_setup_data_combinada_espera_a_data(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato_com_setup(client, h_com)
    cid = contrato["id"]

    sem_data = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"setup_momento": "data_combinada"},
    )
    assert sem_data.status_code == 400

    futuro = (_hoje_sp() + timedelta(days=30)).isoformat()
    r = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"setup_momento": "data_combinada", "setup_data_combinada": futuro},
    )
    assert r.status_code == 200, r.text
    assert [t for t in _titulos(client, h_fin) if t["tipo"] == "implantacao"] == []

    passado = "2026-01-20"
    r = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"setup_data_combinada": passado},
    )
    assert r.status_code == 200, r.text
    setup = [t for t in _titulos(client, h_fin) if t["contrato_id"] == cid and t["tipo"] == "implantacao"]
    assert len(setup) == 1
    assert setup[0]["competencia"] == "2026-01"
    assert setup[0]["vencimento"] == "2026-02-10"


def test_setup_junto_da_primeira_mensalidade(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato_com_setup(client, h_com)
    cid = contrato["id"]
    r = client.patch(
        f"/v1/comercial/contratos/{cid}/cobranca",
        headers=h_com,
        json={"setup_momento": "primeira_mensalidade"},
    )
    assert r.status_code == 200, r.text
    assert [t for t in _titulos(client, h_fin) if t["tipo"] == "implantacao"] == []

    comp = _comp(_hoje_sp())
    gerar = client.post(
        "/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp}
    )
    assert gerar.status_code in (200, 201), gerar.text
    fid = gerar.json()["id"]
    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    assert aprova.status_code == 200, aprova.text

    titulos = _titulos(client, h_fin)
    mensalidade = [t for t in titulos if t["contrato_id"] == cid and t["tipo"] == "mensalidade"]
    setup = [t for t in titulos if t["contrato_id"] == cid and t["tipo"] == "implantacao"]
    assert len(mensalidade) == 1
    assert len(setup) == 1
    assert setup[0]["fatura_id"] is None
    assert setup[0]["valor"] == "1500.00"


def test_cancelar_fatura_cancela_titulo_nao_pago(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_at = auth_headers["a1"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    comp = _comp(_hoje_sp())

    gerar = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp})
    assert gerar.status_code == 201, gerar.text
    fid = gerar.json()["id"]

    assert client.post(f"/v1/faturamento/faturas/{fid}/cancelar", headers=h_at, json={}).status_code == 403
    cancelada = client.post(f"/v1/faturamento/faturas/{fid}/cancelar", headers=h_fin, json={"motivo": "Rescisão no dia 8"})
    assert cancelada.status_code == 200, cancelada.text
    assert cancelada.json()["status"] == "cancelada"

    de_novo = client.post(f"/v1/faturamento/faturas/{fid}/cancelar", headers=h_fin, json={})
    assert de_novo.status_code == 400
    regerar = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp})
    assert regerar.status_code == 400

    # Fatura aprovada com título em aberto: cancelar a fatura cancela o título junto.
    comp2 = _comp(_hoje_sp() + timedelta(days=32))
    gerar2 = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp2})
    assert gerar2.status_code == 201, gerar2.text
    fid2 = gerar2.json()["id"]
    aprova = client.post(f"/v1/faturamento/faturas/{fid2}/aprovar", headers=h_fin)
    assert aprova.status_code == 200, aprova.text
    tid = aprova.json()["titulo"]["id"]

    cancela2 = client.post(f"/v1/faturamento/faturas/{fid2}/cancelar", headers=h_fin, json={})
    assert cancela2.status_code == 200, cancela2.text
    assert cancela2.json()["status"] == "cancelada"
    assert cancela2.json()["titulo"]["status_persistido"] == "cancelado"

    # Título pago obriga estorno antes de cancelar.
    comp3 = _comp(_hoje_sp() + timedelta(days=64))
    gerar3 = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp3})
    fid3 = gerar3.json()["id"]
    aprova3 = client.post(f"/v1/faturamento/faturas/{fid3}/aprovar", headers=h_fin)
    tid3 = aprova3.json()["titulo"]["id"]
    _anexar_boleto(client, h_fin, fid3)
    client.post(f"/v1/faturamento/titulos/{tid3}/baixar", headers=h_fin, json={})
    bloqueia = client.post(f"/v1/faturamento/faturas/{fid3}/cancelar", headers=h_fin, json={})
    assert bloqueia.status_code == 400
    assert "estorne" in bloqueia.json()["detail"].lower()


def test_estornar_e_cancelar_titulo(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    comp = _comp(_hoje_sp())
    gerar = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp})
    fid = gerar.json()["id"]
    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    tid = aprova.json()["titulo"]["id"]

    assert client.post(f"/v1/faturamento/titulos/{tid}/estornar", headers=h_fin, json={}).status_code == 400
    _anexar_boleto(client, h_fin, fid)
    client.post(f"/v1/faturamento/titulos/{tid}/baixar", headers=h_fin, json={"observacao": "PIX"})
    estorno = client.post(
        f"/v1/faturamento/titulos/{tid}/estornar",
        headers=h_fin,
        json={"motivo": "PIX devolvido pelo banco"},
    )
    assert estorno.status_code == 200, estorno.text
    assert estorno.json()["status"] in {"aberto", "vencido"}
    assert estorno.json()["valor_pago"] is None
    assert estorno.json()["baixado_por_id"] is None

    cancela = client.post(
        f"/v1/faturamento/titulos/{tid}/cancelar",
        headers=h_fin,
        json={"motivo": "Contrato rescindido"},
    )
    assert cancela.status_code == 200, cancela.text
    assert cancela.json()["status"] == "cancelado"
    fatura = client.get(f"/v1/faturamento/faturas/{fid}", headers=h_fin).json()
    assert fatura["status"] == "cancelada"

    de_novo = client.post(f"/v1/faturamento/titulos/{tid}/cancelar", headers=h_fin, json={})
    assert de_novo.status_code == 400


def test_rescisao_cancela_faturas_e_titulos_pendentes(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    comp = _comp(_hoje_sp())
    gerar = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp})
    fid = gerar.json()["id"]
    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    tid = aprova.json()["titulo"]["id"]

    rescisao = client.post(f"/v1/comercial/contratos/{cid}/cancelar", headers=h_com)
    assert rescisao.status_code == 200, rescisao.text
    assert rescisao.json()["status"] == "cancelado"

    fatura = client.get(f"/v1/faturamento/faturas/{fid}", headers=h_fin).json()
    assert fatura["status"] == "cancelada"
    titulo = client.get("/v1/faturamento/titulos", headers=h_fin, params={"competencia": comp}).json()
    alvo = next(t for t in titulo if t["id"] == tid)
    assert alvo["status_persistido"] == "cancelado"


def test_data_local_le_assinatura_no_fuso_de_sao_paulo():
    """#1387: assinatura depois das 21h (SP) não pode contar como o dia seguinte (UTC)."""
    from app.services.faturamento import _data_local

    assert _data_local(datetime(2026, 11, 9, 0, 30, tzinfo=timezone.utc)) == date(2026, 11, 8)
    assert _data_local(datetime(2026, 11, 9, 3, 30, tzinfo=timezone.utc)) == date(2026, 11, 9)
    assert _data_local(None) is None


def test_resumo_a_receber_aging_e_previsao(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    comp = _comp(_hoje_sp())
    gerar = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp})
    fid = gerar.json()["id"]
    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    tid_a_vencer = aprova.json()["titulo"]["id"]

    comp2 = _comp(_hoje_sp() + timedelta(days=32))
    gerar2 = client.post("/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": comp2})
    fid2 = gerar2.json()["id"]
    aprova2 = client.post(f"/v1/faturamento/faturas/{fid2}/aprovar", headers=h_fin)
    tid_atrasado = aprova2.json()["titulo"]["id"]

    from app.models.faturamento import TituloReceber

    db = SessionLocal()
    try:
        row = db.query(TituloReceber).filter(TituloReceber.id == tid_atrasado).one()
        row.vencimento = _hoje_sp() - timedelta(days=45)
        db.commit()
    finally:
        db.close()

    resumo = client.get("/v1/faturamento/a-receber/resumo", headers=h_fin)
    assert resumo.status_code == 200, resumo.text
    body = resumo.json()
    assert body["quantidade_titulos"] >= 2
    faixas = {f["chave"]: f for f in body["faixas"]}
    assert faixas["a_vencer"]["quantidade"] >= 1
    assert faixas["vencido_31_60"]["quantidade"] >= 1
    assert faixas["vencido_31_60"]["valor"] == "900.00"
    assert float(body["total_aberto"]) >= 900.0
    assert float(body["total_vencido"]) >= 900.0
    assert float(body["previsao_mes"]["mensalidades_ativas"]) >= 900.0
    assert body["previsao_mes"]["competencia"] == _comp(_hoje_sp())
    # #1385: o resumo alimenta a ficha 360 sem baixar a lista de títulos.
    assert body["proximo_vencimento"] is not None

    from app.models.faturamento import TITULO_PAGO, TITULO_TIPO_MENSALIDADE

    db = SessionLocal()
    try:
        pago = TituloReceber(
            fatura_id=None,
            contrato_id=cid,
            empresa_id=contrato["empresa_id"],
            tipo=TITULO_TIPO_MENSALIDADE,
            competencia=_comp(_hoje_sp()),
            valor=Decimal("250.00"),
            vencimento=_hoje_sp() - timedelta(days=5),
            status=TITULO_PAGO,
            pago_em=_hoje_sp(),
            valor_pago=Decimal("250.00"),
        )
        db.add(pago)
        db.commit()
    finally:
        db.close()

    resumo_pago = client.get("/v1/faturamento/a-receber/resumo", headers=h_fin)
    assert resumo_pago.status_code == 200, resumo_pago.text
    body_pago = resumo_pago.json()
    assert float(body_pago["pago_ano"]) >= 250.0
    assert body_pago["pago_ano_quantidade"] >= 1


def test_filtros_rede_empresa_tipo_e_csv(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_at = auth_headers["a1"]
    contrato = _assinar_contrato_com_setup(client, h_com)
    cid = contrato["id"]
    empresa_id = contrato["empresa_id"]
    rede_id = contrato["rede_id"]
    assert empresa_id and rede_id

    client.patch(f"/v1/comercial/contratos/{cid}/cobranca", headers=h_com, json={"setup_momento": "assinatura"})
    gerar = client.post(
        "/v1/faturamento/faturas", headers=h_fin, json={"contrato_id": cid, "competencia": _comp(_hoje_sp())}
    )
    assert gerar.status_code == 201, gerar.text
    client.post(f"/v1/faturamento/faturas/{gerar.json()['id']}/aprovar", headers=h_fin)

    filtrados = client.get(
        "/v1/faturamento/titulos",
        headers=h_fin,
        params={"rede_id": rede_id, "empresa_id": empresa_id},
    )
    assert filtrados.status_code == 200, filtrados.text
    assert filtrados.json()
    assert all(t["empresa_id"] == empresa_id for t in filtrados.json())

    errado = client.get("/v1/faturamento/titulos", headers=h_fin, params={"rede_id": rede_id + 999})
    assert errado.status_code == 200
    assert errado.json() == []

    so_implantacao = client.get("/v1/faturamento/titulos", headers=h_fin, params={"tipo": "implantacao"})
    assert so_implantacao.status_code == 200, so_implantacao.text
    assert so_implantacao.json()
    assert all(t["tipo"] == "implantacao" for t in so_implantacao.json())
    assert client.get("/v1/faturamento/titulos", headers=h_fin, params={"tipo": "inventado"}).status_code == 400

    csv = client.get("/v1/faturamento/titulos/export.csv", headers=h_fin, params={"tipo": "implantacao"})
    assert csv.status_code == 200, csv.text
    assert "text/csv" in csv.headers["content-type"]
    texto = csv.content.decode("utf-8-sig")
    linhas = texto.strip().splitlines()
    assert linhas[0].startswith("Tipo;Cliente;CNPJ")
    assert "implantacao" in texto
    assert "1500.00" in texto
    assert client.get("/v1/faturamento/titulos/export.csv", headers=h_at).status_code == 403

    resumo = client.get("/v1/faturamento/a-receber/resumo", headers=h_fin, params={"rede_id": rede_id})
    assert resumo.status_code == 200, resumo.text
    assert resumo.json()["quantidade_titulos"] >= 1
    errado_resumo = client.get("/v1/faturamento/a-receber/resumo", headers=h_fin, params={"rede_id": rede_id + 999})
    assert errado_resumo.status_code == 200
    assert errado_resumo.json()["quantidade_titulos"] == 0


def test_csv_a_receber_neutraliza_formula(client, auth_headers):
    """CSV do A receber: nome de cliente que parece fórmula não vira fórmula no Excel."""
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]

    contrato = _assinar_contrato(client, h_com)
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = _comp(inicio)
    gen = client.post(
        "/v1/faturamento/faturas/gerar-competencia",
        headers=h_admin,
        json={"competencia": comp},
    )
    assert gen.status_code == 200, gen.text

    faturas = client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": comp}).json()
    fatura = next(f for f in faturas if f["contrato_id"] == contrato["id"])
    assert client.post(f"/v1/faturamento/faturas/{fatura['id']}/aprovar", headers=h_fin).status_code == 200

    malicioso = "=1+1"
    up = client.patch(
        f"/v1/crm/negociacoes/{contrato['negociacao_id']}/linhas/{contrato['negociacao_linha_cnpj_id']}",
        headers=h_com,
        json={"razao_social": malicioso},
    )
    assert up.status_code == 200, up.text

    csv_r = client.get("/v1/faturamento/titulos/export.csv", headers=h_fin)
    assert csv_r.status_code == 200, csv_r.text
    assert f"'{malicioso}" in csv_r.text
    assert f";{malicioso}" not in csv_r.text.replace("\ufeff", "")
