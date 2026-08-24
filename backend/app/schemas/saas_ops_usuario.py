"""Utilizadores do painel SaaS (role saas_ops) — #883."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SaasOpsUsuarioRead(BaseModel):
    id: int
    nome: str
    email: str
    ativo: bool
    must_change_password: bool
    mcp_token_configurado: bool
    mcp_token_gerado_em: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SaasOpsUsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)


class SaasOpsUsuarioCriado(SaasOpsUsuarioRead):
    """Senha temporária só nesta resposta."""

    senha_temporaria: str


class SaasOpsUsuarioUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=255)
    ativo: bool | None = None


class SaasOpsUsuarioSenha(BaseModel):
    senha_temporaria: str
