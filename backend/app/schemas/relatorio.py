from datetime import date, datetime

from pydantic import BaseModel, Field


class RelatorioTicketLinha(BaseModel):
    protocolo: str
    assunto: str
    status_nome: str
    prioridade: str
    rede_nome: str
    empresa_nome: str
    setor_nome: str
    aberto_em: datetime | None = None
    fechado_em: datetime | None = None
    responsavel_nome: str
    canal: str


class RelatorioTicketsResponse(BaseModel):
    de: date
    ate: date
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    itens: list[RelatorioTicketLinha]


class RelatorioChatLinha(BaseModel):
    protocolo: str
    cliente_nome: str | None = None
    wa_id: str
    estado: str
    estado_rotulo: str
    setor_nome: str
    atendente_nome: str
    empresa_nome: str
    aberto_em: datetime | None = None
    inicio_atendimento: datetime | None = None
    encerrado_em: datetime | None = None
    avaliacao_nota: int | None = None


class RelatorioChatsResponse(BaseModel):
    de: date
    ate: date
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    itens: list[RelatorioChatLinha]
