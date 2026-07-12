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


class KbCategoryReorderItem(BaseModel):
    id: int = Field(..., ge=1)
    ordem: int = Field(..., ge=0, le=32767)


class KbCategoryReorder(BaseModel):
    items: list[KbCategoryReorderItem] = Field(..., min_length=1)


class KbCategoryRead(BaseModel):
    id: int
    nome: str
    slug: str
    ordem: int
    parent_id: int | None
    parent_nome: str | None = None
    artigos_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class KbArticleCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=120)
    category_id: int | None = None
    conteudo_markdown: str = ""
    interno_only: bool = False


class KbArticleUpdate(BaseModel):
    titulo: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=120)
    category_id: int | None = None
    conteudo_markdown: str | None = None
    interno_only: bool | None = None


class KbArticleRead(BaseModel):
    id: int
    titulo: str
    slug: str
    category_id: int | None
    category_nome: str | None = None
    status: str
    conteudo_markdown: str
    interno_only: bool
    autor_atendente_id: int | None
    autor_nome: str | None = None
    published_at: datetime | None
    archived_at: datetime | None
    feedback_util_count: int = 0
    feedback_nao_util_count: int = 0
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
    interno_only: bool = False
    autor_nome: str | None = None
    published_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class KbArticleVersionRead(BaseModel):
    id: int
    article_id: int
    titulo: str
    status: str
    autor_atendente_id: int | None
    autor_nome: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KbArticleVersionDetail(KbArticleVersionRead):
    conteudo_markdown: str


class KbImageUploadResponse(BaseModel):
    url: str
    filename: str


class KbArticleMotivoLinkItem(BaseModel):
    id: int | None = None
    motivo_id: int | None = Field(None, ge=1)
    natureza_id: int | None = Field(None, ge=1)
    ordem: int = Field(0, ge=0, le=32767)
    motivo_nome: str | None = None
    natureza_nome: str | None = None


class KbArticleMotivoLinksUpdate(BaseModel):
    links: list[KbArticleMotivoLinkItem] = Field(default_factory=list, max_length=20)


class KbSuggestionsQuery(BaseModel):
    motivo_id: int | None = Field(None, ge=1)
    natureza_id: int | None = Field(None, ge=1)


class KbArticleFeedbackBody(BaseModel):
    util: bool


class KbArticleFeedbackRead(BaseModel):
    util: bool
    ja_avaliado: bool
    feedback_util_count: int
    feedback_nao_util_count: int


class KbPublicBrandingRead(BaseModel):
    nome_exibicao: str
    portal_titulo: str = "Central de ajuda"
    logo_url: str | None = None
    texto_boas_vindas: str | None = None
    cor_primaria: str = "#0D9488"
    cor_header: str = "#0B2D4A"
    cor_texto_header: str = "#FFFFFF"
    cor_texto_corpo: str = "#0F172A"
    cor_fundo: str = "#F8FAFC"
    cor_link: str = "#0D9488"
    exibir_marca_deskrudder: bool = True
    feedback_habilitado: bool = True


class KbPortalSettingsRead(BaseModel):
    portal_titulo: str | None = None
    texto_boas_vindas: str | None = None
    cor_header: str = "#0B2D4A"
    cor_primaria: str = "#0D9488"
    cor_texto_header: str = "#FFFFFF"
    cor_texto_corpo: str = "#0F172A"
    cor_fundo: str = "#F8FAFC"
    cor_link: str | None = None
    exibir_marca_deskrudder: bool = True
    feedback_habilitado: bool = True
    public_url_preview: str | None = None


_HEX_COLOR = r"^#[0-9A-Fa-f]{6}$"


class KbPortalSettingsUpdate(BaseModel):
    portal_titulo: str | None = Field(None, max_length=120)
    texto_boas_vindas: str | None = Field(None, max_length=500)
    cor_header: str | None = Field(None, pattern=_HEX_COLOR)
    cor_primaria: str | None = Field(None, pattern=_HEX_COLOR)
    cor_texto_header: str | None = Field(None, pattern=_HEX_COLOR)
    cor_texto_corpo: str | None = Field(None, pattern=_HEX_COLOR)
    cor_fundo: str | None = Field(None, pattern=_HEX_COLOR)
    cor_link: str | None = Field(None, pattern=_HEX_COLOR)
    exibir_marca_deskrudder: bool | None = None
    feedback_habilitado: bool | None = None
