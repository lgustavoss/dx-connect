from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class TicketNaturezaBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50)
    ordem: int = 0
    ativo: bool = True


class TicketNaturezaCreate(TicketNaturezaBase):
    pass


class TicketNaturezaUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=100)
    slug: str | None = Field(None, min_length=1, max_length=50)
    ordem: int | None = None
    ativo: bool | None = None


class TicketNaturezaRead(TicketNaturezaBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketMotivoBase(BaseModel):
    natureza_id: int
    nome: str = Field(..., min_length=1, max_length=120)
    slug: str = Field(..., min_length=1, max_length=50)
    ordem: int = 0
    ativo: bool = True


class TicketMotivoCreate(TicketMotivoBase):
    pass


class TicketMotivoUpdate(BaseModel):
    natureza_id: int | None = None
    nome: str | None = Field(None, min_length=1, max_length=120)
    slug: str | None = Field(None, min_length=1, max_length=50)
    ordem: int | None = None
    ativo: bool | None = None


class TicketMotivoRead(TicketMotivoBase):
    id: int
    natureza_nome: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
