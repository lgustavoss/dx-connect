from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NotificacaoResumo(BaseModel):
    sem_responsavel_count: int = Field(ge=0)
    nao_lidas_count: int = Field(
        ge=0,
        description="Quantidade de tickets com mensagens não lidas (com responsável)",
    )
    wpp_fila_count: int = Field(ge=0, description="Quantidade de chats WhatsApp aguardando atendimento")
    wpp_respostas_count: int = Field(
        ge=0,
        description="Quantidade de chats WhatsApp em atendimento do usuário com resposta do cliente pendente",
    )
    portal_fila_count: int = Field(
        ge=0,
        default=0,
        description="Quantidade de chats do portal aguardando atendimento",
    )
    portal_respostas_count: int = Field(
        ge=0,
        default=0,
        description="Quantidade de chats do portal em atendimento com resposta do visitante pendente",
    )
    chat_interno_nao_lidas_count: int = Field(
        ge=0,
        default=0,
        description="Quantidade de conversas internas com mensagens não lidas",
    )
    total_pendencias: int = Field(ge=0, description="Soma usada no badge (sem duplicar fila vs. não lidas)")


class NotificacaoItem(BaseModel):
    tipo: Literal[
        "fila_sem_responsavel",
        "mensagens_nao_lidas",
        "wpp_chats_na_fila",
        "wpp_chats_com_resposta",
        "chat_interno",
    ]
    ticket_id: int | None = None
    conversa_id: int | None = None
    titulo: str
    descricao: str
    count: int = Field(ge=0)
    href: str
    created_at: datetime | None = None


class NotificacaoItensResponse(BaseModel):
    itens: list[NotificacaoItem]
