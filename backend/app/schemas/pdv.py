from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PdvCatalogoBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    ativo: bool = True
    ordem_exibicao: int = 0


class PdvRotuloCreate(PdvCatalogoBase):
    pass


class PdvRotuloUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    ativo: bool | None = None
    ordem_exibicao: int | None = None


class PdvRotuloRead(PdvCatalogoBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class PdvTipoAcessoRemotoCreate(PdvCatalogoBase):
    pass


class PdvTipoAcessoRemotoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    ativo: bool | None = None
    ordem_exibicao: int | None = None


class PdvTipoAcessoRemotoRead(PdvCatalogoBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class EmpresaPdvBase(BaseModel):
    codigo: str = Field(min_length=1, max_length=32)
    rotulo_id: int
    papel: str = Field(pattern=r"^(principal|auxiliar)$")
    usa_tef: bool = False
    tipo_acesso_remoto_id: int | None = None
    acesso_remoto_id: str | None = Field(default=None, max_length=255)
    observacoes: str | None = None
    ativo: bool = True


class EmpresaPdvCreate(EmpresaPdvBase):
    acesso_remoto_senha: str | None = Field(default=None, max_length=500)


class EmpresaPdvUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=32)
    rotulo_id: int | None = None
    papel: str | None = Field(default=None, pattern=r"^(principal|auxiliar)$")
    usa_tef: bool | None = None
    tipo_acesso_remoto_id: int | None = None
    acesso_remoto_id: str | None = Field(default=None, max_length=255)
    acesso_remoto_senha: str | None = Field(default=None, max_length=500)
    observacoes: str | None = None
    ativo: bool | None = None


class EmpresaPdvRead(EmpresaPdvBase):
    id: int
    empresa_id: int
    rotulo_nome: str | None = None
    tipo_acesso_remoto_nome: str | None = None
    tem_senha_remota: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class EmpresaPdvCredencialRead(BaseModel):
    acesso_remoto_senha: str
