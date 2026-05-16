from unittest.mock import patch


def test_admin_pode_salvar_empresa_sistema_e_cnpj_imutavel(client, auth_headers):
    # GET vazio
    r0 = client.get("/v1/settings/empresa-sistema", headers=auth_headers["admin"])
    assert r0.status_code == 200
    assert r0.json()["cnpj"] is None

    # PUT define cnpj
    r1 = client.put(
        "/v1/settings/empresa-sistema",
        headers=auth_headers["admin"],
        json={"cnpj": "12.345.678/0001-00", "nome": "DX Connect"},
    )
    assert r1.status_code == 200
    assert r1.json()["cnpj"] == "12.345.678/0001-00"

    # PUT tenta alterar cnpj (deve falhar)
    r2 = client.put(
        "/v1/settings/empresa-sistema",
        headers=auth_headers["admin"],
        json={"cnpj": "11.111.111/0001-11"},
    )
    assert r2.status_code == 400


def test_email_settings_nao_expoe_segredos(client, auth_headers):
    r1 = client.get("/v1/settings/email", headers=auth_headers["admin"])
    assert r1.status_code == 200
    assert r1.json()["has_transactional_api_key"] is False

    r2 = client.put(
        "/v1/settings/email",
        headers=auth_headers["admin"],
        json={
            "transactional_api_key": "re_secret_key",
            "transactional_from_email": "onboarding@resend.dev",
            "transactional_from_name": "DX Connect",
        },
    )
    assert r2.status_code == 200
    j = r2.json()
    assert j["has_transactional_api_key"] is True
    assert j["transactional_from_email"] == "onboarding@resend.dev"
    assert j["transactional_from_name"] == "DX Connect"
    assert "transactional_api_key" not in j


def test_test_transactional_chama_envio_e_retorna_ok(client, auth_headers, monkeypatch):
    calls: list[tuple] = []

    def fake_enviar(db, **kwargs):
        calls.append((db, kwargs))
        return "<sent@dx.test>"

    monkeypatch.setattr("app.api.system_settings.enviar_mensagem_texto_sistema", fake_enviar)

    r1 = client.post("/v1/settings/email/test-transactional", headers=auth_headers["admin"])
    assert r1.status_code == 200
    assert r1.json()["ok"] is True
    assert len(calls) == 1
    assert calls[0][1]["to_addr"] == "admin@test.local"


def test_endpoints_sao_admin_only(client, auth_headers):
    r1 = client.get("/v1/settings/empresa-sistema", headers=auth_headers["a1"])
    assert r1.status_code == 403
    r2 = client.get("/v1/settings/email", headers=auth_headers["a1"])
    assert r2.status_code == 403
    r3 = client.post("/v1/settings/email/test-transactional", headers=auth_headers["a1"])
    assert r3.status_code == 403


def test_transactional_config_from_row_exige_api_key_e_remetente(db_session, monkeypatch):
    monkeypatch.setattr("app.services.system_email_config.app_settings.RESEND_API_KEY", "")

    from app.models.email_settings import EmailSettings
    from app.services.system_email_config import transactional_config_from_row

    assert transactional_config_from_row(None) is None

    r = EmailSettings(transactional_from_email="noreply@example.com")
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    assert transactional_config_from_row(r) is None

    r.transactional_api_key_enc = "enc"
    db_session.commit()
    with patch("app.services.system_email_config.decrypt_str", return_value="re_xxx"):
        cfg = transactional_config_from_row(r)
    assert cfg is not None
    assert cfg.api_key == "re_xxx"
    assert cfg.from_email == "noreply@example.com"
