from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.schemas.setor_distribuicao import SetorDistribuicaoRead


class SetorBase(BaseModel):
    nome: str
    slug: str
    ativo: bool = True


class SetorCreate(SetorBase):
    pass


class SetorUpdate(BaseModel):
    nome: str | None = None
    slug: str | None = None
    ativo: bool | None = None


class SetorRead(SetorBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    distribuicao: SetorDistribuicaoRead | None = None

    model_config = ConfigDict(from_attributes=True)
