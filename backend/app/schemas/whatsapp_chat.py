from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WhatsappReacaoRead(BaseModel):
    emoji: str
    count: int
    reagiu_eu: bool = False
    atendente_ids: list[int] = Field(default_factory=list)
    tem_cliente: bool = False


class WhatsappReacaoCreate(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=16)


class WhatsappMensagemUpdate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)


class WhatsappMensagemRead(BaseModel):
    id: int
    chat_id: int
    direcao: str
    corpo: str
    tipo_midia: str | None = None
    mimetype: str | None = None
    midia_disponivel: bool = False
    midia_nome_original: str | None = None
    evento_sistema: str | None = None
    wa_message_id: str | None = None
    quoted_wa_message_id: str | None = None
    quoted_corpo_preview: str | None = None
    is_forwarded: bool = False
    forwarding_score: int | None = None
    atendente_id: int | None = None
    atendente_nome: str | None = None
    status_entrega: str | None = None
    created_at: datetime | None = None
    reacoes: list[WhatsappReacaoRead] = Field(default_factory=list)
    editada: bool = False
    editada_em: datetime | None = None
    apagada: bool = False
    pode_editar: bool = False
    pode_apagar_para_todos: bool = False

    model_config = {"from_attributes": True}


class WhatsappEmpresaOpcaoRead(BaseModel):
    id: int
    nome: str


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
    # Empresas do funcionário vinculado — útil quando falta empresa_id de contexto (#592).
    empresas_opcoes: list[WhatsappEmpresaOpcaoRead] = Field(default_factory=list)
    inatividade_pausada: bool = False
    inatividade_retomada_em: datetime | None = None
    classificacao_demanda_pendente: bool = False
    foto_perfil_url: str | None = None
    foto_perfil_atualizada_em: datetime | None = None
    # Não lidas do atendente atual (#951 / #S202608-0004)
    nao_lidas_count: int = 0
    last_seen_at: datetime | None = None
    last_seen_mensagem_id: int | None = None

    model_config = {"from_attributes": True}


class WhatsappEmpresaCatalogoRead(BaseModel):
    id: int
    nome: str
    rede_id: int


class WhatsappFuncionarioOpcaoRead(BaseModel):
    id: int
    nome: str
    email: str | None = None
    telefone: str | None = None
    tipo: str
    empresas: list[WhatsappEmpresaOpcaoRead] = Field(default_factory=list)
    rede_id: int | None = None
    rede_nome: str | None = None
    similaridade: float | None = Field(
        None,
        description="Score 0–1 quando a listagem é por similaridade de nome (#593).",
    )
    similaridade_alta: bool = False


class WhatsappContatoRead(BaseModel):
    id: int
    nome: str
    email: str | None = None
    telefone: str | None = None
    tipo: str
    empresas: list[WhatsappEmpresaOpcaoRead] = Field(default_factory=list)
    rede_id: int | None = None
    rede_nome: str | None = None


class WhatsappIniciarChatBody(BaseModel):
    funcionario_id: int | None = None
    telefone: str | None = Field(
        None,
        description="Número WhatsApp (dígitos). Obrigatório se funcionário sem telefone ou número avulso.",
    )
    mensagem_inicial: str | None = Field(None, max_length=4000)
    empresa_id: int | None = Field(
        None,
        description="Empresa de contexto opcional. Com >1 empresas, pode ficar em branco e ser definida depois na conversa.",
    )

    @field_validator("telefone", mode="before")
    @classmethod
    def telefone_digitos(cls, v: object) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        digits = "".join(ch for ch in str(v) if ch.isdigit())
        return digits or None


class WhatsappEmpresaContextoBody(BaseModel):
    empresa_id: int = Field(..., ge=1, description="Empresa de contexto do atendimento")


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
    email: str | None = Field(default=None, max_length=255)
    rede_id: int
    tipo: str = Field(default="colaborador", description="colaborador | supervisor")
    escopo_empresas: str = Field(default="selected", description="all | selected")
    empresa_ids: list[int] = Field(default_factory=list)
    empresa_id: int | None = Field(
        None,
        description="Empresa exibida no chat quando o funcionário tem várias empresas.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def email_opcional(cls, v: object) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v).strip()


class WhatsappAbrirTicketBody(BaseModel):
    empresa_id: int
    setor_id: int
    assunto: str = Field(..., min_length=1, max_length=500)
    descricao: str | None = None
    natureza_id: int | None = Field(None, description="Natureza da demanda escalada (opcional)")
    motivo_id: int | None = Field(None, description="Motivo opcional; deve pertencer à natureza")


class WhatsappChatDemandaCreate(BaseModel):
    natureza_id: int
    motivo_id: int | None = None
    descricao_curta: str | None = Field(None, max_length=500)


class WhatsappChatDemandaUpdate(BaseModel):
    natureza_id: int | None = None
    motivo_id: int | None = None
    descricao_curta: str | None = Field(None, max_length=500)


class WhatsappChatDemandaRead(BaseModel):
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

    model_config = {"from_attributes": True}


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
