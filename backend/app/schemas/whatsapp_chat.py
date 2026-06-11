from datetime import datetime

from pydantic import BaseModel, Field


class WhatsappMensagemRead(BaseModel):
    id: int
    chat_id: int
    direcao: str
    corpo: str
    tipo_midia: str | None = None
    mimetype: str | None = None
    midia_disponivel: bool = False
    evento_sistema: str | None = None
    wa_message_id: str | None = None
    quoted_wa_message_id: str | None = None
    quoted_corpo_preview: str | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class WhatsappChatRead(BaseModel):
    id: int
    protocolo: str
    wa_id: str
    cliente_nome: str | None = None
    estado: str
    setor_id: int | None = None
    setor_nome: str | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    created_at: datetime | None = None
    atendimento_inicio_at: datetime | None = None
    encerramento_at: datetime | None = None
    avaliacao_nota: int | None = None
    avaliacao_respondida_at: datetime | None = None
    avaliacao_solicitada: bool = False
    ticket_ids: list[int] = Field(default_factory=list)
    funcionario_rede_id: int | None = None
    funcionario_nome: str | None = None
    funcionario_email: str | None = None
    funcionario_tipo: str | None = None
    empresa_id: int | None = None
    empresa_nome: str | None = None

    model_config = {"from_attributes": True}


class WhatsappEmpresaOpcaoRead(BaseModel):
    id: int
    nome: str


class WhatsappEmpresaCatalogoRead(BaseModel):
    id: int
    nome: str
    rede_id: int


class WhatsappFuncionarioOpcaoRead(BaseModel):
    id: int
    nome: str
    email: str
    tipo: str
    empresas: list[WhatsappEmpresaOpcaoRead] = Field(default_factory=list)


class WhatsappRedeCatalogoRead(BaseModel):
    id: int
    nome: str


class WhatsappFuncionarioCatalogoRead(BaseModel):
    redes: list[WhatsappRedeCatalogoRead] = Field(default_factory=list)
    empresas: list[WhatsappEmpresaCatalogoRead] = Field(default_factory=list)


class WhatsappChatMensagemCreate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)
    quoted_wa_message_id: str | None = Field(
        None,
        max_length=128,
        description="Id WhatsApp (key.id) da mensagem a citar, já existente neste chat.",
    )


class WhatsappChatComentarioInternoCreate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)


class WhatsappVincularTicketBody(BaseModel):
    ticket_id: int


class WhatsappVincularFuncionarioBody(BaseModel):
    funcionario_rede_id: int
    empresa_id: int | None = Field(
        None,
        description="Obrigatório quando o funcionário está vinculado a mais de uma empresa.",
    )


class WhatsappCadastrarFuncionarioBody(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    rede_id: int
    tipo: str = Field(default="colaborador", description="colaborador | supervisor")
    escopo_empresas: str = Field(default="selected", description="all | selected")
    empresa_ids: list[int] = Field(default_factory=list)
    empresa_id: int | None = Field(
        None,
        description="Empresa exibida no chat quando o funcionário tem várias empresas.",
    )


class WhatsappAbrirTicketBody(BaseModel):
    empresa_id: int
    setor_id: int
    assunto: str = Field(..., min_length=1, max_length=500)
    descricao: str | None = None


class WhatsappTransferirChatBody(BaseModel):
    setor_id: int
    atendente_id: int | None = None


class WhatsappAvaliacaoRead(BaseModel):
    chat_id: int
    protocolo: str
    wa_id: str
    cliente_nome: str | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    setor_id: int | None = None
    setor_nome: str | None = None
    nota: int | None = None
    avaliacao_respondida_at: datetime | None = None
    encerramento_at: datetime | None = None
    sem_avaliacao: bool = False
