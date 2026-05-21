from app.services.email_body_sanitize import sanitize_inbound_email_body


def test_remove_legacy_prefix_and_quote_pt():
    corpo = (
        "Mensagem recebida por e-mail.\n\n"
        "Remetente: Luis Gustavo <gustavo@gmail.com>\n"
        "Message-ID: abc@mail.gmail.com\n\n"
        "Teste recebido.\n\n"
        "att. Luis Gustavo\n\n"
        "Em dom., 17 de mai. de 2026 às 14:23, DX Connect <noreply@notify.duplexsoft.com.br> escreveu:\n"
        "> testando resposta por email\n"
        ">\n"
    )
    out = sanitize_inbound_email_body(corpo)
    assert "Remetente:" not in out
    assert "Message-ID" not in out
    assert "Mensagem recebida" not in out
    assert "Teste recebido." in out
    assert "att. Luis Gustavo" in out
    assert "escreveu:" not in out
    assert "testando resposta" not in out


def test_message_id_with_space():
    corpo = "Message ID: foo@bar\n\nOlá"
    assert sanitize_inbound_email_body(corpo) == "Olá"


def test_resend_fallback_placeholder():
    corpo = "(Mensagem recebida por e-mail; corpo não obtido da API Resend no momento do webhook.)"
    assert sanitize_inbound_email_body(corpo) == "(sem conteúdo)"
