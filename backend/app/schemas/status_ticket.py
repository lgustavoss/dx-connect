from pydantic import BaseModel, ConfigDict
from datetime import datetime


class StatusTicketBase(BaseModel):
    nome: str
    slug: str
    ordem: int = 0
    ativo: bool = True


class StatusTicketCreate(StatusTicketBase):
    pass


class StatusTicketUpdate(BaseModel):
    nome: str | None = None
    slug: str | None = None
    ordem: int | None = None
    ativo: bool | None = None


class StatusTicketRead(StatusTicketBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
