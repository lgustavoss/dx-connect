from pydantic import BaseModel, ConfigDict, Field


class PermissaoCatalogoItem(BaseModel):
    modulo: str
    codigo: str
    nome: str
    descricao: str
    pacote: str | None = None


class PermissaoGrupoRead(BaseModel):
    id: int
    nome: str
    slug: str
    sistema: bool
    permissoes: list[str]
    membros: int

    model_config = ConfigDict(from_attributes=True)


class PermissaoGrupoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    permissoes: list[str] = Field(min_length=1)


class PermissaoGrupoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    permissoes: list[str] | None = None


class PermissaoGrupoMembro(BaseModel):
    id: int
    nome: str
    email: str
    ativo: bool


class PermissaoGrupoMembroCreate(BaseModel):
    atendente_id: int
