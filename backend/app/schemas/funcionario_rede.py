from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from datetime import datetime


def _email_vazio_para_none(v: object) -> object:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    return v


def _telefone_normalizado(v: object) -> str | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    return digits or None


class FuncionarioRedeBase(BaseModel):
    nome: str
    email: EmailStr | None = None
    telefone: str | None = None
    tipo: str  # socio | supervisor | colaborador
    escopo_empresas: str = "selected"  # all | selected
    ativo: bool = True

    @field_validator("email", mode="before")
    @classmethod
    def email_opcional(cls, v: object) -> object:
        return _email_vazio_para_none(v)

    @field_validator("telefone", mode="before")
    @classmethod
    def telefone_opcional(cls, v: object) -> str | None:
        return _telefone_normalizado(v)


class FuncionarioRedeCreate(FuncionarioRedeBase):
    rede_id: int | None = None
    empresa_id: int | None = None  # legado colaborador (preferir empresa_ids)
    empresa_ids: list[int] = []  # obrigatório se escopo_empresas == selected
    # Portal do cliente (#300): senha inicial opcional
    senha_portal: str | None = None
    must_change_password: bool = True


class FuncionarioRedeUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    tipo: str | None = None
    escopo_empresas: str | None = None
    ativo: bool | None = None
    rede_id: int | None = None
    empresa_id: int | None = None
    empresa_ids: list[int] | None = None
    senha_portal: str | None = None
    must_change_password: bool | None = None
    notificar_email_portal: bool | None = None
    revogar_sessoes_portal: bool | None = None

    @field_validator("email", mode="before")
    @classmethod
    def email_opcional(cls, v: object) -> object:
        return _email_vazio_para_none(v)

    @field_validator("telefone", mode="before")
    @classmethod
    def telefone_opcional(cls, v: object) -> str | None:
        return _telefone_normalizado(v)


class FuncionarioRedeRead(FuncionarioRedeBase):
    id: int
    rede_id: int | None = None
    empresa_id: int | None = None
    empresa_ids: list[int] = []  # preenchido quando escopo_empresas == selected
    portal_habilitado: bool = False
    must_change_password: bool = False
    notificar_email_portal: bool = True
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
