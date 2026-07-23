"""Schemas e serviço de leads comerciais B2B (DR-06)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.models.lead_comercial import STATUS_LEAD_COMERCIAL, LeadComercial
from app.services.saas_notify import notificar_equipe_saas

StatusLead = Literal["novo", "em_atendimento", "fechado"]


class LeadComercialCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    empresa: str | None = Field(None, max_length=200)
    mensagem: str = Field(..., min_length=1, max_length=5000)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("nome", "mensagem")
    @classmethod
    def non_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Campo obrigatório")
        return s

    @field_validator("empresa")
    @classmethod
    def strip_empresa(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class LeadComercialUpdate(BaseModel):
    status: StatusLead | None = None
    notas_internas: str | None = None


class LeadComercialRead(BaseModel):
    id: int
    nome: str
    email: str
    empresa: str | None = None
    mensagem: str
    status: str
    origem: str
    notas_internas: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LeadComercialPublicRead(BaseModel):
    id: int
    mensagem: str


def criar_lead_publico(db: Session, data: LeadComercialCreate) -> LeadComercial:
    row = LeadComercial(
        nome=data.nome,
        email=str(data.email).strip().lower(),
        empresa=data.empresa,
        mensagem=data.mensagem,
        status="novo",
        origem="landing",
    )
    db.add(row)
    db.flush()
    notificar_equipe_saas(
        db,
        subject=f"[DeskRudder] Contato comercial — {row.nome}",
        body=(
            f"Nome: {row.nome}\n"
            f"E-mail: {row.email}\n"
            f"Empresa: {row.empresa or '—'}\n"
            f"Mensagem:\n{row.mensagem}\n"
            f"\nPainel: /saas/leads/{row.id}\n"
        ),
    )
    return row


def obter_lead(db: Session, lead_id: int) -> LeadComercial | None:
    return db.query(LeadComercial).filter(LeadComercial.id == lead_id).first()


def atualizar_lead(db: Session, lead: LeadComercial, data: LeadComercialUpdate) -> LeadComercial:
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"] not in STATUS_LEAD_COMERCIAL:
        raise ValueError("Status inválido")
    if "notas_internas" in payload and payload["notas_internas"] is not None:
        notas = payload["notas_internas"].strip()
        payload["notas_internas"] = notas or None
    for k, v in payload.items():
        setattr(lead, k, v)
    db.flush()
    return lead
