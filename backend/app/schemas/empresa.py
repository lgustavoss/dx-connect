from pydantic import BaseModel, ConfigDict
from datetime import datetime


class EmpresaBase(BaseModel):
    rede_id: int
    tipo_negocio_id: int | None = None
    nome: str
    cnpj_cpf: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    inscricao_estadual: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    email: str | None = None
    telefone: str | None = None
    resp_legal_nome: str | None = None
    resp_legal_cpf: str | None = None
    resp_legal_rg: str | None = None
    resp_legal_orgao_emissor: str | None = None
    resp_legal_nacionalidade: str | None = None
    resp_legal_estado_civil: str | None = None
    resp_legal_cargo: str | None = None
    resp_legal_email: str | None = None
    resp_legal_telefone: str | None = None
    resp_legal_endereco: str | None = None
    resp_legal_numero: str | None = None
    resp_legal_complemento: str | None = None
    resp_legal_bairro: str | None = None
    resp_legal_cidade: str | None = None
    resp_legal_estado: str | None = None
    resp_legal_cep: str | None = None
    ativo: bool = True


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    rede_id: int | None = None
    tipo_negocio_id: int | None = None
    nome: str | None = None
    cnpj_cpf: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    inscricao_estadual: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    email: str | None = None
    telefone: str | None = None
    resp_legal_nome: str | None = None
    resp_legal_cpf: str | None = None
    resp_legal_rg: str | None = None
    resp_legal_orgao_emissor: str | None = None
    resp_legal_nacionalidade: str | None = None
    resp_legal_estado_civil: str | None = None
    resp_legal_cargo: str | None = None
    resp_legal_email: str | None = None
    resp_legal_telefone: str | None = None
    resp_legal_endereco: str | None = None
    resp_legal_numero: str | None = None
    resp_legal_complemento: str | None = None
    resp_legal_bairro: str | None = None
    resp_legal_cidade: str | None = None
    resp_legal_estado: str | None = None
    resp_legal_cep: str | None = None
    ativo: bool | None = None


class EmpresaRead(EmpresaBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RedeListaResumo(BaseModel):
    """Nome da rede para listagens com minimização de dados (não-admin)."""

    id: int
    nome: str

    model_config = ConfigDict(from_attributes=True)


class EmpresaListaResumo(BaseModel):
    """Lista paginada para atendentes: identificação + rede, sem CNPJ/endereço/PII."""

    id: int
    nome: str
    ativo: bool
    rede: RedeListaResumo

    model_config = ConfigDict(from_attributes=True)


class ConsultaCNPJResponse(BaseModel):
    """Resposta normalizada da consulta ReceitaWS para preenchimento do formulário."""
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None
    situacao: str | None = None
    endereco: str = ""
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    email: str | None = None
    telefone: str | None = None
    abertura: str | None = None
    natureza_juridica: str | None = None
    atividade_principal: str | None = None
