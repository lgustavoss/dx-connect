import imaplib
import smtplib


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
    assert r1.json()["has_smtp_password"] is False
    assert r1.json()["has_imap_password"] is False

    r2 = client.put(
        "/v1/settings/email",
        headers=auth_headers["admin"],
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "user",
            "smtp_password": "secret",
            "imap_host": "imap.example.com",
            "imap_port": 993,
            "imap_user": "user",
            "imap_password": "secret2",
            "imap_use_ssl": True,
            "imap_folder": "INBOX",
        },
    )
    assert r2.status_code == 200
    j = r2.json()
    assert j["has_smtp_password"] is True
    assert j["has_imap_password"] is True
    assert "smtp_password" not in j
    assert "imap_password" not in j


def test_test_smtp_e_imap_usam_config_e_retornam_ok(client, auth_headers, monkeypatch):
    class DummySMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            return None

        def starttls(self):
            return None

        def login(self, user, password):
            assert user == "user"
            assert password == "secret"
            return None

    class DummyIMAP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def login(self, user, password):
            assert user == "user"
            assert password == "secret2"
            return "OK"

        def select(self, folder, readonly=True):
            assert folder == "INBOX"
            return ("OK", [b"0"])

        def logout(self):
            return ("BYE", [b""])

    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)
    monkeypatch.setattr(imaplib, "IMAP4_SSL", DummyIMAP)

    # configura
    r0 = client.put(
        "/v1/settings/email",
        headers=auth_headers["admin"],
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "user",
            "smtp_password": "secret",
            "smtp_use_starttls": True,
            "imap_host": "imap.example.com",
            "imap_port": 993,
            "imap_user": "user",
            "imap_password": "secret2",
            "imap_use_ssl": True,
            "imap_folder": "INBOX",
        },
    )
    assert r0.status_code == 200

    r1 = client.post("/v1/settings/email/test-smtp", headers=auth_headers["admin"])
    assert r1.status_code == 200
    assert r1.json()["ok"] is True

    r2 = client.post("/v1/settings/email/test-imap", headers=auth_headers["admin"])
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_endpoints_sao_admin_only(client, auth_headers):
    r1 = client.get("/v1/settings/empresa-sistema", headers=auth_headers["a1"])
    assert r1.status_code == 403
    r2 = client.get("/v1/settings/email", headers=auth_headers["a1"])
    assert r2.status_code == 403
    r3 = client.post("/v1/settings/email/test-smtp", headers=auth_headers["a1"])
    assert r3.status_code == 403


def test_smtp_runtime_from_row_exige_host_e_porta_validos(db_session):
    from app.models.email_settings import EmailSettings
    from app.services.system_email_config import smtp_runtime_from_row

    assert smtp_runtime_from_row(None) is None
    r = EmailSettings(smtp_host="", smtp_port=587)
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    assert smtp_runtime_from_row(r) is None

    r.smtp_host = "smtp.example.com"
    r.smtp_port = 0
    db_session.commit()
    assert smtp_runtime_from_row(r) is None

    r.smtp_port = 587
    db_session.commit()
    cfg = smtp_runtime_from_row(r)
    assert cfg is not None
    assert cfg.host == "smtp.example.com"
    assert cfg.port == 587
    assert cfg.password is None


def test_imap_runtime_from_row_exige_credenciais(db_session):
    from app.models.email_settings import EmailSettings
    from app.services.system_email_config import imap_runtime_from_row

    r = EmailSettings(imap_host="imap.example.com", imap_port=993, imap_user="u", imap_use_ssl=True)
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    assert imap_runtime_from_row(r) is None

    r.imap_password_enc = "dummy"
    db_session.commit()
    from unittest.mock import patch

    with patch("app.services.system_email_config.decrypt_str", return_value="secret"):
        cfg = imap_runtime_from_row(r)
    assert cfg is not None
    assert cfg.user == "u"
    assert cfg.password == "secret"
    assert cfg.folder == "INBOX"

