"""Fatura interna: geração mensal e aprovação do financeiro (#326)."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.comercial_contrato import CONTRATO_ASSINADO, Contrato
from app.models.crm import CrmNegociacaoCnpjLinha
from app.models.empresa import Empresa
from app.models.faturamento import (
    FATURA_AGUARDANDO,
    FATURA_APROVADA,
    FATURA_CANCELADA,
    FATURA_REJEITADA,
    VENCIMENTO_DIA_PADRAO,
    Fatura,
)

TZ_SP = ZoneInfo("America/Sao_Paulo")
_COMPETENCIA_RE = re.compile(r"^(\d{4})-(\d{2})$")


def competencia_atual(hoje: date | None = None) -> str:
    d = hoje or datetime.now(TZ_SP).date()
    return f"{d.year:04d}-{d.month:02d}"


def validar_competencia(valor: str | None) -> str:
    raw = (valor or competencia_atual()).strip()
    m = _COMPETENCIA_RE.match(raw)
    if not m:
        raise HTTPException(status_code=400, detail="Competência inválida. Use YYYY-MM.")
    ano, mes = int(m.group(1)), int(m.group(2))
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Competência inválida. Use YYYY-MM.")
    return f"{ano:04d}-{mes:02d}"


def vencimento_da_competencia(competencia: str) -> date:
    """Dia 10 do mês seguinte à competência (fatura de agosto vence em 10/09)."""
    ano, mes = (int(p) for p in competencia.split("-"))
    if mes == 12:
        ano, mes = ano + 1, 1
    else:
        mes += 1
    ultimo = calendar.monthrange(ano, mes)[1]
    dia = min(VENCIMENTO_DIA_PADRAO, ultimo)
    return date(ano, mes, dia)


def _linha_contrato(db: Session, contrato: Contrato) -> CrmNegociacaoCnpjLinha | None:
    if contrato.linha:
        return contrato.linha
    return db.query(CrmNegociacaoCnpjLinha).filter(CrmNegociacaoCnpjLinha.id == contrato.negociacao_linha_cnpj_id).first()


def fatura_para_read(db: Session, row: Fatura) -> dict:
    contrato = row.contrato or db.query(Contrato).filter(Contrato.id == row.contrato_id).first()
    empresa = row.empresa
    if empresa is None and row.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == row.empresa_id).first()
    linha = _linha_contrato(db, contrato) if contrato else None
    return {
        "id": row.id,
        "contrato_id": row.contrato_id,
        "empresa_id": row.empresa_id,
        "empresa_nome": empresa.nome if empresa else None,
        "cnpj": linha.cnpj if linha else (empresa.cnpj_cpf if empresa else None),
        "razao_social": (linha.razao_social if linha else None) or (empresa.razao_social if empresa else None),
        "competencia": row.competencia,
        "valor": row.valor,
        "vencimento": row.vencimento,
        "emite_nfse": bool(row.emite_nfse),
        "status": row.status,
        "rejeicao_motivo": row.rejeicao_motivo,
        "gerada_em": row.gerada_em,
        "aprovada_por_id": row.aprovada_por_id,
        "aprovada_por_nome": row.aprovada_por.nome if row.aprovada_por else None,
        "aprovada_em": row.aprovada_em,
    }


def _contratos_faturaveis(db: Session) -> list[Contrato]:
    return (
        db.query(Contrato)
        .options(joinedload(Contrato.linha))
        .filter(Contrato.status == CONTRATO_ASSINADO, Contrato.empresa_id.isnot(None))
        .order_by(Contrato.id.asc())
        .all()
    )


def _emite_nfse_empresa(db: Session, empresa_id: int | None) -> bool:
    if not empresa_id:
        return True
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if emp is None:
        return True
    return bool(getattr(emp, "emite_nfse", True))


def _competencia_antes_inicio(contrato: Contrato, competencia: str) -> bool:
    inicio = contrato.data_inicio
    if inicio is None:
        return False
    return competencia < f"{inicio.year:04d}-{inicio.month:02d}"


def _preencher_fatura(db: Session, row: Fatura, contrato: Contrato, competencia: str) -> None:
    row.contrato_id = contrato.id
    row.empresa_id = contrato.empresa_id
    row.competencia = competencia
    row.valor = Decimal(str(contrato.valor_mensalidade or 0))
    row.vencimento = vencimento_da_competencia(competencia)
    row.emite_nfse = _emite_nfse_empresa(db, contrato.empresa_id)
    row.status = FATURA_AGUARDANDO
    row.rejeicao_motivo = None
    row.aprovada_por_id = None
    row.aprovada_em = None
    row.gerada_em = datetime.now(timezone.utc)


def obter_fatura(db: Session, fatura_id: int) -> Fatura:
    row = (
        db.query(Fatura)
        .options(
            joinedload(Fatura.contrato).joinedload(Contrato.linha),
            joinedload(Fatura.empresa),
            joinedload(Fatura.aprovada_por),
        )
        .filter(Fatura.id == fatura_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Fatura não encontrada.")
    return row


def listar_faturas(db: Session, *, competencia: str | None, status_filtro: str | None) -> list[Fatura]:
    q = db.query(Fatura).options(
        joinedload(Fatura.contrato).joinedload(Contrato.linha),
        joinedload(Fatura.empresa),
        joinedload(Fatura.aprovada_por),
    )
    if competencia:
        q = q.filter(Fatura.competencia == validar_competencia(competencia))
    if status_filtro:
        q = q.filter(Fatura.status == status_filtro.strip())
    return q.order_by(Fatura.competencia.desc(), Fatura.id.desc()).all()


def listar_contratos_elegiveis(db: Session) -> list[dict]:
    out: list[dict] = []
    for c in _contratos_faturaveis(db):
        emp = db.query(Empresa).filter(Empresa.id == c.empresa_id).first() if c.empresa_id else None
        linha = _linha_contrato(db, c)
        out.append(
            {
                "id": c.id,
                "empresa_id": c.empresa_id,
                "empresa_nome": emp.nome if emp else None,
                "cnpj": linha.cnpj if linha else (emp.cnpj_cpf if emp else None),
                "razao_social": (linha.razao_social if linha else None) or (emp.razao_social if emp else None),
                "valor_mensalidade": c.valor_mensalidade,
            }
        )
    return out


def gerar_fatura_contrato(db: Session, contrato_id: int, competencia: str | None) -> tuple[Fatura, bool]:
    comp = validar_competencia(competencia)
    contrato = (
        db.query(Contrato)
        .options(joinedload(Contrato.linha))
        .filter(Contrato.id == contrato_id)
        .first()
    )
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    if contrato.status != CONTRATO_ASSINADO or not contrato.empresa_id:
        raise HTTPException(status_code=400, detail="Só contratos assinados com empresa vinculada geram fatura.")
    if _competencia_antes_inicio(contrato, comp):
        raise HTTPException(status_code=400, detail="Competência anterior ao início do contrato.")
    existente = db.query(Fatura).filter(Fatura.contrato_id == contrato.id, Fatura.competencia == comp).first()
    if existente:
        if existente.status == FATURA_APROVADA:
            raise HTTPException(status_code=400, detail="Já existe fatura aprovada desta competência.")
        if existente.status == FATURA_CANCELADA:
            raise HTTPException(status_code=400, detail="Fatura desta competência está cancelada.")
        if existente.status == FATURA_AGUARDANDO:
            return existente, False
        _preencher_fatura(db, existente, contrato, comp)
        db.flush()
        return existente, False
    row = Fatura()
    _preencher_fatura(db, row, contrato, comp)
    db.add(row)
    db.flush()
    return row, True


def gerar_competencia(
    db: Session,
    competencia: str | None,
    *,
    reabrir_rejeitadas: bool = False,
) -> tuple[str, int, int, int, int | None]:
    """Gera faturas da competência. O job não reabre rejeitadas; a acção manual sim."""
    comp = validar_competencia(competencia)
    criadas = 0
    existentes = 0
    reabertas = 0
    audit_id: int | None = None
    for contrato in _contratos_faturaveis(db):
        if _competencia_antes_inicio(contrato, comp):
            continue
        existente = db.query(Fatura).filter(Fatura.contrato_id == contrato.id, Fatura.competencia == comp).first()
        if existente:
            if reabrir_rejeitadas and existente.status == FATURA_REJEITADA:
                _preencher_fatura(db, existente, contrato, comp)
                reabertas += 1
                if audit_id is None:
                    audit_id = existente.id
            else:
                existentes += 1
            continue
        row = Fatura()
        _preencher_fatura(db, row, contrato, comp)
        db.add(row)
        db.flush()
        criadas += 1
        if audit_id is None:
            audit_id = row.id
    db.flush()
    return comp, criadas, existentes, reabertas, audit_id


def processar_faturamento_mensal(db: Session) -> int:
    """Job: gera faturas novas da competência atual (idempotente; não reabre rejeitadas)."""
    _, criadas, _, _, _ = gerar_competencia(db, None, reabrir_rejeitadas=False)
    return criadas


def aprovar_fatura(db: Session, row: Fatura, ator: Atendente) -> Fatura:
    if row.status != FATURA_AGUARDANDO:
        raise HTTPException(status_code=400, detail="Só faturas aguardando aprovação podem ser aprovadas.")
    row.status = FATURA_APROVADA
    row.aprovada_por_id = ator.id
    row.aprovada_em = datetime.now(timezone.utc)
    row.rejeicao_motivo = None
    db.flush()
    return row


def rejeitar_fatura(db: Session, row: Fatura, motivo: str) -> Fatura:
    if row.status != FATURA_AGUARDANDO:
        raise HTTPException(status_code=400, detail="Só faturas aguardando aprovação podem ser rejeitadas.")
    texto = (motivo or "").strip()
    if len(texto) < 3:
        raise HTTPException(status_code=400, detail="Informe o motivo da rejeição.")
    row.status = FATURA_REJEITADA
    row.rejeicao_motivo = texto
    row.aprovada_por_id = None
    row.aprovada_em = None
    db.flush()
    return row
