from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversaDiretaCreate(BaseModel):
    atendente_id: int = Field(..., gt=0)


class MensagemInternaCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=8000)


class MensagemInternaRead(BaseModel):
    id: int
    conversa_id: int
    atendente_id: int | None
    atendente_nome: str | None = None
    corpo: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversaRead(BaseModel):
    id: int
    tipo: Literal["direta", "setor"]
    setor_id: int | None = None
    setor_nome: str | None = None
    titulo: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversaInboxRead(BaseModel):
    id: int
    tipo: Literal["direta", "setor"]
    titulo: str
    setor_id: int | None = None
    ultima_mensagem_corpo: str | None = None
    ultima_mensagem_em: datetime | None = None
    nao_lidas_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
