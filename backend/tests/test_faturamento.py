"""Fatura interna e aprovação do financeiro (#326 / #363 / #364)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.database import SessionLocal
from app.services.faturamento import processar_faturamento_mensal, vencimento_da_competencia
from tests.test_implantacao import _assinar_contrato


def _anexar_boleto(client, h, fatura_id: int) -> None:
    """Baixa exige boleto anexado (#1387)."""
    r = client.post(
        f"/v1/faturamento/faturas/{fatura_id}/anexos",
        headers=h,
        files={"file": ("boleto.pdf", b"%PDF-1.4 teste", "application/pdf")},
        data={"tipo": "boleto"},
    )
    assert r.status_code == 201, r.text


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
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = f"{inicio.year:04d}-{inicio.month:02d}"
    vencto = vencimento_da_competencia(comp).isoformat()

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
        json={"contrato_id": cid, "competencia": comp},
    )
    assert g.status_code == 201, g.text
    fatura = g.json()
    assert fatura["status"] == "aguardando_aprovacao"
    assert fatura["competencia"] == comp
    assert fatura["emite_nfse"] is False
    assert float(fatura["valor"]) == 900.0
    assert fatura["vencimento"] == vencto
    fid = fatura["id"]

    dup = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": comp},
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
    ainda = client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": comp})
    assert any(x["id"] == fid and x["status"] == "rejeitada" for x in ainda.json())

    lote = client.post(
        "/v1/faturamento/faturas/gerar-competencia",
        headers=h_admin,
        json={"competencia": comp},
    )
    assert lote.status_code == 200, lote.text
    assert lote.json()["reabertas"] >= 1
    reaberta = client.get("/v1/faturamento/faturas", headers=h_fin, params={"competencia": comp})
    assert any(x["id"] == fid and x["status"] == "aguardando_aprovacao" for x in reaberta.json())

    regen = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": comp},
    )
    assert regen.status_code == 200
    assert regen.json()["id"] == fid
    assert regen.json()["status"] == "aguardando_aprovacao"
    assert regen.json()["rejeicao_motivo"] is None

    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    assert aprova.status_code == 200, aprova.text
    assert aprova.json()["status"] == "aprovada"
    assert aprova.json()["aprovada_por_id"]
    assert aprova.json()["titulo"]
    assert aprova.json()["titulo"]["status"] in {"aberto", "vencido"}
    assert aprova.json()["titulo"]["fatura_id"] == fid

    recusa_aprovada = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": comp},
    )
    assert recusa_aprovada.status_code == 400

    job = client.post(
        "/v1/faturamento/faturas/gerar-competencia",
        headers=h_admin,
        json={"competencia": comp},
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


def test_anexos_manuais_boleto_sem_nf(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    empresa_id = contrato["empresa_id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = f"{inicio.year:04d}-{inicio.month:02d}"

    client.patch(f"/v1/empresas/{empresa_id}", headers=h_admin, json={"emite_nfse": False})
    g = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": comp},
    )
    assert g.status_code == 201, g.text
    fid = g.json()["id"]
    assert client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_fin,
        files={"file": ("boleto.pdf", b"%PDF-1.4 teste", "application/pdf")},
        data={"tipo": "boleto"},
    ).status_code == 400

    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    assert aprova.status_code == 200

    nf_recusado = client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_fin,
        files={"file": ("nota.pdf", b"%PDF-1.4 nf", "application/pdf")},
        data={"tipo": "nfse_pdf"},
    )
    assert nf_recusado.status_code == 400

    com_recusado = client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_com,
        files={"file": ("boleto.pdf", b"%PDF-1.4 teste", "application/pdf")},
        data={"tipo": "boleto"},
    )
    assert com_recusado.status_code == 403

    up = client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_fin,
        files={"file": ("boleto.pdf", b"%PDF-1.4 teste", "application/pdf")},
        data={"tipo": "boleto"},
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["documentos_completos"] is True
    assert len(body["anexos"]) == 1
    assert body["anexos"][0]["tipo"] == "boleto"
    anexo_id = body["anexos"][0]["id"]

    linha = "0" * 47
    docs = client.patch(
        f"/v1/faturamento/faturas/{fid}/documentos",
        headers=h_fin,
        json={"boleto_linha_digitavel": linha, "boleto_nosso_numero": "12345"},
    )
    assert docs.status_code == 200, docs.text
    assert docs.json()["boleto_linha_digitavel"] == linha
    assert docs.json()["boleto_nosso_numero"] == "12345"

    invalida = client.patch(
        f"/v1/faturamento/faturas/{fid}/documentos",
        headers=h_fin,
        json={"boleto_linha_digitavel": "123"},
    )
    assert invalida.status_code == 400

    dl = client.get(f"/v1/faturamento/faturas/{fid}/anexos/{anexo_id}/download", headers=h_fin)
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")

    up2 = client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_fin,
        files={"file": ("boleto-2.pdf", b"%PDF-1.4 segundo", "application/pdf")},
        data={"tipo": "boleto"},
    )
    assert up2.status_code == 201
    assert len(up2.json()["anexos"]) == 1

    filtrado = client.get("/v1/faturamento/faturas", headers=h_fin, params={"emite_nfse": False, "competencia": comp})
    assert filtrado.status_code == 200
    assert any(x["id"] == fid for x in filtrado.json())
    so_nf = client.get("/v1/faturamento/faturas", headers=h_fin, params={"emite_nfse": True, "competencia": comp})
    assert all(x["id"] != fid for x in so_nf.json())


