from pydantic import BaseModel, Field


class EmpresaSistemaRead(BaseModel):
    cnpj: str | None = None
    nome: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    logo_url: str | None = None


class EmpresaSistemaUpdate(BaseModel):
    cnpj: str | None = Field(default=None, description="CNPJ (imutável após o primeiro save)")
    nome: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
