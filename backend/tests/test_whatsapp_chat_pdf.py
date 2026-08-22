"""Exportação PDF de conversa WhatsApp (#837)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem


def test_exportar_chat_pdf_ok_e_403(client, seed_base, auth_headers, monkeypatch, db_session):
    captured: list[str] = []

    def _fake(html: str) -> bytes:
        captured.append(html)
        return b"%PDF-1.4\nfake-chat-pdf"

    monkeypatch.setattr("app.services.comercial_proposta.html_para_pdf", _fake)

    chat = WhatsappChat(
        protocolo="PDF-TEST-837",
        wa_id="5511999008371",
        cliente_nome="Cliente Export",
        estado="em_atendimento",
        setor_id=seed_base["setor1"].id,
        atendente_id=seed_base["a1"].id,
        atendimento_inicio_at=datetime.now(timezone.utc),
    )
    db_session.add(chat)
    db_session.flush()
    db_session.add_all(
        [
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="inbound",
                corpo="Preciso de ajuda com o PDV",
                tipo_midia="texto",
            ),
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="outbound",
                corpo="Claro, vamos verificar.",
                tipo_midia="texto",
                atendente_id=seed_base["a1"].id,
            ),
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="outbound",
                corpo="",
                tipo_midia="imagem",
                midia_nome_original="foto.jpg",
                atendente_id=seed_base["a1"].id,
            ),
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="outbound",
                corpo="Transferido para Financeiro",
                evento_sistema="transferencia",
            ),
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="outbound",
                corpo="Nota interna secreta",
                evento_sistema="comentario_interno",
                atendente_id=seed_base["a1"].id,
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(chat)

    ok = client.get(f"/v1/whatsapp/chats/{chat.id}/pdf", headers=auth_headers["a1"])
    assert ok.status_code == 200
    assert ok.headers.get("content-type", "").startswith("application/pdf")
    cd = ok.headers.get("content-disposition") or ""
    assert "attachment" in cd
    assert "chat-PDF-TEST-837.pdf" in cd or "PDF-TEST-837" in cd
    assert ok.content.startswith(b"%PDF")
    assert captured
    assert "Preciso de ajuda" in captured[0]
    assert "Claro, vamos verificar" in captured[0]
    assert "[Imagem]" in captured[0]
    assert "transferido" in captured[0].lower() or "Transfer" in captured[0]
    assert "Nota interna secreta" not in captured[0]

    denied = client.get(f"/v1/whatsapp/chats/{chat.id}/pdf", headers=auth_headers["a2"])
    assert denied.status_code == 403

    admin_ok = client.get(f"/v1/whatsapp/chats/{chat.id}/pdf", headers=auth_headers["admin"])
    assert admin_ok.status_code == 200
