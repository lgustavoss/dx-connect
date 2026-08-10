"""Conversão lead comercial → licença SaaS com vínculo persistido."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.models.cliente_saas import ClienteSaaS
from app.models.lead_comercial import LeadComercial
from app.schemas.saas import ClienteSaaSCreate, _validar_slug
from app.services import saas_clientes as svc
from app.services.saas_contato import obter_lead


def slug_sugerido(texto: str) -> str:
    s = unicodedata.normalize("NFD", (texto or "").strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s[:80] or "cliente"


class LeadConverterCreate(BaseModel):
    slug: str | None = Field(None, max_length=80)
    plano: str | None = Field(None, max_length=80)
    status: str = "trial"
    enfileirar_provisionamento: bool = False
    notas_extra: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("slug")
    @classmethod
    def slug_ok(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        return _validar_slug(v)


def vincular_lead_licenca(db: Session, lead: LeadComercial, cliente: ClienteSaaS) -> None:
    lead.cliente_saas_id = cliente.id
    cliente.lead_comercial_id = lead.id
    if lead.status != "fechado":
        lead.status = "fechado"
    db.flush()


def ligar_lead_ao_criar(db: Session, cliente: ClienteSaaS, lead_id: int | None) -> ClienteSaaS:
    if not lead_id:
        return cliente
    lead = obter_lead(db, lead_id)
    if not lead:
        raise svc.SaasErro("Lead comercial não encontrado", 404)
    if lead.cliente_saas_id and lead.cliente_saas_id != cliente.id:
        raise svc.SaasErro("Este lead já está vinculado a outra licença", 409)
    vincular_lead_licenca(db, lead, cliente)
    return cliente


def converter_lead(
    db: Session,
    lead_id: int,
    data: LeadConverterCreate | None = None,
) -> ClienteSaaS:
    body = data or LeadConverterCreate()
    lead = obter_lead(db, lead_id)
    if not lead:
        raise svc.SaasErro("Lead comercial não encontrado", 404)
    if lead.cliente_saas_id:
        raise svc.SaasErro("Lead já convertido em licença", 409)

    nome = (lead.empresa or lead.nome or "").strip() or f"Lead {lead.id}"
    slug = body.slug or slug_sugerido(nome)
    # Evita colisão: tenta sufixo numérico
    base = slug
    n = 2
    while db.query(ClienteSaaS.id).filter(ClienteSaaS.slug == slug).first():
        slug = f"{base}-{n}"[:80]
        n += 1
        if n > 99:
            raise svc.SaasErro("Não foi possível gerar um slug único", 409)

    notas_parts = [f"Convertido do lead #{lead.id}"]
    if lead.mensagem:
        notas_parts.append(lead.mensagem[:1500])
    if body.notas_extra:
        notas_parts.append(body.notas_extra.strip())

    create = ClienteSaaSCreate(
        nome=nome[:200],
        slug=slug,
        status=body.status if body.status in ("trial", "ativo", "suspenso", "churn") else "trial",
        plano=body.plano,
        data_inicio=date.today(),
        contato_email=lead.email,
        contato_nome=lead.nome,
        notas="\n\n".join(notas_parts),
    )
    row = svc.criar(db, create)
    vincular_lead_licenca(db, lead, row)

    if body.enfileirar_provisionamento:
        from app.services.saas_provisionamento import enfileirar_provisionamento

        try:
            enfileirar_provisionamento(db, row.id)
        except svc.SaasErro:
            pass

    return row
