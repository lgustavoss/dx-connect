from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WhatsAppMessageRead(BaseModel):
    id: int
    conversation_id: int
    ticket_id: int | None = None
    wa_message_id: str | None = None
    direction: str
    sender_phone: str | None = None
    recipient_phone: str | None = None
    message_type: str
    body: str | None = None
    media_url: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    status: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WhatsAppConversationRead(BaseModel):
    id: int
    wa_id: str
    profile_name: str | None = None
    phone_number: str
    status: str
    ai_enabled: bool
    ai_mode: str
    last_message_at: datetime | None = None
    linked_ticket_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    linked_ticket_protocolo: str | None = None
    linked_ticket_assunto: str | None = None
    linked_ticket_empresa_nome: str | None = None
    messages: list[WhatsAppMessageRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class WhatsAppConversationUpdate(BaseModel):
    linked_ticket_id: int | None = None
    ai_enabled: bool | None = None
    ai_mode: Literal["assist", "copilot"] | None = None
    status: Literal["open", "pending", "resolved"] | None = None
    profile_name: str | None = Field(default=None, max_length=255)


class WhatsAppOutboundMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4096)
    auto_generated: bool = False


class WhatsAppAiAssistRequest(BaseModel):
    objective: str | None = Field(default=None, max_length=500)
    auto_send: bool = False


class WhatsAppAiAssistResponse(BaseModel):
    reply: str
    sent: bool = False
    source: Literal["openai", "fallback"]
