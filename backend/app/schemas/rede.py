from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime


def _texto_opcional(v: object) -> object:
    if isinstance(v, str):
        s = v.strip()
        return s or None
    return v


class RedeBase(BaseModel):
    nome: str
    login_retaguarda: str | None = None
    versao_retaguarda: str | None = Field(default=None, max_length=80)
    ativo: bool = True

    @field_validator("versao_retaguarda", mode="before")
    @classmethod
    def _texto_vazio(cls, v: object) -> object:
        return _texto_opcional(v)


class RedeCreate(RedeBase):
    pass


class RedeUpdate(BaseModel):
    nome: str | None = None
    login_retaguarda: str | None = None
    versao_retaguarda: str | None = Field(default=None, max_length=80)
    ativo: bool | None = None

    @field_validator("versao_retaguarda", mode="before")
    @classmethod
    def _texto_vazio(cls, v: object) -> object:
        return _texto_opcional(v)


class RedeRead(RedeBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
