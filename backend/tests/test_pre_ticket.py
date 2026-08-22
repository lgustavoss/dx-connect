"""Testes de pré-ticket IA (#809 / #811 / #812 / #813 / #814)."""

from app.models import AuditLog
from app.services.pre_ticket_metricas import OpenAiCallMeta
from app.services.pre_ticket_redaction import redact_text


def _analise_fake() -> dict:
    return {
        "classificacao": "melhoria",
        "lacunas_perguntas": ["Qual ambiente reproduz?"],
        "riscos": ["Regressão no fluxo de tickets"],
        "viabilidade": "viavel",
        "titulo_sugerido": "Melhorar triagem de tickets duplicados",
        "criterios_aceite": ["Detectar duplicata antes de abrir ticket"],
        "corpo_sugerido": "## Contexto\nCliente reporta duplicatas.",
        "dependencias": [],
        "prompt_version": "v1",
    }


def _mock_openai_ok(_s, _u):
    return (
        {k: v for k, v in _analise_fake().items() if k != "prompt_version"},
        OpenAiCallMeta(
            latencia_ms=100,
            model="gpt-4o-mini",
            prompt_version="v1",
            tokens_input=80,
            tokens_output=40,
            erro_tipo="ok",
        ),
    )


def _criar_sessao_minima(client, headers):
    r = client.post(
        "/v1/pre-ticket/sessoes",
        headers=headers,
        json={
            "contexto": "Contexto mínimo válido para testes automatizados do pré-ticket IA.",
            "problema": "Problema mínimo válido para testes automatizados do pré-ticket IA.",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _aprovar_sessao(client, headers, sessao_id, monkeypatch):
    monkeypatch.setattr("app.services.pre_ticket_ai.settings.PRE_TICKET_AI_ENABLED", True)
    monkeypatch.setattr("app.services.pre_ticket_ai.settings.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.pre_ticket_ai._chamar_openai",
        _mock_openai_ok,
    )
    assert client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/analisar",
        headers=headers,
    ).status_code == 200
    r = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/aprovar",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_redact_text_mascara_email():
    assert "[EMAIL_REDACTED]" in redact_text("Contacte joao@empresa.com.br hoje")


def test_pre_ticket_status_admin(client, auth_headers):
    r = client.get("/v1/pre-ticket/status", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert "ia_habilitada" in body
    assert "github_habilitado" in body


def test_pre_ticket_status_nao_admin_regista_audit(client, auth_headers, db_session):
    r = client.get("/v1/pre-ticket/status", headers=auth_headers["a1"])
    assert r.status_code == 403
    denied = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "pre_ticket_sessao", AuditLog.action == "acesso_negado")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert denied is not None
    assert denied.payload_json.get("acao") == "acessar"


def test_pre_ticket_criar_e_analisar_mock(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.services.pre_ticket_ai.settings.PRE_TICKET_AI_ENABLED", True)
    monkeypatch.setattr("app.services.pre_ticket_ai.settings.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.pre_ticket_ai._chamar_openai",
        _mock_openai_ok,
    )

    criar = client.post(
        "/v1/pre-ticket/sessoes",
        headers=auth_headers["admin"],
        json={
            "contexto": "Atendente reporta lentidão ao abrir ticket com muitos anexos.",
            "problema": "A tela trava por mais de 10 segundos quando há 20+ anexos.",
            "impacto": "Operação do suporte fica parada no horário de pico.",
            "evidencias": "Gravação de tela enviada pelo cliente interno.",
            "urgencia": "alta",
        },
    )
    assert criar.status_code == 200, criar.text
    sessao_id = criar.json()["id"]
    assert criar.json()["estado"] == "rascunho"

    analisar = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/analisar",
        headers=auth_headers["admin"],
    )
    assert analisar.status_code == 200, analisar.text
    body = analisar.json()
    assert body["estado"] == "analisado"
    assert body["analise"]["classificacao"] == "melhoria"


def test_pre_ticket_analisar_sem_ia_retorna_503(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.services.pre_ticket_ai.settings.PRE_TICKET_AI_ENABLED", False)
    monkeypatch.setattr("app.services.pre_ticket_ai.settings.OPENAI_API_KEY", None)
    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    r = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/analisar",
        headers=auth_headers["admin"],
    )
    assert r.status_code == 503


def test_pre_ticket_aprovar_exige_analise(client, auth_headers):
    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    r = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/aprovar",
        headers=auth_headers["admin"],
    )
    assert r.status_code == 400


