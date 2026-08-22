from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ImplantacaoTemplateItemIn(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str | None = Field(None, max_length=2000)
    ordem: int = Field(1, ge=1)
    obrigatorio: bool = True
    chave: str | None = Field(None, max_length=64)


class ImplantacaoTemplateItemRead(ImplantacaoTemplateItemIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ImplantacaoTemplateCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    setor_id: int | None = None
    ativo: bool = True
    itens: list[ImplantacaoTemplateItemIn] = Field(default_factory=list)


class ImplantacaoTemplateUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    setor_id: int | None = None
    ativo: bool | None = None
    itens: list[ImplantacaoTemplateItemIn] | None = None


class ImplantacaoTemplateRead(BaseModel):
    id: int
    nome: str
    versao: int
    setor_id: int | None = None
    setor_nome: str | None = None
    ativo: bool
    itens: list[ImplantacaoTemplateItemRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TicketChecklistItemPatch(BaseModel):
    concluido: bool | None = None
    observacao: str | None = Field(None, max_length=2000)


class TicketChecklistItemRead(BaseModel):
    id: int
    titulo: str
    descricao: str | None = None
    ordem: int
    obrigatorio: bool
    chave: str | None = None
    concluido: bool
    concluido_por_id: int | None = None
    concluido_por_nome: str | None = None
    concluido_em: datetime | None = None
    observacao: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketChecklistRead(BaseModel):
    aplicavel: bool
    ticket_id: int
    contrato_id: int | None = None
    negociacao_id: int | None = None
    empresa_id: int | None = None
    progresso_pct: int = 0
    itens_obrigatorios_pendentes: int = 0
    pdvs_ativos: int | None = None
    itens: list[TicketChecklistItemRead] = Field(default_factory=list)
