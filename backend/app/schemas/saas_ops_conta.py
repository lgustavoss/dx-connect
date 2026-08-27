"""Schemas — conta do ops no painel SaaS."""

from pydantic import BaseModel, ConfigDict, Field


class SaasOpsContaPerfilUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=255)
    email: str | None = Field(None, min_length=3, max_length=255)


class SaasOpsContaPerfilRead(BaseModel):
    """Resposta do PATCH /saas/me. Tokens só vêm quando o e-mail muda (JWT usa o e-mail no sub)."""

    id: int
    nome: str
    email: str
    access_token: str | None = None
    refresh_token: str | None = None

    model_config = ConfigDict(from_attributes=True)
