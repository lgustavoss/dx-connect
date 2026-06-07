from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime


class FuncionarioRedeBase(BaseModel):
    nome: str
    email: EmailStr
    tipo: str  # socio | supervisor | colaborador
    escopo_empresas: str = "selected"  # all | selected
    ativo: bool = True


class FuncionarioRedeCreate(FuncionarioRedeBase):
    rede_id: int | None = None
    empresa_id: int | None = None  # legado colaborador (preferir empresa_ids)
    empresa_ids: list[int] = []  # obrigatório se escopo_empresas == selected


class FuncionarioRedeUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    tipo: str | None = None
    escopo_empresas: str | None = None
    ativo: bool | None = None
    rede_id: int | None = None
    empresa_id: int | None = None
    empresa_ids: list[int] | None = None


class FuncionarioRedeRead(FuncionarioRedeBase):
    id: int
    rede_id: int | None = None
    empresa_id: int | None = None
    empresa_ids: list[int] = []  # preenchido quando escopo_empresas == selected
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FuncionarioRedeComVinculo(FuncionarioRedeRead):
    """Funcionário com texto 'vinculado a' (para exibição na tela da rede)."""
    vinculado_a: str = ""


class EmpresaOpcaoRead(BaseModel):
    id: int
    nome: str


class RemetenteFuncionarioResolveRead(BaseModel):
    email: str
    requer_cadastro: bool
    conflito_multiplas_redes: bool = False
    funcionario_id: int | None = None
    rede_id: int | None = None
    empresa_id: int | None = None
    empresas_opcao: list[EmpresaOpcaoRead] = []
