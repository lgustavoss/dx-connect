from datetime import datetime

from pydantic import BaseModel, Field


class WhatsappMensagemRead(BaseModel):
    id: int
    chat_id: int
    direcao: str
    corpo: str
    wa_message_id: str | None = None
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
    atendente_id: int | None = None
    atendente_nome: str | None = None
    created_at: datetime | None = None
    atendimento_inicio_at: datetime | None = None
    encerramento_at: datetime | None = None
    ticket_ids: list[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WhatsappChatMensagemCreate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)


class WhatsappVincularTicketBody(BaseModel):
    ticket_id: int


class WhatsappAbrirTicketBody(BaseModel):
    empresa_id: int
    setor_id: int
    assunto: str = Field(..., min_length=1, max_length=500)
    descricao: str | None = None
