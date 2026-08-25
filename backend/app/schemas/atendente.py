from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import date, datetime


class AtendenteBase(BaseModel):
    email: EmailStr
    nome: str
    role: str = "atendente"  # admin | atendente | comercial | saas_ops
    ativo: bool = True
    usa_escala: bool = False
    escala_horas_trabalho: int | None = Field(default=None, ge=1, le=168)
    escala_horas_folga: int | None = Field(default=None, ge=1, le=720)
    escala_inicio_em: date | None = None
    horario_previsto_entrada: str | None = Field(default=None, max_length=5)
    horario_previsto_saida: str | None = Field(default=None, max_length=5)
    tolerancia_atraso_minutos: int = Field(default=0, ge=0, le=120)


class AtendenteCreate(AtendenteBase):
    senha: str
    setor_ids: list[int] = []  # atendente: pelo menos um setor; admin: pode vazio


class AtendenteUpdate(BaseModel):
    email: str | None = None
    nome: str | None = None
    senha: str | None = None
    role: str | None = None
    ativo: bool | None = None
    setor_ids: list[int] | None = None
    usa_escala: bool | None = None
    escala_horas_trabalho: int | None = Field(default=None, ge=1, le=168)
    escala_horas_folga: int | None = Field(default=None, ge=1, le=720)
    escala_inicio_em: date | None = None
    horario_previsto_entrada: str | None = Field(default=None, max_length=5)
    horario_previsto_saida: str | None = Field(default=None, max_length=5)
    tolerancia_atraso_minutos: int | None = Field(default=None, ge=0, le=120)


class AtendenteRead(AtendenteBase):
    """Resposta da API: e-mail vem do banco; não usar EmailStr (legado .test / TLD reservado quebra a listagem)."""

    id: int
    email: str  # type: ignore[assignment]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    setor_ids: list[int] = []
    e_financeiro: bool = False
    must_change_password: bool = False
    saas_setor_ids: list[int] = []
    saas_setor_nomes: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class AtendenteLogin(BaseModel):
    """Corpo do login: aceita qualquer string para não bloquear contas legadas no banco."""

    email: str
    senha: str


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    must_change_password: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TrocaSenhaPropria(BaseModel):
    senha_atual: str = Field(..., min_length=1)
    senha_nova: str = Field(..., min_length=8, max_length=128)
