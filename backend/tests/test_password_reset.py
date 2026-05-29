"""Redefinição de senha por e-mail (#105)."""

from datetime import datetime, timedelta, timezone

from app.core.security import hash_senha, verificar_senha
from app.models.password_reset_token import PasswordResetToken
from app.services.password_reset import (
    MSG_SOLICITACAO_OK,
    _hash_token,
    build_reset_link,
    redefinir_senha_com_token,
    solicitar_redefinicao,
)


def test_solicitar_resposta_generica_sem_vazar_email(client, seed_base):
    r1 = client.post("/v1/auth/solicitar-redefinicao-senha", json={"email": seed_base["admin"].email})
    r2 = client.post("/v1/auth/solicitar-redefinicao-senha", json={"email": "naoexiste@example.com"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["detail"] == MSG_SOLICITACAO_OK
    assert r2.json()["detail"] == MSG_SOLICITACAO_OK


def test_fluxo_completo_reset_senha(client, db_session, seed_base, monkeypatch):
    sent: list[dict] = []

    def fake_enviar(db, *, to_addr, subject, body, in_reply_to=None, references=None):
        sent.append({"to": to_addr, "subject": subject, "body": body})
        return "msg-id"

    monkeypatch.setattr("app.services.password_reset.enviar_mensagem_texto_sistema", fake_enviar)

    admin = seed_base["admin"]
    res = client.post("/v1/auth/solicitar-redefinicao-senha", json={"email": admin.email})
    assert res.status_code == 200
    assert len(sent) == 1

    row = db_session.query(PasswordResetToken).filter(PasswordResetToken.atendente_id == admin.id).first()
    assert row is not None

    raw = "token-teste-reset-12345678901234567890123456789012"
    row.token_hash = _hash_token(raw)
    db_session.commit()

    api_res = client.post(
        "/v1/auth/redefinir-senha",
        json={"token": raw, "senha_nova": "novaSenhaSegura1"},
    )
    assert api_res.status_code == 200, api_res.text

    db_session.refresh(admin)
    assert verificar_senha("novaSenhaSegura1", admin.senha_hash)
    assert admin.must_change_password is False

    login_res = client.post("/v1/auth/login", json={"email": admin.email, "senha": "novaSenhaSegura1"})
    assert login_res.status_code == 200


def test_token_expirado_rejeitado(db_session, seed_base):
    admin = seed_base["admin"]
    raw = "token-expirado-teste-abcdefghijklmnopqrstuvwxyz"
    row = PasswordResetToken(
        atendente_id=admin.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(row)
    db_session.commit()

    import pytest

    with pytest.raises(ValueError, match="inválido|expirado"):
        redefinir_senha_com_token(db_session, raw, "outraSenha123")


def test_build_reset_link_dev():
    link = build_reset_link("abc")
    assert link.startswith("http://localhost:5173/redefinir-senha?token=abc")
