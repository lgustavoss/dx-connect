from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TipoNegocioBase(BaseModel):
    nome: str
    ativo: bool = True


class TipoNegocioCreate(TipoNegocioBase):
    pass


class TipoNegocioUpdate(BaseModel):
    nome: str | None = None
    ativo: bool | None = None


class TipoNegocioRead(TipoNegocioBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
