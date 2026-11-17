"""Assinatura eletrônica multiparte — DocuSeal fakeado (#1380 / #1429)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.docuseal_client import DocusealError, DocusealSubmission, DocusealSubmitterOut, set_client_factory
from tests.test_comercial_contrato import (
    _anexar_pdf_assinado,
    _criar_item_catalogo,
    _negociacao_com_linha,
)


@pytest.fixture(autouse=True)
def _pdf_fake(monkeypatch):
    monkeypatch.setattr(
        "app.services.comercial_proposta.html_para_pdf",
        lambda html: b"%PDF-1.4\n" + html.encode("utf-8"),
    )


@pytest.fixture(autouse=True)
def _docuseal_env(monkeypatch):
    monkeypatch.setattr("app.config.settings.DOCUSEAL_URL", "http://docuseal.test")
    monkeypatch.setattr("app.config.settings.DOCUSEAL_API_TOKEN", "tok-teste")
    monkeypatch.setattr("app.config.settings.DOCUSEAL_WEBHOOK_SECRET", "segredo-teste")
    monkeypatch.setattr("app.config.settings.DOCUSEAL_TEMPLATE_ID", "tpl-1")
    monkeypatch.setattr("app.config.settings.DOCUSEAL_EXPIRACAO_DIAS", 7)
    yield
    set_client_factory(None)


def _payload_padrao(**extra):
    base = {
        "signatarios": [
            {
                "papel": "contratante",
                "nome": "Maria Silva",
                "email": "maria@posto.com",
                "cpf": "39053344705",
                "telefone": "11999990000",
            },
            {
                "papel": "contratada",
                "nome": "João Duplex",
                "email": "joao@duplex.com",
                "cpf": "52998224725",
            },
            {
                "papel": "testemunha",
                "nome": "Ana Testemunha",
                "email": "ana@ex.com",
                "cpf": "11144477735",
            },
            {
                "papel": "testemunha",
                "nome": "Pedro Testemunha",
                "email": "pedro@ex.com",
                "cpf": "15350946056",
            },
        ],
    }
    base.update(extra)
    return base


class _FakeDocuseal:
    def __init__(self, *, falhar_criar: bool = False):
        self.falhar_criar = falhar_criar
        self.cancelados: list[str] = []
        self.baixados: list[str] = []
        self.ultimo_submitters: list[dict] = []

    def criar_submissao(self, *, template_id: str, submitters: list[dict], send_email: bool = False):
        if self.falhar_criar:
            raise DocusealError("DocuSeal indisponível no teste.")
        self.ultimo_submitters = list(submitters)
        outs = []
        for i, s in enumerate(submitters):
            slug = f"slug-{i + 1}"
            outs.append(
                DocusealSubmitterOut(
                    role=s["role"],
                    slug=slug,
                    link_assinatura=f"http://docuseal.test/s/{slug}",
                    email=s.get("email"),
                )
            )
        return DocusealSubmission(submission_id="sub-100", submitters=outs, raw={"id": "sub-100"})

    def cancelar_submissao(self, submission_id: str) -> None:
        self.cancelados.append(submission_id)

    def baixar_url(self, url: str) -> bytes:
        self.baixados.append(url)
        if "audit" in url:
            return b"%PDF-1.4 audit"
        if "selfie" in url or url.endswith(".jpg"):
            return b"\xff\xd8\xff selfie"
        return b"%PDF-1.4 signed-docuseal"


def _setup_contrato(client, auth_headers):
    h_admin = auth_headers["admin"]
    h = auth_headers["comercial"]
    item_id = _criar_item_catalogo(client, h_admin)
    tmpl = client.post(
        "/v1/comercial/contrato-templates",
        headers=h_admin,
        json={
            "nome": "Modelo Assinatura 1380",
            "conteudo_html": "<p>Contrato {{razao_social}}</p>",
            "ativo": True,
        },
    )
    assert tmpl.status_code == 201, tmpl.text
    neg_id, linha = _negociacao_com_linha(client, h, item_id=item_id, cnpj="11.222.333/0001-81")
    gerado = client.post(
        "/v1/comercial/contratos",
        headers=h,
        json={"linha_id": linha["id"], "template_id": tmpl.json()["id"], "data_inicio": "2026-11-12"},
    )
    assert gerado.status_code == 201, gerado.text
    return h, h_admin, gerado.json()


def test_enviar_assinatura_cria_envelope_multiparte(client, auth_headers):
    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    h, _, contrato = _setup_contrato(client, auth_headers)
    r = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provedor"] == "docuseal"
    assert body["status"] == "enviado"
    assert body["submission_id"] == "sub-100"
    assert len(body["partes"]) == 4
    papeis = [p["papel"] for p in body["partes"]]
    assert papeis.count("contratante") == 1
    assert papeis.count("contratada") == 1
    assert papeis.count("testemunha") == 2
    assert all(p["link_assinatura"] for p in body["partes"])
    assert [s["role"] for s in fake.ultimo_submitters] == [
        "Contratante",
        "Contratada",
        "Testemunha 1",
        "Testemunha 2",
    ]
    assert all(
        any(f.get("name") == "CPF" for f in (s.get("fields") or []))
        for s in fake.ultimo_submitters
    )
    assert all(p.get("cpf_mascarado") for p in body["partes"])

    detalhe = client.get(f"/v1/comercial/contratos/{contrato['id']}", headers=h)
    assert detalhe.status_code == 200
    assert detalhe.json()["assinatura_modo"] == "docuseal"
    assert len(detalhe.json()["assinatura"]["partes"]) == 4


def test_atendente_403_enviar_email_e_evidencias(client, auth_headers):
    """Atendente sem contratos.emitir/ver não acessa o fluxo de assinatura."""
    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    h, _, contrato = _setup_contrato(client, auth_headers)
    env = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    ).json()
    h_a1 = auth_headers["a1"]
    cid = contrato["id"]
    parte_id = env["partes"][0]["id"]

    assert (
        client.post(
            f"/v1/comercial/contratos/{cid}/assinatura/enviar",
            headers=h_a1,
            json=_payload_padrao(),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/comercial/contratos/{cid}/assinatura/partes/{parte_id}/enviar-email",
            headers=h_a1,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/comercial/contratos/{cid}/assinatura/cancelar",
            headers=h_a1,
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/v1/comercial/contratos/{cid}/assinatura/evidencias/pdf",
            headers=h_a1,
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/v1/comercial/contratos/{cid}/assinatura",
            headers=h_a1,
        ).status_code
        == 403
    )


def test_enviar_exige_contratante_e_contratada(client, auth_headers):
    set_client_factory(lambda: _FakeDocuseal())
    h, _, contrato = _setup_contrato(client, auth_headers)
    r = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json={
            "signatarios": [
                {
                    "papel": "contratante",
                    "nome": "Só um",
                    "email": "a@a.com",
                    "cpf": "39053344705",
                },
            ]
        },
    )
    assert r.status_code == 422


def test_enviar_rejeita_cpf_invalido(client, auth_headers):
    set_client_factory(lambda: _FakeDocuseal())
    h, _, contrato = _setup_contrato(client, auth_headers)
    payload = _payload_padrao()
    payload["signatarios"][0]["cpf"] = "11111111111"
    r = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=payload,
    )
    assert r.status_code == 422


def test_enviar_email_convite(client, auth_headers, monkeypatch):
    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    enviados: list[dict] = []

    def _fake_email(db, *, to_addr, subject, body, **kwargs):
        enviados.append({"to": to_addr, "subject": subject, "body": body})
        return "msg-teste"

    monkeypatch.setattr(
        "app.services.contrato_assinatura.enviar_mensagem_texto_sistema",
        _fake_email,
    )
    h, _, contrato = _setup_contrato(client, auth_headers)
    env = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    ).json()
    parte = env["partes"][0]
    r = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/partes/{parte['id']}/enviar-email",
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert enviados and enviados[0]["to"] == parte["email"]
    assert parte["link_assinatura"] in enviados[0]["body"]


def test_reenvio_sem_forcar_conflita_e_com_forcar_cancela_anterior(client, auth_headers):
    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    h, _, contrato = _setup_contrato(client, auth_headers)
    payload = _payload_padrao()
    assert (
        client.post(
            f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
            headers=h,
            json=payload,
        ).status_code
        == 200
    )
    conflito = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=payload,
    )
    assert conflito.status_code == 409

    class _Fake2(_FakeDocuseal):
        def criar_submissao(self, *, template_id: str, submitters: list[dict], send_email: bool = False):
            outs = [
                DocusealSubmitterOut(
                    role=s["role"],
                    slug=f"slug-b-{i}",
                    link_assinatura=f"http://docuseal.test/s/slug-b-{i}",
                    email=s.get("email"),
                )
                for i, s in enumerate(submitters)
            ]
            return DocusealSubmission(submission_id="sub-200", submitters=outs, raw={})

    fake2 = _Fake2()
    set_client_factory(lambda: fake2)
    ok = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json={**payload, "forcar_reenvio": True},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["submission_id"] == "sub-200"
    assert "sub-100" in fake2.cancelados or "sub-100" in fake.cancelados


def test_webhook_parcial_nao_marca_contrato_e_completo_sim(client, auth_headers):
    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    h, _, contrato = _setup_contrato(client, auth_headers)
    env = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    ).json()
    partes = env["partes"]

    # Primeira parte conclui — envelope parcial; contrato ainda não assinado.
    parcial = client.post(
        "/v1/webhooks/docuseal",
        headers={"X-Docuseal-Secret": "segredo-teste"},
        json={
            "event_type": "form.completed",
            "data": {
                "submission_id": env["submission_id"],
                "slug": partes[0]["submitter_slug"],
                "email": partes[0]["email"],
                "role": partes[0]["role_docuseal"],
                "status": "completed",
            },
        },
    )
    assert parcial.status_code == 200, parcial.text
    assert parcial.json()["status"] == "parcial"
    detalhe = client.get(f"/v1/comercial/contratos/{contrato['id']}", headers=h).json()
    assert detalhe["status"] != "assinado"
    assert detalhe["assinatura"]["status"] == "parcial"

    # Demais partes + submission.completed com PDF.
    for p in partes[1:]:
        client.post(
            "/v1/webhooks/docuseal",
            headers={"X-Docuseal-Secret": "segredo-teste"},
            json={
                "event_type": "form.completed",
                "data": {
                    "submission_id": env["submission_id"],
                    "slug": p["submitter_slug"],
                    "email": p["email"],
                    "role": p["role_docuseal"],
                    "status": "completed",
                },
            },
        )

    ok = client.post(
        "/v1/webhooks/docuseal",
        headers={"X-Docuseal-Secret": "segredo-teste"},
        json={
            "event_type": "submission.completed",
            "data": {
                "submission_id": env["submission_id"],
                "status": "completed",
                "combined_document_url": "http://docuseal.test/doc.pdf",
                "audit_log_url": "http://docuseal.test/audit.pdf",
                "values": {"selfie": "http://docuseal.test/selfie.jpg"},
            },
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "assinado"

    detalhe = client.get(f"/v1/comercial/contratos/{contrato['id']}", headers=h).json()
    assert detalhe["status"] == "assinado"
    assert detalhe["tem_pdf_assinado"] is True
    assert detalhe["assinatura"]["tem_audit_log"] is True
    assert all(p["status"] == "assinado" for p in detalhe["assinatura"]["partes"])


def test_webhook_invalido_e_recusa(client, auth_headers):
    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    h, _, contrato = _setup_contrato(client, auth_headers)
    env = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    ).json()

    sem_segredo = client.post(
        "/v1/webhooks/docuseal",
        json={"event_type": "submission.completed", "data": {"submission_id": env["submission_id"]}},
    )
    assert sem_segredo.status_code == 401

    r = client.post(
        "/v1/webhooks/docuseal",
        headers={"X-Docuseal-Secret": "segredo-teste"},
        json={
            "event_type": "form.declined",
            "data": {
                "submission_id": env["submission_id"],
                "slug": env["partes"][0]["submitter_slug"],
                "email": env["partes"][0]["email"],
                "status": "declined",
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "recusado"


def test_anexo_externo_cria_envelope_externo(client, auth_headers):
    h, _, contrato = _setup_contrato(client, auth_headers)
    _anexar_pdf_assinado(client, h, contrato["id"])
    detalhe = client.get(f"/v1/comercial/contratos/{contrato['id']}", headers=h).json()
    assert detalhe["assinatura_modo"] == "externo"
    assert detalhe["assinatura"]["status"] == "assinado"
    assert detalhe["assinatura"]["provedor"] == "externo"


def test_erro_docuseal_aparece_na_ficha(client, auth_headers):
    set_client_factory(lambda: _FakeDocuseal(falhar_criar=True))
    h, _, contrato = _setup_contrato(client, auth_headers)
    r = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    )
    assert r.status_code == 502
    detalhe = client.get(f"/v1/comercial/contratos/{contrato['id']}", headers=h).json()
    assert detalhe["assinatura"]["status"] == "erro"
    assert "indisponível" in (detalhe["assinatura"]["ultimo_erro"] or "").lower()


def test_cancelar_envelope_libera_novo_envio(client, auth_headers):
    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    h, _, contrato = _setup_contrato(client, auth_headers)
    client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    )
    cancel = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/cancelar",
        headers=h,
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelado"
    assert fake.cancelados == ["sub-100"]

    class _FakeNovo(_FakeDocuseal):
        def criar_submissao(self, *, template_id: str, submitters: list[dict], send_email: bool = False):
            outs = [
                DocusealSubmitterOut(
                    role=s["role"],
                    slug=f"slug-n-{i}",
                    link_assinatura=f"http://docuseal.test/s/slug-n-{i}",
                    email=s.get("email"),
                )
                for i, s in enumerate(submitters)
            ]
            return DocusealSubmission(submission_id="sub-300", submitters=outs, raw={})

    set_client_factory(lambda: _FakeNovo())
    novo = client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    )
    assert novo.status_code == 200
    assert novo.json()["submission_id"] == "sub-300"


def test_expiracao_libera_status(client, auth_headers, db_session):
    from app.models.contrato_assinatura import ContratoAssinatura, STATUS_ENVIADO, STATUS_EXPIRADO
    from app.services import contrato_assinatura as assinatura_svc

    fake = _FakeDocuseal()
    set_client_factory(lambda: fake)
    h, _, contrato = _setup_contrato(client, auth_headers)
    client.post(
        f"/v1/comercial/contratos/{contrato['id']}/assinatura/enviar",
        headers=h,
        json=_payload_padrao(),
    )
    env = (
        db_session.query(ContratoAssinatura)
        .filter(ContratoAssinatura.contrato_id == contrato["id"], ContratoAssinatura.status == STATUS_ENVIADO)
        .one()
    )
    env.expira_em = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    assinatura_svc.sincronizar_expiracao(db_session, contrato["id"])
    db_session.refresh(env)
    assert env.status == STATUS_EXPIRADO
