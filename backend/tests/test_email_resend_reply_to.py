import json
from unittest.mock import MagicMock, patch

from app.services.email_resend import enviar_via_resend
from app.services.system_email_config import TransactionalEmailConfig


def test_enviar_via_resend_inclui_reply_to():
    cfg = TransactionalEmailConfig(
        api_key="re_test",
        from_email="noreply@notify.example.com",
        from_name="DX Connect",
        reply_to="suporte@duplexsoft.com.br",
    )
    captured: dict = {}

    def fake_urlopen(req, timeout=30):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.read.return_value = b'{"id": "msg_abc"}'
        resp.__enter__ = lambda s: resp
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", fake_urlopen):
        mid = enviar_via_resend(
            cfg,
            to_addr="cliente@example.com",
            subject="Re: teste",
            body="Olá",
            in_reply_to="parent@mail.test",
        )

    assert captured["body"]["reply_to"] == ["suporte@duplexsoft.com.br"]
    assert mid == "msg_abc@resend.dx-connect.local"
