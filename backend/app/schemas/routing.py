from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.routing import RoutingCampo, RoutingCanal, RoutingOperador
from app.core.ticket_prioridade import PrioridadeTicket


class RoutingCondition(BaseModel):
    campo: RoutingCampo
    operador: RoutingOperador
    valor: str = Field(..., min_length=1, max_length=500)

    @field_validator("valor")
    @classmethod
    def valor_nao_vazio(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Valor da condição é obrigatório")
        return s

    @model_validator(mode="after")
    def validar_regex(self):
        if self.operador == RoutingOperador.regex:
            try:
                re.compile(self.valor)
            except re.error as e:
                raise ValueError(f"Expressão regular inválida: {e}") from e
        return self


class RoutingAction(BaseModel):
    setor_id: int | None = None
    prioridade: PrioridadeTicket | None = None
    natureza_id: int | None = None
    motivo_id: int | None = None
    atendente_id: int | None = None

    @model_validator(mode="after")
    def ao_menos_uma_acao(self):
        if not any(
            v is not None
            for v in (
                self.setor_id,
                self.prioridade,
                self.natureza_id,
                self.motivo_id,
                self.atendente_id,
            )
        ):
            raise ValueError("Informe ao menos uma ação (setor, prioridade, natureza, motivo ou atendente)")
        return self


class RoutingRuleBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    ativo: bool = True
    rede_id: int | None = Field(None, description="Null = escopo global do tenant")
    condicoes: list[RoutingCondition] = Field(..., min_length=1)
    acoes: RoutingAction


class RoutingRuleCreate(RoutingRuleBase):
    pass


class RoutingRuleUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=200)
    ativo: bool | None = None
    rede_id: int | None = None
    condicoes: list[RoutingCondition] | None = Field(None, min_length=1)
    acoes: RoutingAction | None = None


class RoutingRuleRead(RoutingRuleBase):
    id: int
    ordem: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_row(cls, row: Any) -> RoutingRuleRead:
        return cls(
            id=row.id,
            nome=row.nome,
            ativo=row.ativo,
            ordem=row.ordem,
            rede_id=row.rede_id,
            condicoes=[RoutingCondition.model_validate(c) for c in (row.condicoes or [])],
            acoes=RoutingAction.model_validate(row.acoes or {}),
        )


class RoutingRuleReorderItem(BaseModel):
    id: int
    ordem: int = Field(..., ge=0)


class RoutingRuleReorder(BaseModel):
    items: list[RoutingRuleReorderItem] = Field(..., min_length=1)


class RoutingSimulateRequest(BaseModel):
    email_from: str | None = None
    email_to: str | None = None
    assunto: str | None = None
    canal: RoutingCanal = RoutingCanal.email
    rede_id: int | None = None
    setor_id_atual: int | None = None
    aplicar_setor: bool = True


class RoutingResultRead(BaseModel):
    matched: bool = False
    rule_id: int | None = None
    rule_nome: str | None = None
    setor_id: int | None = None
    prioridade: PrioridadeTicket | None = None
    natureza_id: int | None = None
    motivo_id: int | None = None
    atendente_id: int | None = None
