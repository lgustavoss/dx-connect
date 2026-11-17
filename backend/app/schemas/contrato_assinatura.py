"""Schemas da assinatura eletrônica multiparte do contrato (#1380 / #1429)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PapelSignatario = Literal["contratante", "contratada", "testemunha"]


def _digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def normalizar_cpf(raw: str) -> str:
    return _digitos(raw)


def cpf_valido(digits: str) -> bool:
    d = _digitos(digits)
    if len(d) != 11 or d == d[0] * 11:
        return False

    def _dv(base: str, fatores: list[int]) -> str:
        soma = sum(int(base[i]) * fatores[i] for i in range(len(fatores)))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = _dv(d[:9], list(range(10, 1, -1)))
    d2 = _dv(d[:9] + d1, list(range(11, 1, -1)))
    return d[-2:] == d1 + d2


def mascarar_cpf(digits: str | None) -> str | None:
    d = _digitos(digits or "")
    if len(d) != 11:
        return None
    return f"***.***.***-{d[-2:]}"


def formatar_cpf(digits: str | None) -> str | None:
    d = _digitos(digits or "")
    if len(d) != 11:
        return None
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


class ContratoAssinaturaParteRead(BaseModel):
    id: int
    papel: str
    ordem: int
    nome: str
    email: str
    cpf_mascarado: str | None = None
    telefone: str | None = None
    role_docuseal: str
    submitter_slug: str | None = None
    link_assinatura: str | None = None
    status: str
    visualizado_em: datetime | None = None
    assinado_em: datetime | None = None
    ultimo_erro: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ContratoAssinaturaRead(BaseModel):
    id: int
    contrato_id: int
    provedor: str
    status: str
    submission_id: str | None = None
    submitter_slug: str | None = None
    link_assinatura: str | None = None
    enviado_em: datetime | None = None
    visualizado_em: datetime | None = None
    assinado_em: datetime | None = None
    expira_em: datetime | None = None
    tem_pdf_assinado: bool = False
    tem_audit_log: bool = False
    tem_selfie: bool = False
    pdf_sha256: str | None = None
    audit_sha256: str | None = None
    ultimo_erro: str | None = None
    criado_por_id: int | None = None
    created_at: datetime
    partes: list[ContratoAssinaturaParteRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ContratoAssinaturaParteIn(BaseModel):
    papel: PapelSignatario
    nome: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=255)
    cpf: str = Field(..., min_length=11, max_length=18)
    telefone: str | None = Field(None, max_length=40)

    @field_validator("cpf")
    @classmethod
    def _cpf_ok(cls, v: str) -> str:
        d = normalizar_cpf(v)
        if not cpf_valido(d):
            raise ValueError("CPF inválido.")
        return d


class ContratoAssinaturaEnviarIn(BaseModel):
    """Lista de partes: 1 contratante + 1 contratada + 0–4 testemunhas (#1429)."""

    signatarios: list[ContratoAssinaturaParteIn] = Field(..., min_length=2)
    forcar_reenvio: bool = False

    @field_validator("signatarios")
    @classmethod
    def _trim_signatarios(cls, rows: list[ContratoAssinaturaParteIn]) -> list[ContratoAssinaturaParteIn]:
        out: list[ContratoAssinaturaParteIn] = []
        for row in rows:
            out.append(
                ContratoAssinaturaParteIn(
                    papel=row.papel,
                    nome=row.nome.strip(),
                    email=row.email.strip().lower(),
                    cpf=row.cpf,
                    telefone=(row.telefone or "").strip() or None,
                )
            )
        return out

    @model_validator(mode="after")
    def _valida_papeis(self) -> ContratoAssinaturaEnviarIn:
        from app.models.contrato_assinatura import (
            MAX_TESTEMUNHAS,
            PAPEL_CONTRATADA,
            PAPEL_CONTRATANTE,
            PAPEL_TESTEMUNHA,
        )

        n_contratante = sum(1 for s in self.signatarios if s.papel == PAPEL_CONTRATANTE)
        n_contratada = sum(1 for s in self.signatarios if s.papel == PAPEL_CONTRATADA)
        n_testemunha = sum(1 for s in self.signatarios if s.papel == PAPEL_TESTEMUNHA)
        if n_contratante != 1:
            raise ValueError("Informe exatamente um signatário com papel contratante.")
        if n_contratada != 1:
            raise ValueError("Informe exatamente um signatário com papel contratada.")
        if n_testemunha > MAX_TESTEMUNHAS:
            raise ValueError(f"No máximo {MAX_TESTEMUNHAS} testemunhas por envelope.")
        emails = [s.email for s in self.signatarios]
        if len(emails) != len(set(emails)):
            raise ValueError("Cada signatário precisa de um e-mail distinto.")
        cpfs = [s.cpf for s in self.signatarios]
        if len(cpfs) != len(set(cpfs)):
            raise ValueError("Cada signatário precisa de um CPF distinto.")
        return self


class ContratoAssinaturaWebhookAck(BaseModel):
    ok: bool = True
    contrato_id: int | None = None
    assinatura_id: int | None = None
    status: str | None = None
