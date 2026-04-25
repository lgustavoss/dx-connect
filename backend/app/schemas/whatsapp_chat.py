from datetime import datetime

from pydantic import BaseModel, Field


class WhatsappMensagemRead(BaseModel):
    id: int
    chat_id: int
    direcao: str
    corpo: str
    tipo_midia: str | None = None
    mimetype: str | None = None
    midia_disponivel: bool = False
    evento_sistema: str | None = None
    wa_message_id: str | None = None
    quoted_wa_message_id: str | None = None
    quoted_corpo_preview: str | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class WhatsappChatRead(BaseModel):
    id: int
    protocolo: str
    wa_id: str
    cliente_nome: str | None = None
    estado: str
    setor_id: int | None = None
    setor_nome: str | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    created_at: datetime | None = None
    atendimento_inicio_at: datetime | None = None
    encerramento_at: datetime | None = None
    ticket_ids: list[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WhatsappChatMensagemCreate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)
    quoted_wa_message_id: str | None = Field(
        None,
        max_length=128,
        description="Id WhatsApp (key.id) da mensagem a citar, já existente neste chat.",
    )


class WhatsappChatComentarioInternoCreate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)


class WhatsappVincularTicketBody(BaseModel):
    ticket_id: int


class WhatsappAbrirTicketBody(BaseModel):
    empresa_id: int
    setor_id: int
    assunto: str = Field(..., min_length=1, max_length=500)
    descricao: str | None = None


class WhatsappTransferirChatBody(BaseModel):
    setor_id: int
    atendente_id: int | None = None
