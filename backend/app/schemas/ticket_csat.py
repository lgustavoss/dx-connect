from datetime import datetime

from pydantic import BaseModel, Field


class TicketCsatSubmitBody(BaseModel):
    nota: int = Field(..., ge=1, le=5)
    comentario: str | None = Field(None, max_length=2000)


class TicketCsatPublicRead(BaseModel):
    status: str
    protocolo: str | None = None
    assunto: str | None = None
    nota: int | None = None
    comentario: str | None = None
    respondida_em: datetime | None = None


class AvaliacaoResumoRead(BaseModel):
    media: float | None = None
    total: int = 0


class AtendenteAvaliacoesRead(BaseModel):
    geral: AvaliacaoResumoRead
    whatsapp: AvaliacaoResumoRead
    tickets: AvaliacaoResumoRead


class TicketAvaliacaoBrief(BaseModel):
    nota: int
    comentario: str | None = None
    respondida_em: datetime | None = None
    csat_pendente: bool = False


class TicketCsatDevLinkRead(BaseModel):
    link: str
    expires_at: datetime
