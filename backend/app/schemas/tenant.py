from pydantic import BaseModel, Field


class TenantRead(BaseModel):
    id: int
    nome: str
    ativo: bool
    app_host: str | None = None

    model_config = {"from_attributes": True}


class TenantInboundAddressRead(BaseModel):
    id: int
    tenant_id: int
    local_part: str
    full_address: str
    label: str | None = None
    setor_id: int
    setor_nome: str | None = None
    default_empresa_id: int | None = None
    ativo: bool

    model_config = {"from_attributes": True}


class TenantInboundAddressCreate(BaseModel):
    local_part: str = Field(..., min_length=2, max_length=128)
    label: str | None = Field(default=None, max_length=100)
    setor_id: int
    default_empresa_id: int | None = None


class TenantInboundAddressUpdate(BaseModel):
    label: str | None = None
    setor_id: int | None = None
    default_empresa_id: int | None = None
    ativo: bool | None = None
