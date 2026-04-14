from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NotificacaoResumo(BaseModel):
    sem_responsavel_count: int = Field(ge=0)
    nao_lidas_count: int = Field(
        ge=0,
        description="Quantidade de tickets com mensagens não lidas (com responsável)",
    )
    total_pendencias: int = Field(ge=0, description="Soma usada no badge (sem duplicar fila vs. não lidas)")


class NotificacaoItem(BaseModel):
    tipo: Literal["fila_sem_responsavel", "mensagens_nao_lidas"]
    ticket_id: int | None = None
    titulo: str
    descricao: str
    count: int = Field(ge=0)
    href: str
    created_at: datetime | None = None


class NotificacaoItensResponse(BaseModel):
    itens: list[NotificacaoItem]
