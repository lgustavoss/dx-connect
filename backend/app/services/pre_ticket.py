"""Persistência e fluxo de sessões de pré-ticket (#809 / #813 / #814)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.pre_ticket_historico import PreTicketHistorico
from app.models.pre_ticket_sessao import PreTicketSessao
from app.models.ticket import Ticket
from app.schemas.pre_ticket import PreTicketRascunhoUpdate, PreTicketSessaoCreate
from app.services import pre_ticket_ai as ai_svc
from app.services import pre_ticket_github as gh_svc
from app.services import pre_ticket_metricas as metricas_svc


def tenant_id(atendente: Atendente) -> int:
    return int(getattr(atendente, "tenant_id", None) or 1)


def _carregar_atendente_nome(db: Session, atendente_id: int | None) -> str | None:
    if not atendente_id:
        return None
    row = db.get(Atendente, atendente_id)
    return row.nome if row else None


def _parse_analise(row: PreTicketSessao) -> dict | None:
    if not row.analise_json:
        return None
    try:
        return json.loads(row.analise_json)
    except json.JSONDecodeError:
        return None


def registrar_historico(
    db: Session,
    sessao_id: int,
    acao: str,
    atendente: Atendente | None,
    *,
    detalhe: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        PreTicketHistorico(
            sessao_id=sessao_id,
            acao=acao,
            detalhe=detalhe,
            atendente_id=atendente.id if atendente else None,
            atendente_nome=atendente.nome if atendente else None,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
        )
    )


def serializar(row: PreTicketSessao, db: Session) -> dict:
    analise = _parse_analise(row)
    return {
        "id": row.id,
        "ticket_id": row.ticket_id,
        "contexto": row.contexto,
        "problema": row.problema,
        "impacto": row.impacto,
        "evidencias": row.evidencias,
        "urgencia": row.urgencia,
        "estado": row.estado,
        "prompt_version": row.prompt_version,
        "analise": analise,
        "rascunho_titulo": row.rascunho_titulo,
        "rascunho_corpo": row.rascunho_corpo,
        "rascunho_publicado_titulo": row.rascunho_publicado_titulo,
        "rascunho_publicado_corpo": row.rascunho_publicado_corpo,
        "github_repo": row.github_repo,
        "github_issue_number": row.github_issue_number,
        "github_issue_url": row.github_issue_url,
        "github_last_error": row.github_last_error,
        "criado_por_nome": _carregar_atendente_nome(db, row.criado_por_id),
        "aprovado_por_nome": _carregar_atendente_nome(db, row.aprovado_por_id),
        "publicado_por_nome": _carregar_atendente_nome(db, row.publicado_por_id),
        "aprovado_em": row.aprovado_em,
        "publicado_em": row.publicado_em,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def serializar_historico(row: PreTicketHistorico) -> dict:
    payload = None
    if row.payload_json:
        try:
            payload = json.loads(row.payload_json)
        except json.JSONDecodeError:
            payload = None
    return {
        "id": row.id,
        "acao": row.acao,
        "detalhe": row.detalhe,
        "atendente_nome": row.atendente_nome,
        "payload": payload,
        "created_at": row.created_at,
    }


def item_lista(row: PreTicketSessao, db: Session) -> dict:
    analise = _parse_analise(row)
    return {
        "id": row.id,
        "ticket_id": row.ticket_id,
        "estado": row.estado,
        "rascunho_titulo": row.rascunho_titulo,
        "classificacao": analise.get("classificacao") if analise else None,
        "criado_por_nome": _carregar_atendente_nome(db, row.criado_por_id),
        "created_at": row.created_at,
    }


def _validar_ticket(db: Session, tenant_id_val: int, ticket_id: int | None) -> None:
    if ticket_id is None:
        return
    ticket = db.get(Ticket, ticket_id)
    if not ticket or int(ticket.tenant_id) != tenant_id_val:
        raise HTTPException(status_code=404, detail="Ticket não encontrado.")


def obter(db: Session, sessao_id: int, tenant_id_val: int) -> PreTicketSessao:
    row = (
        db.query(PreTicketSessao)
        .filter(PreTicketSessao.id == sessao_id, PreTicketSessao.tenant_id == tenant_id_val)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Sessão de pré-ticket não encontrada.")
    return row


def listar(db: Session, tenant_id_val: int, *, limite: int = 50) -> list[PreTicketSessao]:
    return (
        db.query(PreTicketSessao)
        .filter(PreTicketSessao.tenant_id == tenant_id_val)
        .order_by(PreTicketSessao.id.desc())
        .limit(limite)
        .all()
    )


def listar_historico(db: Session, row: PreTicketSessao) -> list[PreTicketHistorico]:
    return (
        db.query(PreTicketHistorico)
        .filter(PreTicketHistorico.sessao_id == row.id)
        .order_by(PreTicketHistorico.created_at.asc())
        .all()
    )


def criar(db: Session, admin: Atendente, data: PreTicketSessaoCreate) -> PreTicketSessao:
    tid = tenant_id(admin)
    _validar_ticket(db, tid, data.ticket_id)
    row = PreTicketSessao(
        tenant_id=tid,
        ticket_id=data.ticket_id,
        criado_por_id=admin.id,
        contexto=data.contexto.strip(),
        problema=data.problema.strip(),
        impacto=(data.impacto or "").strip() or None,
        evidencias=(data.evidencias or "").strip() or None,
        urgencia=(data.urgencia or "").strip() or None,
        estado="rascunho",
    )
    db.add(row)
    db.flush()
    registrar_historico(db, row.id, "criar", admin, detalhe="Sessão criada")
    registrar_audit(db, "pre_ticket_sessao", row.id, "create", admin.id)
    db.commit()
    db.refresh(row)
    return row


def atualizar_rascunho(
    db: Session, row: PreTicketSessao, admin: Atendente, data: PreTicketRascunhoUpdate
) -> PreTicketSessao:
    if row.estado in ("publicado", "descartado"):
        raise HTTPException(status_code=400, detail="Esta sessão não pode ser editada.")
    alteracoes: dict[str, Any] = {}
    if data.rascunho_titulo is not None:
        row.rascunho_titulo = data.rascunho_titulo.strip() or None
        alteracoes["titulo"] = True
    if data.rascunho_corpo is not None:
        row.rascunho_corpo = data.rascunho_corpo.strip() or None
        alteracoes["corpo"] = True
    if not alteracoes:
        return row
    registrar_historico(
        db, row.id, "editar_rascunho", admin, detalhe="Rascunho editado", payload=alteracoes
    )
    registrar_audit(db, "pre_ticket_sessao", row.id, "editar_rascunho", admin.id, payload=alteracoes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def analisar(db: Session, row: PreTicketSessao, admin: Atendente) -> PreTicketSessao:
    if row.estado in ("publicado", "descartado"):
        raise HTTPException(status_code=400, detail="Esta sessão não pode ser analisada.")

    resultado = ai_svc.analisar(
        contexto=row.contexto,
        problema=row.problema,
        impacto=row.impacto,
        evidencias=row.evidencias,
        urgencia=row.urgencia,
        ticket_id=row.ticket_id,
    )
    metricas_svc.registrar_chamada_ia(
        db,
        tenant_id=row.tenant_id,
        sessao_id=row.id,
        atendente_id=admin.id,
        meta=resultado.meta,
        sucesso=resultado.data is not None,
    )
    if resultado.http_error:
        db.commit()
        raise resultado.http_error

    resultado_data = resultado.data or {}
    row.analise_json = json.dumps(resultado_data, ensure_ascii=False)
    row.prompt_version = resultado_data["prompt_version"]
    row.rascunho_titulo = resultado_data["titulo_sugerido"]
    row.rascunho_corpo = resultado_data["corpo_sugerido"]
    row.estado = "analisado"
    registrar_historico(
        db,
        row.id,
        "analisar",
        admin,
        detalhe=f"Análise IA ({resultado_data['prompt_version']})",
        payload={"classificacao": resultado_data["classificacao"]},
    )
    registrar_audit(
        db,
        "pre_ticket_sessao",
        row.id,
        "analisar",
        admin.id,
        payload={"prompt_version": resultado_data["prompt_version"]},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def aprovar(db: Session, row: PreTicketSessao, admin: Atendente) -> PreTicketSessao:
    if row.estado not in ("analisado", "aprovado"):
        raise HTTPException(
            status_code=400,
            detail="Analise a sessão antes de aprovar o rascunho.",
        )
    if not row.rascunho_titulo or not row.rascunho_corpo:
        raise HTTPException(status_code=400, detail="Rascunho incompleto para aprovação.")
    row.estado = "aprovado"
    row.aprovado_por_id = admin.id
    row.aprovado_em = datetime.now(timezone.utc)
    registrar_historico(db, row.id, "aprovar", admin, detalhe="Rascunho aprovado para publicação")
    registrar_audit(db, "pre_ticket_sessao", row.id, "aprovar", admin.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def publicar_github(db: Session, row: PreTicketSessao, admin: Atendente) -> PreTicketSessao:
    if row.github_issue_number:
        return row
    analise = _parse_analise(row) or {}
    row = gh_svc.criar_issue(db, row, admin, analise)
    registrar_historico(
        db,
        row.id,
        "publicar",
        admin,
        detalhe=f"Issue GitHub #{row.github_issue_number}",
        payload={"github_issue_number": row.github_issue_number, "github_repo": row.github_repo},
    )
    registrar_audit(
        db,
        "pre_ticket_sessao",
        row.id,
        "publicar",
        admin.id,
        payload={
            "github_issue_number": row.github_issue_number,
            "rascunho_publicado_titulo": row.rascunho_publicado_titulo,
            "prompt_version": row.prompt_version,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def descartar(db: Session, row: PreTicketSessao, admin: Atendente) -> PreTicketSessao:
    if row.estado == "publicado":
        raise HTTPException(status_code=400, detail="Sessão já publicada no GitHub.")
    row.estado = "descartado"
    registrar_historico(db, row.id, "descartar", admin, detalhe="Sessão descartada")
    registrar_audit(db, "pre_ticket_sessao", row.id, "descartar", admin.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
