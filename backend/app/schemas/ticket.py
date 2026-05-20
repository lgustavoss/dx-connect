from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class TicketBase(BaseModel):
    empresa_id: int
    setor_id: int
    assunto: str
    descricao: str | None = None
    aberto_por_id: int | None = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    """Assunto e descrição não são editáveis aqui — use mensagens no ticket."""

    empresa_id: int | None = None
    setor_id: int | None = None
    status_id: int | None = None
    atendente_id: int | None = None


class EmpresaVinculoSugerida(BaseModel):
    id: int
    nome: str


class TicketTriagemInbound(BaseModel):
    requer_cadastro_funcionario: bool = False
    remetente_email: str | None = None
    conflito_multiplas_redes: bool = False
    empresas_vinculo_sugeridas: list[EmpresaVinculoSugerida] = []


class TicketRead(BaseModel):
    id: int
    protocolo: str
    empresa_id: int | None = None
    setor_id: int
    status_id: int
    atendente_id: int | None = None
    aberto_por_id: int | None = None
    assunto: str
    descricao: str | None = None
    fechado_em: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # opcional: nomes para exibição
    rede_id: int | None = None
    empresa_nome: str | None = None
    rede_nome: str | None = None
    setor_nome: str | None = None
    status_nome: str | None = None
    atendente_nome: str | None = None
    triagem_inbound: TicketTriagemInbound | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketMensagemCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=20000)
    tipo: Literal["publico", "interno"]
    notificar_cliente_por_email: bool = Field(
        default=False,
        description="Se true e tipo=publico, envia e-mail SMTP ao último remetente do ticket (ingestão) e regista Message-ID (#165).",
    )


class TicketMensagemRead(BaseModel):
    id: int
    ticket_id: int
    atendente_id: int | None = None
    atendente_nome: str | None = None
    autor_externo: str | None = None
    tipo: str
    corpo: str
    created_at: datetime
    cliente_notificado_por_email: bool = False

    model_config = ConfigDict(from_attributes=True)


class TicketHistoricoRead(BaseModel):
    id: int
    ticket_id: int
    atendente_id: int | None = None
    atendente_nome: str | None = None
    campo: str
    valor_antigo: str | None = None
    valor_novo: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
