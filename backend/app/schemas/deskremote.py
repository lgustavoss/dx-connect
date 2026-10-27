from datetime import datetime

from pydantic import BaseModel, Field


class DeskremoteTokenCreate(BaseModel):
    acesso_id: int | None = None


class DeskremoteTokenCriado(BaseModel):
    url: str
    expira_em: datetime
    pdv_id: int
    acesso_id: int
    rotulo: str


class DeskremoteEnrollIn(BaseModel):
    token: str = Field(min_length=8, max_length=200)
    rustdesk_id: str | None = Field(default=None, max_length=64)


class DeskremoteServidor(BaseModel):
    servidor_id: str
    servidor_relay: str
    chave: str


class DeskremoteEnrollOut(BaseModel):
    dispositivo_token: str
    senha: str
    senha_versao: int
    rustdesk_id: str | None = None
    rotulo: str
    pdv_id: int
    acesso_id: int
    servidor: DeskremoteServidor


class DeskremoteConfirmarIdIn(BaseModel):
    rustdesk_id: str = Field(min_length=1, max_length=64)


class DeskremoteConfirmarIdOut(BaseModel):
    rustdesk_id: str
    rotulo: str
    pdv_id: int


class DeskremoteSyncOut(BaseModel):
    senha_versao: int
    senha: str | None = None
    rotulo: str
    rustdesk_id: str | None = None
    servidor: DeskremoteServidor
