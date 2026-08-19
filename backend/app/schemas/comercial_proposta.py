"""Schemas da proposta comercial (#323 / #345–#347)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PropostaTemplateCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    conteudo_html: str = Field(..., min_length=1)
    vigencia_inicio: datetime | None = None
    ativo: bool = True


class PropostaTemplateUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    conteudo_html: str | None = Field(None, min_length=1)
    vigencia_inicio: datetime | None = None
    ativo: bool | None = None


class PropostaTemplateRead(BaseModel):
    id: int
    nome: str
    versao: int
    conteudo_html: str
    vigencia_inicio: datetime | None = None
    ativo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PropostaTemplatePreviewIn(BaseModel):
    conteudo_html: str = Field(..., min_length=1)


class PropostaTemplatePreviewOut(BaseModel):
    html: str


class PropostaGerarIn(BaseModel):
    negociacao_id: int
    template_id: int | None = None
    linha_ids: list[int] | None = None
    condicoes: str | None = Field(None, max_length=8000)


class PropostaMarcarEnviadaIn(BaseModel):
    canal: str
    enviado_em: datetime | None = None
    avancar_funil: bool = False

    @field_validator("canal")
    @classmethod
    def _canal(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if s not in {"email", "impresso", "outro"}:
            raise ValueError("Canal deve ser email, impresso ou outro.")
        return s


class PropostaRead(BaseModel):
    id: int
    negociacao_id: int
    template_id: int
    template_nome: str | None = None
    template_versao: int | None = None
    gerado_por_id: int
    status: str
    conteudo_html_snapshot: str
    conteudo_hash: str
    linha_ids: list[int]
    canal: str | None = None
    enviado_em: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
