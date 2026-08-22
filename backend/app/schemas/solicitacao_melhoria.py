from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TipoSolicitacao = Literal["sugestao", "problema"]
StatusSolicitacao = Literal[
    "aberta",
    "em_analise",
    "planejada",
    "em_desenvolvimento",
    "concluida",
    "nao_sera_desenvolvida",
]


class SolicitacaoMelhoriaCreate(BaseModel):
    tipo: TipoSolicitacao
    titulo: str = Field(..., min_length=3, max_length=200)
    descricao: str = Field(..., min_length=10, max_length=20000)
    versao_contexto: str | None = Field(None, max_length=64)
    anexo_ids: list[int] = Field(default_factory=list)


class SolicitacaoAnexoRead(BaseModel):
    id: int
    papel: str
    nome_original: str
    content_type: str | None
    tamanho_bytes: int
    url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SolicitacaoMelhoriaStatusUpdate(BaseModel):
    status: StatusSolicitacao
    motivo_nao_desenvolvimento: str | None = Field(None, max_length=4000)


class SolicitacaoComentarioCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=8000)
    publico_cliente: bool = True


class SolicitacaoHistoricoRead(BaseModel):
    id: int
    status_anterior: str | None
    status_novo: str
    status_novo_rotulo: str
    motivo: str | None
    mensagem_publica: str | None
    atendente_nome: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SolicitacaoComentarioRead(BaseModel):
    id: int
    corpo: str
    publico_cliente: bool
    origem: str
    autor_nome: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SolicitacaoMelhoriaRead(BaseModel):
    id: int
    protocolo: str | None = None
    organizacao_id: int
    autor_atendente_id: int | None
    autor_nome: str | None
    tipo: str
    titulo: str
    descricao: str
    status: str
    status_rotulo: str
    motivo_nao_desenvolvimento: str | None
    versao_contexto: str | None
    mensagem_status: str
    created_at: datetime
    updated_at: datetime | None
    # Campos GitHub só em respostas admin (preenchidos no serializer interno)
    github_repo: str | None = None
    github_issue_number: int | None = None
    github_issue_url: str | None = None
    github_last_error: str | None = None
    historico: list[SolicitacaoHistoricoRead] = []
    comentarios: list[SolicitacaoComentarioRead] = []
    anexos: list[SolicitacaoAnexoRead] = []

    model_config = {"from_attributes": True}


class SolicitacaoMelhoriaListaItem(BaseModel):
    id: int
    protocolo: str | None = None
    tipo: str
    titulo: str
    status: str
    status_rotulo: str
    autor_nome: str | None
    organizacao_id: int
    created_at: datetime
    updated_at: datetime | None
    github_issue_number: int | None = None

    model_config = {"from_attributes": True}
