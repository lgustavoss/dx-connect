"""Vínculo de chat com negociação do CRM e repasse para a empresa (#1182 / #S202610-0006)."""

from __future__ import annotations

import re

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.crm import FUNIL_TIPO_PERDIDO, CrmLead, CrmNegociacao, CrmNegociacaoCnpjLinha, FunilEstagio
from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa
from app.models.whatsapp_chat import WhatsappChat
from app.services.funcionario_escopo import sincronizar_vinculos_empresas
from app.services.permissao_grupos import tem_permissao


def _digits(valor: str | None) -> str:
    return re.sub(r"\D", "", valor or "")


def _exigir_crm(ator: Atendente) -> None:
    if not tem_permissao(ator, "crm.ver"):
        raise HTTPException(status_code=403, detail="Sem permissão para ver o CRM")


def buscar_negociacoes_abertas(db: Session, ator: Atendente, q: str | None, *, limit: int = 20) -> list[dict]:
    _exigir_crm(ator)
    query = (
        db.query(CrmNegociacao)
        .join(FunilEstagio, FunilEstagio.id == CrmNegociacao.estagio_id)
        .join(CrmLead, CrmLead.id == CrmNegociacao.lead_id)
        .options(joinedload(CrmNegociacao.estagio), joinedload(CrmNegociacao.lead))
        .filter(CrmNegociacao.ativa.is_(True), FunilEstagio.tipo != FUNIL_TIPO_PERDIDO)
    )
    termo = (q or "").strip()
    if termo:
        like = f"%{termo}%"
        query = query.outerjoin(CrmNegociacaoCnpjLinha).filter(
            (CrmNegociacao.titulo.ilike(like))
            | (CrmLead.nome.ilike(like))
            | (CrmLead.telefone.ilike(like))
            | (CrmNegociacaoCnpjLinha.razao_social.ilike(like))
        )
    rows = query.distinct().order_by(CrmNegociacao.id.desc()).limit(limit).all()
    return [
        {
            "id": n.id,
            "titulo": n.titulo,
            "lead_nome": n.lead.nome if n.lead else None,
            "lead_telefone": n.lead.telefone if n.lead else None,
            "estagio_nome": n.estagio.nome if n.estagio else None,
        }
        for n in rows
    ]


def _negociacao_vinculavel(db: Session, negociacao_id: int) -> CrmNegociacao:
    neg = (
        db.query(CrmNegociacao)
        .options(joinedload(CrmNegociacao.estagio), joinedload(CrmNegociacao.lead))
        .filter(CrmNegociacao.id == negociacao_id)
        .first()
    )
    if neg is None:
        raise HTTPException(status_code=404, detail="Negociação não encontrada")
    tipo = neg.estagio.tipo if neg.estagio else None
    if not neg.ativa or tipo == FUNIL_TIPO_PERDIDO:
        raise HTTPException(status_code=400, detail="Só é possível vincular uma negociação em aberto.")
    return neg


def vincular_negociacao(db: Session, chat: WhatsappChat, negociacao_id: int, ator: Atendente) -> WhatsappChat:
    _exigir_crm(ator)
    if chat.funcionario_rede_id:
        raise HTTPException(status_code=400, detail="Este chat já tem contato de empresa.")
    neg = _negociacao_vinculavel(db, negociacao_id)
    if chat.negociacao_id and chat.negociacao_id != neg.id:
        raise HTTPException(
            status_code=400,
            detail="Desvincule a negociação atual antes de escolher outra.",
        )
    chat.negociacao_id = neg.id
    db.add(chat)
    db.flush()
    return chat


def desvincular_negociacao(db: Session, chat: WhatsappChat, ator: Atendente) -> WhatsappChat:
    _exigir_crm(ator)
    chat.negociacao_id = None
    db.add(chat)
    db.flush()
    return chat


def chats_da_negociacao(db: Session, negociacao_id: int) -> list[dict]:
    rows = (
        db.query(WhatsappChat)
        .filter(WhatsappChat.negociacao_id == negociacao_id)
        .order_by(WhatsappChat.id.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "protocolo": c.protocolo,
            "cliente_nome": c.cliente_nome,
            "wa_id": c.wa_id,
            "estado": c.estado,
        }
        for c in rows
    ]


def _funcionario_da_empresa_por_telefone(
    db: Session, *, empresa_id: int, telefone_digits: str
) -> FuncionarioRede | None:
    if not telefone_digits:
        return None
    ids = [
        row[0]
        for row in db.query(FuncionarioRedeEmpresa.funcionario_id)
        .filter(FuncionarioRedeEmpresa.empresa_id == empresa_id)
        .all()
    ]
    if not ids:
        return None
    for func in db.query(FuncionarioRede).filter(FuncionarioRede.id.in_(ids), FuncionarioRede.ativo.is_(True)):
        if _digits(func.telefone) == telefone_digits:
            return func
    return None


def _criar_colaborador(db: Session, ator: Atendente, empresa: Empresa, chat: WhatsappChat) -> FuncionarioRede:
    nome = (chat.cliente_nome or "").strip() or "Contato do WhatsApp"
    telefone = _digits(chat.wa_id) or None
    func = FuncionarioRede(
        nome=nome[:255],
        email=None,
        telefone=telefone,
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=empresa.rede_id,
        empresa_id=empresa.id,
    )
    db.add(func)
    db.flush()
    registrar_audit(db, "funcionario_rede", func.id, "create", ator.id)
    sincronizar_vinculos_empresas(
        db,
        func,
        escopo="selected",
        rede_id=empresa.rede_id,
        empresa_ids=[empresa.id],
    )
    return func


def repassar_chats_da_negociacao(db: Session, negociacao_id: int, ator: Atendente) -> None:
    """Quando a negociação tem uma única empresa, os chats sem contato passam a usá-la."""
    linhas = db.query(CrmNegociacaoCnpjLinha).filter(CrmNegociacaoCnpjLinha.negociacao_id == negociacao_id).all()
    empresas = {ln.empresa_id for ln in linhas if ln.empresa_id}
    if len(empresas) != 1:
        return
    empresa = db.query(Empresa).filter(Empresa.id == next(iter(empresas))).first()
    if empresa is None or not empresa.rede_id:
        return
    chats = (
        db.query(WhatsappChat)
        .filter(
            WhatsappChat.negociacao_id == negociacao_id,
            WhatsappChat.empresa_id.is_(None),
            WhatsappChat.funcionario_rede_id.is_(None),
        )
        .all()
    )
    for chat in chats:
        digits = _digits(chat.wa_id)
        func = _funcionario_da_empresa_por_telefone(db, empresa_id=empresa.id, telefone_digits=digits)
        if func is None:
            func = _criar_colaborador(db, ator, empresa, chat)
        elif not _digits(func.telefone) and digits:
            func.telefone = digits
        chat.funcionario_rede_id = func.id
        chat.empresa_id = empresa.id
        db.add(chat)
    db.flush()


def emitir_fila_dos_chats(db: Session, negociacao_id: int) -> None:
    """Avisa a conversa aberta depois do commit que gravou a empresa."""
    from app.services.realtime_emit import emit_chat_fila_from_model

    chats = db.query(WhatsappChat).filter(WhatsappChat.negociacao_id == negociacao_id).all()
    for chat in chats:
        emit_chat_fila_from_model(db, chat, estado_anterior=chat.estado)