def test_anexos_manuais_nfse_obrigatoria(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = f"{inicio.year:04d}-{inicio.month:02d}"
    g = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": comp},
    )
    fid = g.json()["id"]
    client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)

    so_boleto = client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_fin,
        files={"file": ("boleto.pdf", b"%PDF-1.4 teste", "application/pdf")},
        data={"tipo": "boleto"},
    )
    assert so_boleto.status_code == 201
    assert so_boleto.json()["documentos_completos"] is False

    nf = client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_fin,
        files={"file": ("nfse.pdf", b"%PDF-1.4 nota", "application/pdf")},
        data={"tipo": "nfse_pdf"},
    )
    assert nf.status_code == 201, nf.text
    assert nf.json()["documentos_completos"] is True
    assert {a["tipo"] for a in nf.json()["anexos"]} == {"boleto", "nfse_pdf"}

    xml = client.post(
        f"/v1/faturamento/faturas/{fid}/anexos",
        headers=h_fin,
        files={"file": ("nfse.xml", b"<nfse/>", "application/xml")},
        data={"tipo": "nfse_xml"},
    )
    assert xml.status_code == 201
    assert len(xml.json()["anexos"]) == 3

    anexo_nf = next(a for a in xml.json()["anexos"] if a["tipo"] == "nfse_pdf")
    rem = client.delete(f"/v1/faturamento/faturas/{fid}/anexos/{anexo_nf['id']}", headers=h_fin)
    assert rem.status_code == 200
    assert rem.json()["documentos_completos"] is False


def test_titulo_receber_baixa_manual_e_vencido(client, auth_headers):
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato(client, h_com)
    cid = contrato["id"]
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = f"{inicio.year:04d}-{inicio.month:02d}"
    g = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": cid, "competencia": comp},
    )
    fid = g.json()["id"]
    assert client.get("/v1/faturamento/titulos", headers=h_com).status_code == 403
    assert client.get("/v1/faturamento/titulos", headers=h_fin).json() == []

    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    titulo = aprova.json()["titulo"]
    tid = titulo["id"]
    assert titulo["status"] in {"aberto", "vencido"}
    assert titulo["tem_boleto"] is False

    lista = client.get("/v1/faturamento/titulos", headers=h_fin, params={"competencia": comp})
    assert lista.status_code == 200
    item = next(x for x in lista.json() if x["id"] == tid)
    assert item["tem_boleto"] is False

    _anexar_boleto(client, h_fin, fid)
    com_boleto = client.get("/v1/faturamento/titulos", headers=h_fin, params={"competencia": comp})
    assert next(x for x in com_boleto.json() if x["id"] == tid)["tem_boleto"] is True

    from app.models.faturamento import TituloReceber

    db = SessionLocal()
    try:
        row = db.query(TituloReceber).filter(TituloReceber.id == tid).one()
        row.vencimento = date(2020, 1, 10)
        db.commit()
    finally:
        db.close()

    vencidos = client.get("/v1/faturamento/titulos", headers=h_fin, params={"status": "vencido"})
    assert any(x["id"] == tid and x["status"] == "vencido" for x in vencidos.json())
    abertos = client.get("/v1/faturamento/titulos", headers=h_fin, params={"status": "aberto"})
    assert all(x["id"] != tid for x in abertos.json())

    assert client.post(f"/v1/faturamento/titulos/{tid}/baixar", headers=h_com, json={}).status_code == 403
    baixa = client.post(
        f"/v1/faturamento/titulos/{tid}/baixar",
        headers=h_fin,
        json={"observacao": "PIX conferido no extrato"},
    )
    assert baixa.status_code == 200, baixa.text
    assert baixa.json()["status"] == "pago"
    assert baixa.json()["baixa_observacao"] == "PIX conferido no extrato"
    assert float(baixa.json()["valor_pago"]) == float(titulo["valor"])

    de_novo = client.post(f"/v1/faturamento/titulos/{tid}/baixar", headers=h_fin, json={})
    assert de_novo.status_code == 400


def _fatura_aprovada_sem_boleto(client, auth_headers):
    """Contrato + fatura aprovada (sem boleto) e o título a receber correspondente."""
    h_com = auth_headers["comercial"]
    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato(client, h_com)
    inicio = date.fromisoformat(str(contrato["data_inicio"]))
    comp = f"{inicio.year:04d}-{inicio.month:02d}"
    gerar = client.post(
        "/v1/faturamento/faturas",
        headers=h_fin,
        json={"contrato_id": contrato["id"], "competencia": comp},
    )
    assert gerar.status_code == 201, gerar.text
    fid = gerar.json()["id"]
    aprova = client.post(f"/v1/faturamento/faturas/{fid}/aprovar", headers=h_fin)
    assert aprova.status_code == 200, aprova.text
    return contrato, fid, comp, aprova.json()["titulo"]


