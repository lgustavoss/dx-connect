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
