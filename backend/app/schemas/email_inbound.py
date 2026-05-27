from pydantic import BaseModel, Field


class EmailInboundWebhookResponse(BaseModel):
    """Resposta do webhook público de ingestão de e-mail → ticket."""

    ticket_id: int = Field(description="Identificador interno do ticket criado ou referido.")
    protocolo: str = Field(description="Protocolo visível ao cliente/atendente.")
    duplicate: bool = Field(description="True se este Message-ID já tinha sido ingerido (idempotência).")
    threaded: bool = Field(
        default=False,
        description="True se a mensagem foi anexada a um ticket ainda aberto (mesma thread).",
    )
    after_close_new_ticket: bool = Field(
        default=False,
        description="True se a thread apontava para um ticket já encerrado: foi criado um novo ticket de triagem.",
    )
    auto_reply_sent: bool = Field(
        default=False,
        description="True se foi enviado e-mail automático ao remetente (requer SMTP configurado).",
    )
