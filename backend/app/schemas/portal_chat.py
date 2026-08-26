from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PortalChatSessionCreate(BaseModel):
    visitante_nome: str = Field(..., min_length=1, max_length=120)
    visitante_email: str | None = Field(None, max_length=255)


class PortalChatMensagemCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=4000)


class PortalChatMensagemRead(BaseModel):
    id: int
    chat_id: int
    direcao: str
    corpo: str
    tipo_midia: str = "texto"
    mimetype: str | None = None
    midia_disponivel: bool = False
    atendente_id: int | None
    atendente_nome: str | None = None
    evento_sistema: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortalChatRead(BaseModel):
    id: int
    protocolo: str
    visitante_nome: str
    visitante_email: str | None
    estado: str
    setor_id: int | None
    setor_nome: str | None = None
    atendente_id: int | None
    atendente_nome: str | None = None
    created_at: datetime
    atendimento_inicio_at: datetime | None
    encerramento_at: datetime | None
    ultima_mensagem_preview: str | None = None
    nao_lidas_count: int = 0
    last_seen_at: datetime | None = None
    last_seen_mensagem_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PortalChatSessionRead(BaseModel):
    visitor_token: str
    chat: PortalChatRead
    mensagens: list[PortalChatMensagemRead] = Field(default_factory=list)


class PortalChatPublicSessionRead(BaseModel):
    protocolo: str
    estado: str
    visitante_nome: str
    mensagens: list[PortalChatMensagemRead] = Field(default_factory=list)


class PortalChatDemandaCreate(BaseModel):
    natureza_id: int
    motivo_id: int | None = None
    descricao_curta: str | None = Field(None, max_length=500)


class PortalChatDemandaUpdate(BaseModel):
    natureza_id: int | None = None
    motivo_id: int | None = None
    descricao_curta: str | None = Field(None, max_length=500)


class PortalChatDemandaRead(BaseModel):
    id: int
    chat_id: int
    natureza_id: int
    natureza_nome: str | None = None
    motivo_id: int | None = None
    motivo_nome: str | None = None
    desfecho: str
    ticket_id: int | None = None
    descricao_curta: str | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PortalTransferirChatBody(BaseModel):
    setor_id: int
    atendente_id: int | None = None
