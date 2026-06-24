from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KbCategoryCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(None, max_length=80)
    ordem: int = Field(0, ge=0, le=32767)
    parent_id: int | None = None


class KbCategoryUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    slug: str | None = Field(None, max_length=80)
    ordem: int | None = Field(None, ge=0, le=32767)
    parent_id: int | None = None


class KbCategoryRead(BaseModel):
    id: int
    nome: str
    slug: str
    ordem: int
    parent_id: int | None
    artigos_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class KbArticleCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=120)
    category_id: int | None = None
    conteudo_markdown: str = ""


class KbArticleUpdate(BaseModel):
    titulo: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=120)
    category_id: int | None = None
    conteudo_markdown: str | None = None


class KbArticleRead(BaseModel):
    id: int
    titulo: str
    slug: str
    category_id: int | None
    category_nome: str | None = None
    status: str
    conteudo_markdown: str
    autor_atendente_id: int | None
    autor_nome: str | None = None
    published_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class KbArticleBrief(BaseModel):
    id: int
    titulo: str
    slug: str
    category_id: int | None
    category_nome: str | None = None
    status: str
    autor_nome: str | None = None
    published_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
