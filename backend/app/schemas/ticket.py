from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime

from app.core.ticket_prioridade import PrioridadeTicket


class TicketCreate(BaseModel):
    empresa_id: int | None = None
    rede_id: int | None = None
    setor_id: int
    assunto: str
    descricao: str | None = None
    aberto_por_id: int | None = None
    parent_ticket_id: int | None = None
    prioridade: PrioridadeTicket = PrioridadeTicket.normal

    @model_validator(mode="after")
    def validar_escopo(self):
        e, r = self.empresa_id, self.rede_id
        if e is not None and r is not None:
            raise ValueError("Informe a empresa ou a rede (coordenação), não ambos.")
        if e is None and r is None:
            raise ValueError("Informe a empresa ou a rede (ticket de coordenação).")
        if self.parent_ticket_id is not None and e is None:
            raise ValueError("Ticket filho exige empresa vinculada.")
        return self


class TicketUpdate(BaseModel):
    """Assunto e descrição não são editáveis aqui — use mensagens no ticket."""

    empresa_id: int | None = None
    setor_id: int | None = None
    status_id: int | None = None
    atendente_id: int | None = None
    parent_ticket_id: int | None = None
    prioridade: PrioridadeTicket | None = None
    motivo_id: int | None = None
    motivo_outro_texto: str | None = Field(None, max_length=255)


class TicketParentBrief(BaseModel):
    id: int
    protocolo: str
    assunto: str
    status_nome: str | None = None
    fechado_em: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketChildBrief(BaseModel):
    id: int
    protocolo: str
    assunto: str
    status_nome: str | None = None
    atendente_nome: str | None = None
    fechado_em: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketVinculoOutroBrief(BaseModel):
    id: int
    protocolo: str
    assunto: str
    status_nome: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketVinculoRead(BaseModel):
    id: int
    tipo: str
    rotulo: str
    outro_ticket: TicketVinculoOutroBrief
    duplicado_fechado: bool = False


class TicketVinculoCreate(BaseModel):
    related_ticket_id: int
    tipo: Literal["duplicado_de", "relacionado_a"]
    fechar_como_duplicado: bool = Field(
        default=True,
        description="Se tipo=duplicado_de, encerra este ticket e registra mensagem pública apontando para o original.",
    )
    motivo_id: int | None = None
    motivo_outro_texto: str | None = Field(None, max_length=255)


class TicketFilhoMassaEmpresaOpcao(BaseModel):
    id: int
    nome: str
    ja_tem_filho: bool


class TicketFilhosMassaOpcoesRead(BaseModel):
    rede_id: int
    rede_nome: str | None = None
    assunto_padrao: str
    descricao_padrao: str | None = None
    setor_id: int
    empresas: list[TicketFilhoMassaEmpresaOpcao] = Field(default_factory=list)


class TicketFilhosMassaCreate(BaseModel):
    empresa_ids: list[int] = Field(..., min_length=1)
    assunto: str | None = Field(None, max_length=500)
    descricao: str | None = None
    setor_id: int | None = None


class TicketFilhoMassaCriado(BaseModel):
    id: int
    protocolo: str
    empresa_id: int
    empresa_nome: str


class TicketFilhosMassaRead(BaseModel):
    criados: list[TicketFilhoMassaCriado]
    total: int


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
    coordenacao_rede: bool = False
    empresa_nome: str | None = None
    rede_nome: str | None = None
    setor_nome: str | None = None
    status_nome: str | None = None
    atendente_nome: str | None = None
    parent_ticket_id: int | None = None
    prioridade: PrioridadeTicket = PrioridadeTicket.normal
    motivo_id: int | None = None
    motivo_nome: str | None = None
    motivo_outro_texto: str | None = None
    natureza_id: int | None = None
    natureza_nome: str | None = None
    parent: TicketParentBrief | None = None
    children: list[TicketChildBrief] = Field(default_factory=list)
    vinculos: list[TicketVinculoRead] = Field(default_factory=list)
    triagem_inbound: TicketTriagemInbound | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketMensagemCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=20000)
    tipo: Literal["publico", "interno"]
    notificar_cliente_por_email: bool = Field(
        default=False,
        description="Se true e tipo=publico, agenda envio por e-mail ao último remetente (janela de edição #140) e regista Message-ID após envio (#165).",
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
    status: str | None = Field(
        None,
        description="Estado da fila de e-mail (#140): pendente_envio, em_edicao, enviada, cancelada, etc.",
    )
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketMensagemUpdate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=20000)
    edit_lock_token: str = Field(..., min_length=1, max_length=64)


class TicketMensagemStartEditRead(BaseModel):
    edit_lock_token: str
    mensagem: TicketMensagemRead


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