def test_baixa_exige_boleto_e_excecao_auditada(client, auth_headers):
    """#1387: sem boleto → 400; exceção com motivo exige faturamento.aprovar e vai para a auditoria."""
    h_fin = auth_headers["a2"]
    h_admin = auth_headers["admin"]
    _contrato, fid, _comp, titulo = _fatura_aprovada_sem_boleto(client, auth_headers)
    tid = titulo["id"]

    sem_boleto = client.post(f"/v1/faturamento/titulos/{tid}/baixar", headers=h_fin, json={})
    assert sem_boleto.status_code == 400
    assert sem_boleto.json()["detail"] == "Anexe o boleto da fatura antes de dar baixa."

    # Financeiro sem a permissão do grupo não usa a exceção.
    motivo = "Boleto emitido no banco e enviado ao cliente por WhatsApp"
    sem_permissao = client.post(
        f"/v1/faturamento/titulos/{tid}/baixar",
        headers=h_fin,
        json={"sem_documento_motivo": motivo},
    )
    assert sem_permissao.status_code == 403
    assert "faturamento.aprovar" in sem_permissao.json()["detail"]

    # Motivo curto e motivo ausente continuam bloqueados até para quem pode a exceção.
    curto = client.post(
        f"/v1/faturamento/titulos/{tid}/baixar",
        headers=h_admin,
        json={"sem_documento_motivo": "curto"},
    )
    assert curto.status_code == 400
    assert "10 a 500" in curto.json()["detail"]
    longo = client.post(
        f"/v1/faturamento/titulos/{tid}/baixar",
        headers=h_admin,
        json={"sem_documento_motivo": "x" * 501},
    )
    assert longo.status_code == 400
    assert "10 a 500" in longo.json()["detail"]
    ausente = client.post(f"/v1/faturamento/titulos/{tid}/baixar", headers=h_admin, json={})
    assert ausente.status_code == 400
    assert ausente.json()["detail"] == "Anexe o boleto da fatura antes de dar baixa."

    ok = client.post(
        f"/v1/faturamento/titulos/{tid}/baixar",
        headers=h_admin,
        json={"sem_documento_motivo": motivo},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "pago"
    assert ok.json()["baixa_observacao"] == f"Baixa sem boleto: {motivo}"

    from app.models import Atendente, AuditLog

    db = SessionLocal()
    try:
        log = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "faturamento_titulo",
                AuditLog.entity_id == tid,
                AuditLog.action == "baixa_sem_boleto",
            )
            .one()
        )
        assert log.payload_json == {"motivo": motivo, "fatura_id": fid}
        admin = db.query(Atendente).filter(Atendente.email == "admin@test.local").one()
        assert log.atendente_id == admin.id
    finally:
        db.close()


def test_baixa_com_boleto_anexado_libera_e_lista_tem_boleto(client, auth_headers):
    """#1387: boleto anexado libera a baixa normal e a lista expõe tem_boleto."""
    h_fin = auth_headers["a2"]
    _contrato, fid, comp, titulo = _fatura_aprovada_sem_boleto(client, auth_headers)
    tid = titulo["id"]

    _anexar_boleto(client, h_fin, fid)
    lista = client.get("/v1/faturamento/titulos", headers=h_fin, params={"competencia": comp})
    assert next(x for x in lista.json() if x["id"] == tid)["tem_boleto"] is True

    baixa = client.post(f"/v1/faturamento/titulos/{tid}/baixar", headers=h_fin, json={"observacao": "PIX"})
    assert baixa.status_code == 200, baixa.text
    assert baixa.json()["baixa_observacao"] == "PIX"
    assert baixa.json()["tem_boleto"] is True


def test_baixa_titulo_implantacao_sem_fatura_nao_exige_boleto(client, auth_headers):
    """#1387: título sem fatura (implantação/multa) continua com baixa normal."""
    from app.models.faturamento import TITULO_ABERTO, TITULO_TIPO_IMPLANTACAO, TituloReceber

    h_fin = auth_headers["a2"]
    contrato = _assinar_contrato(client, auth_headers["comercial"])
    db = SessionLocal()
    try:
        row = TituloReceber(
            fatura_id=None,
            contrato_id=contrato["id"],
            empresa_id=contrato["empresa_id"],
            tipo=TITULO_TIPO_IMPLANTACAO,
            competencia=f"{date.today().year:04d}-{date.today().month:02d}",
            valor=Decimal("1500.00"),
            vencimento=date(2026, 1, 10),
            status=TITULO_ABERTO,
        )
        db.add(row)
        db.commit()
        tid = row.id
    finally:
        db.close()

    baixa = client.post(f"/v1/faturamento/titulos/{tid}/baixar", headers=h_fin, json={})
    assert baixa.status_code == 200, baixa.text
    assert baixa.json()["status"] == "pago"
    assert baixa.json()["tem_boleto"] is False
    assert baixa.json()["baixa_observacao"] is None
