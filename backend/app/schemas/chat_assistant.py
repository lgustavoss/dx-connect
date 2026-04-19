from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatAssistantMessage(BaseModel):
    role: Literal["customer", "agent", "internal"]
    content: str = Field(..., min_length=1, max_length=12000)
    created_at: datetime | None = None


class ChatAssistantTicketContext(BaseModel):
    protocolo: str
    assunto: str
    empresa_nome: str | None = None
    setor_nome: str | None = None
    status_nome: str | None = None


class ChatAssistantSuggestRequest(BaseModel):
    ticket: ChatAssistantTicketContext
    conversation: list[ChatAssistantMessage] = Field(default_factory=list)
    objective: str | None = Field(default=None, max_length=500)
    tone: Literal["acolhedor", "consultivo", "agil"] = "consultivo"


class ChatAssistantSuggestResponse(BaseModel):
    reply: str
    model: str
    provider: Literal["openai"]
