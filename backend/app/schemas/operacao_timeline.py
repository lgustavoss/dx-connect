"""Schemas da timeline 360 e da saúde do cliente da carteira (#912 / #914)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CategoriaEvento(str, Enum):
    """Categorias operacionais da jornada do cliente.

    `cobranca` (#1385) cobre fatura e título a receber derivados — os eventos
    não carregam valores; o bloco financeiro da ficha usa o resumo de
    /v1/faturamento/a-receber com o RBAC `faturamento.ver`.
    """

    crm = "crm"
    implantacao = "implantacao"
    suporte = "suporte"
    cobranca = "cobranca"


class EventoTimelineRead(BaseModel):
    """Marco da jornada do cliente derivado das tabelas existentes.

    Não há tabela de eventos no MVP: `id` é estável porque combina tipo + origem
    (`<tipo>-<id da origem>`), o que também garante a deduplicação.
    """

    id: str
    em: datetime
    categoria: CategoriaEvento
    tipo: str
    titulo: str
    detalhe: str | None = None
    # Navegação no painel: crm_negociacao, comercial_contrato, comercial_proposta,
    # ticket, fatura, titulo.
    ref_tipo: str | None = None
    ref_id: int | None = None


class SaudeStatus(str, Enum):
    """Status resumido de saúde/engajamento do cliente da carteira."""

    saudavel = "saudavel"
    atencao = "atencao"
    risco = "risco"


class SinalSaudeRead(BaseModel):
    """Sinal objetivo que compõe o status de saúde.

    `nivel` segue os valores de `SaudeStatus`; `info` indica sinal informativo
    (não altera o status, apenas dá contexto ao operador).
    """

    codigo: str
    rotulo: str
    valor: str
    nivel: str
    explicacao: str | None = None


class SaudeEmpresaRead(BaseModel):
    """Status de saúde + sinais objetivos de uma empresa da carteira."""

    empresa_id: int
    empresa_nome: str
    rede_id: int | None = None
    rede_nome: str | None = None
    ativo: bool = True
    status: SaudeStatus
    motivos: list[str] = Field(default_factory=list)
    sinais: list[SinalSaudeRead] = Field(default_factory=list)
    ultimo_evento_em: datetime | None = None
    dias_sem_movimento: int | None = None
    atualizado_em: datetime