def test_pre_ticket_aprovar_fluxo(client, auth_headers, monkeypatch):
    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    body = _aprovar_sessao(client, auth_headers["admin"], sessao_id, monkeypatch)
    assert body["estado"] == "aprovado"
    assert body["aprovado_por_nome"]


def test_pre_ticket_editar_rascunho(client, auth_headers, monkeypatch):
    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    _aprovar_sessao(client, auth_headers["admin"], sessao_id, monkeypatch)

    patch = client.patch(
        f"/v1/pre-ticket/sessoes/{sessao_id}/rascunho",
        headers=auth_headers["admin"],
        json={
            "rascunho_titulo": "Título editado pelo analista",
            "rascunho_corpo": "## Editado\nCorpo revisado.",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["rascunho_titulo"] == "Título editado pelo analista"


def test_pre_ticket_historico(client, auth_headers, monkeypatch):
    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    _aprovar_sessao(client, auth_headers["admin"], sessao_id, monkeypatch)
    r = client.get(
        f"/v1/pre-ticket/sessoes/{sessao_id}/historico",
        headers=auth_headers["admin"],
    )
    assert r.status_code == 200
    acoes = {item["acao"] for item in r.json()}
    assert "criar" in acoes
    assert "analisar" in acoes
    assert "aprovar" in acoes


def test_pre_ticket_publicar_github_mock(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.services.pre_ticket_github.github_configurado", lambda: True)
    monkeypatch.setattr("app.services.pre_ticket_github.settings.GITHUB_REPO_SUGESTOES", "org/repo")
    monkeypatch.setattr(
        "app.services.pre_ticket_github._post_issue",
        lambda _repo, _payload: {"number": 999, "html_url": "https://github.com/org/repo/issues/999"},
    )

    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    _aprovar_sessao(client, auth_headers["admin"], sessao_id, monkeypatch)

    pub = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/github",
        headers=auth_headers["admin"],
    )
    assert pub.status_code == 200, pub.text
    body = pub.json()
    assert body["estado"] == "publicado"
    assert body["github_issue_number"] == 999
    assert body["rascunho_publicado_titulo"]

    dup = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/github",
        headers=auth_headers["admin"],
    )
    assert dup.status_code == 200
    assert dup.json()["github_issue_number"] == 999


def test_pre_ticket_publicar_nao_admin(client, auth_headers, monkeypatch, db_session):
    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    _aprovar_sessao(client, auth_headers["admin"], sessao_id, monkeypatch)

    r = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/github",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 403
    denied = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "pre_ticket_sessao",
            AuditLog.entity_id == sessao_id,
            AuditLog.action == "acesso_negado",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert denied is not None
    assert denied.payload_json.get("acao") == "publicar"


def test_pre_ticket_analisar_nao_admin(client, auth_headers, db_session):
    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    r = client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/analisar",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 403
    denied = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "pre_ticket_sessao", AuditLog.action == "acesso_negado")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert denied is not None
    assert denied.payload_json.get("acao") == "analisar"


def test_pre_ticket_metricas_apos_analise(client, auth_headers, monkeypatch, db_session):
    from app.models.pre_ticket_analise_metrica import PreTicketAnaliseMetrica

    monkeypatch.setattr("app.services.pre_ticket_ai.settings.PRE_TICKET_AI_ENABLED", True)
    monkeypatch.setattr("app.services.pre_ticket_ai.settings.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.pre_ticket_ai._chamar_openai", _mock_openai_ok)

    sessao_id = _criar_sessao_minima(client, auth_headers["admin"])
    assert client.post(
        f"/v1/pre-ticket/sessoes/{sessao_id}/analisar",
        headers=auth_headers["admin"],
    ).status_code == 200

    count = db_session.query(PreTicketAnaliseMetrica).filter_by(sessao_id=sessao_id).count()
    assert count == 1

    m = client.get("/v1/pre-ticket/metricas", headers=auth_headers["admin"])
    assert m.status_code == 200
    body = m.json()
    assert body["uso"]["total_analises"] >= 1
    assert body["custo"]["total_usd"] >= 0
