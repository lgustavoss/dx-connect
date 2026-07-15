from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversaDiretaCreate(BaseModel):
    atendente_id: int = Field(..., gt=0)


class ConversaGrupoCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=120)
    atendente_ids: list[int] = Field(..., min_length=1)


class GrupoParticipantesUpdate(BaseModel):
    adicionar: list[int] = Field(default_factory=list)
    remover: list[int] = Field(default_factory=list)
    promover_admin: list[int] = Field(default_factory=list)
    rebaixar_admin: list[int] = Field(default_factory=list)


class ParticipanteGrupoRead(BaseModel):
    atendente_id: int
    nome: str
    papel: Literal["admin", "membro"]


class MensagemInternaCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=8000)
    reply_to_message_id: int | None = Field(None, gt=0)


class MensagemInternaUpdate(BaseModel):
    corpo: str = Field(..., max_length=8000)


class ReacaoMensagemCreate(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=16)


class ReacaoMensagemRead(BaseModel):
    emoji: str
    count: int
    reagiu_eu: bool = False


class MensagemInternaRead(BaseModel):
    id: int
    conversa_id: int
    atendente_id: int | None
    atendente_nome: str | None = None
    corpo: str
    tipo_midia: Literal["texto", "imagem", "video", "audio", "documento"] = "texto"
    mimetype: str | None = None
    nome_arquivo: str | None = None
    tamanho_bytes: int | None = None
    midia_disponivel: bool = False
    status_entrega: Literal["enviada", "entregue", "lida"] | None = None
    apagada: bool = False
    editada: bool = False
    reacoes: list[ReacaoMensagemRead] = Field(default_factory=list)
    pode_editar: bool = False
    pode_apagar_para_todos: bool = False
    pode_apagar_para_mim: bool = False
    reply_to_message_id: int | None = None
    reply_preview: str | None = None
    reply_autor_nome: str | None = None
    created_at: datetime
    editada_em: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MensagensInternasPaginaRead(BaseModel):
    items: list[MensagemInternaRead]
    total: int
    tem_mais_antigas: bool


class ConversaRead(BaseModel):
    id: int
    tipo: Literal["direta", "setor", "grupo"]
    setor_id: int | None = None
    setor_nome: str | None = None
    titulo: str | None = None
    participantes: list[ParticipanteGrupoRead] | None = None
    sou_admin_grupo: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversaInboxRead(BaseModel):
    id: int
    tipo: Literal["direta", "setor", "grupo"]
    titulo: str
    setor_id: int | None = None
    ultima_mensagem_corpo: str | None = None
    ultima_mensagem_em: datetime | None = None
    nao_lidas_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
