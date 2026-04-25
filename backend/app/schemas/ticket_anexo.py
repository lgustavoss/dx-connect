from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TicketAnexoRead(BaseModel):
    id: int
    ticket_id: int
    mensagem_id: int | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    visibilidade: Literal["publico", "interno"]
    nome_original: str
    content_type: str | None = None
    tamanho_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketAnexoCreateResponse(BaseModel):
    anexo: TicketAnexoRead
    # URL relativa do download (para o frontend usar quando existir)
    download_url: str = Field(..., examples=["/v1/tickets/123/anexos/456/download"])

