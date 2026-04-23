from pydantic import BaseModel, ConfigDict
from datetime import datetime


class RedeBase(BaseModel):
    nome: str
    login_retaguarda: str | None = None
    ativo: bool = True


class RedeCreate(RedeBase):
    pass


class RedeUpdate(BaseModel):
    nome: str | None = None
    login_retaguarda: str | None = None
    ativo: bool | None = None


class RedeRead(RedeBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
