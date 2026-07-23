"""Trial / pré-cadastro público (#527 / DR-07)."""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente_saas import ClienteSaaS
from app.schemas.saas import ClienteSaaSCreate, _validar_slug
from app.services import saas_clientes as svc
from app.services.saas_notify import notificar_equipe_saas
from app.services.saas_provisionamento import enfileirar_provisionamento


class TrialSolicitacaoCreate(BaseModel):
    empresa: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=80)
    contato_nome: str = Field(..., min_length=1, max_length=200)
    contato_email: EmailStr
    notas: str | None = None
    solicitar_provisionamento: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("empresa", "contato_nome")
    @classmethod
    def non_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Campo obrigatório")
        return s

    @field_validator("slug")
    @classmethod
    def slug_ok(cls, v: str) -> str:
        return _validar_slug(v)


class TrialSolicitacaoRead(BaseModel):
    id: int
    nome: str
    slug: str
    status: str
    data_renovacao: date | None = None
    mensagem: str

    model_config = ConfigDict(from_attributes=True)


def criar_trial_publico(db: Session, data: TrialSolicitacaoCreate) -> ClienteSaaS:
    hoje = date.today()
    dias = max(1, int(settings.SAAS_TRIAL_DAYS or 14))
    create = ClienteSaaSCreate(
        nome=data.empresa,
        slug=data.slug,
        status="trial",
        plano="trial",
        data_inicio=hoje,
        data_renovacao=hoje + timedelta(days=dias),
        notas=data.notas,
    )
    row = svc.criar(db, create)
    row.contato_email = str(data.contato_email).strip().lower()
    row.contato_nome = data.contato_nome.strip()
    db.flush()

    notificar_equipe_saas(
        db,
        subject=f"[DeskRudder] Novo trial — {row.nome} ({row.slug})",
        body=(
            f"Empresa: {row.nome}\n"
            f"Slug: {row.slug}\n"
            f"Contacto: {row.contato_nome} <{row.contato_email}>\n"
            f"Trial até: {row.data_renovacao}\n"
            f"Notas: {row.notas or '—'}\n"
        ),
    )

    if data.solicitar_provisionamento:
        try:
            enfileirar_provisionamento(db, row.id)
        except svc.SaasErro:
            pass

    return row
