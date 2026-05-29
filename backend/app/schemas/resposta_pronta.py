from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RespostaProntaBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    corpo: str = Field(..., min_length=1)
    setor_id: int | None = None
    ordem: int = 0
    ativo: bool = True


class RespostaProntaCreate(RespostaProntaBase):
    pass


class RespostaProntaUpdate(BaseModel):
    titulo: str | None = Field(None, min_length=1, max_length=200)
    corpo: str | None = Field(None, min_length=1)
    setor_id: int | None = None
    ordem: int | None = None
    ativo: bool | None = None


class RespostaProntaRead(RespostaProntaBase):
    id: int
    setor_nome: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
