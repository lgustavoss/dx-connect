"""Regras de negócio — solicitações de melhoria (#800–#804)."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.solicitacao_melhoria import (
    SolicitacaoMelhoria,
    SolicitacaoMelhoriaComentario,
    SolicitacaoMelhoriaHistorico,
)
from app.schemas.solicitacao_melhoria import (
    SolicitacaoComentarioCreate,
    SolicitacaoComentarioRead,
    SolicitacaoHistoricoRead,
    SolicitacaoMelhoriaCreate,
    SolicitacaoMelhoriaListaItem,
    SolicitacaoMelhoriaRead,
    SolicitacaoMelhoriaStatusUpdate,
)
from app.services.solicitacao_melhoria_copy import (
    STATUS_FINAIS,
    STATUS_VALIDOS,
    TIPOS_VALIDOS,
    mensagem_publica_status,
    rotulo_status,
)


def organizacao_id_de(atendente: Atendente) -> int:
    return int(getattr(atendente, "tenant_id", None) or 1)


def _is_admin(atendente: Atendente) -> bool:
    return atendente.role == "admin"


def _carregar(db: Session, solicitacao_id: int) -> SolicitacaoMelhoria:
    row = (
        db.query(SolicitacaoMelhoria)
        .options(
            joinedload(SolicitacaoMelhoria.historico).joinedload(SolicitacaoMelhoriaHistorico.atendente),
            joinedload(SolicitacaoMelhoria.comentarios),
        )
        .filter(SolicitacaoMelhoria.id == solicitacao_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return row


def _garantir_mesma_org(row: SolicitacaoMelhoria, atendente: Atendente) -> None:
    if _is_admin(atendente):
        return
    if row.organizacao_id != organizacao_id_de(atendente):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para esta solicitação")


def _historico_read(h: SolicitacaoMelhoriaHistorico) -> SolicitacaoHistoricoRead:
    nome = None
    if h.atendente is not None:
        nome = h.atendente.nome
    return SolicitacaoHistoricoRead(
        id=h.id,
        status_anterior=h.status_anterior,
        status_novo=h.status_novo,
        status_novo_rotulo=rotulo_status(h.status_novo),
        motivo=h.motivo,
        mensagem_publica=h.mensagem_publica,
        atendente_nome=nome,
        created_at=h.created_at,
    )


def serializar(row: SolicitacaoMelhoria, *, incluir_github: bool, incluir_internos: bool) -> SolicitacaoMelhoriaRead:
    comentarios = [
        SolicitacaoComentarioRead(
            id=c.id,
            corpo=c.corpo,
            publico_cliente=c.publico_cliente,
            origem=c.origem,
            autor_nome=c.autor_nome,
            created_at=c.created_at,
        )
        for c in (row.comentarios or [])
        if incluir_internos or c.publico_cliente
    ]
    return SolicitacaoMelhoriaRead(
        id=row.id,
        organizacao_id=row.organizacao_id,
        autor_atendente_id=row.autor_atendente_id,
        autor_nome=row.autor_nome,
        tipo=row.tipo,
        titulo=row.titulo,
        descricao=row.descricao,
        status=row.status,
        status_rotulo=rotulo_status(row.status),
        motivo_nao_desenvolvimento=row.motivo_nao_desenvolvimento,
        versao_contexto=row.versao_contexto,
        mensagem_status=mensagem_publica_status(row.status, motivo=row.motivo_nao_desenvolvimento),
        created_at=row.created_at,
        updated_at=row.updated_at,
        github_repo=row.github_repo if incluir_github else None,
        github_issue_number=row.github_issue_number if incluir_github else None,
        github_issue_url=row.github_issue_url if incluir_github else None,
        github_last_error=row.github_last_error if incluir_github else None,
        historico=[_historico_read(h) for h in (row.historico or [])],
        comentarios=comentarios,
    )


def criar(db: Session, atendente: Atendente, data: SolicitacaoMelhoriaCreate) -> SolicitacaoMelhoria:
    if data.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Tipo inválido")
    row = SolicitacaoMelhoria(
        organizacao_id=organizacao_id_de(atendente),
        autor_atendente_id=atendente.id,
        autor_nome=atendente.nome,
        tipo=data.tipo,
        titulo=data.titulo.strip(),
        descricao=data.descricao.strip(),
        status="aberta",
        versao_contexto=(data.versao_contexto or "").strip() or None,
    )
    db.add(row)
    db.flush()
    msg = mensagem_publica_status("aberta")
    db.add(
        SolicitacaoMelhoriaHistorico(
            solicitacao_id=row.id,
            status_anterior=None,
            status_novo="aberta",
            atendente_id=atendente.id,
            mensagem_publica=msg,
        )
    )
    db.commit()
    return _carregar(db, row.id)


def listar_minhas(db: Session, atendente: Atendente) -> list[SolicitacaoMelhoria]:
    org = organizacao_id_de(atendente)
    q = db.query(SolicitacaoMelhoria).filter(SolicitacaoMelhoria.organizacao_id == org)
    if not _is_admin(atendente):
        # Utilizador “cliente”: vê as da organização (instância), foco nas próprias no UI.
        pass
    return q.order_by(SolicitacaoMelhoria.created_at.desc()).limit(200).all()


def listar_admin(
    db: Session,
    *,
    status_filtro: str | None = None,
    tipo: str | None = None,
    organizacao_id: int | None = None,
    desde: datetime | None = None,
    ate: datetime | None = None,
) -> list[SolicitacaoMelhoria]:
    q = db.query(SolicitacaoMelhoria)
    if status_filtro:
        q = q.filter(SolicitacaoMelhoria.status == status_filtro)
    if tipo:
        q = q.filter(SolicitacaoMelhoria.tipo == tipo)
    if organizacao_id is not None:
        q = q.filter(SolicitacaoMelhoria.organizacao_id == organizacao_id)
    if desde is not None:
        q = q.filter(SolicitacaoMelhoria.created_at >= desde)
    if ate is not None:
        q = q.filter(SolicitacaoMelhoria.created_at <= ate)
    return q.order_by(SolicitacaoMelhoria.created_at.desc()).limit(500).all()


def obter_para_leitura(db: Session, solicitacao_id: int, atendente: Atendente) -> SolicitacaoMelhoria:
    row = _carregar(db, solicitacao_id)
    _garantir_mesma_org(row, atendente)
    return row


def alterar_status(
    db: Session,
    solicitacao_id: int,
    admin: Atendente,
    data: SolicitacaoMelhoriaStatusUpdate,
) -> SolicitacaoMelhoria:
    if not _is_admin(admin):
        raise HTTPException(status_code=403, detail="Apenas admin pode alterar o status")
    if data.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail="Status inválido")
    row = _carregar(db, solicitacao_id)
    if data.status == "nao_sera_desenvolvida" and not (data.motivo_nao_desenvolvimento or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Informe o motivo quando marcar como não será desenvolvida",
        )
    anterior = row.status
    if anterior == data.status:
        return row
    row.status = data.status
    if data.status == "nao_sera_desenvolvida":
        row.motivo_nao_desenvolvimento = (data.motivo_nao_desenvolvimento or "").strip()
    elif data.motivo_nao_desenvolvimento is not None and data.status != "nao_sera_desenvolvida":
        # não limpa obrigatoriamente — mantém histórico se reabrir
        pass
    msg = mensagem_publica_status(data.status, motivo=row.motivo_nao_desenvolvimento)
    db.add(
        SolicitacaoMelhoriaHistorico(
            solicitacao_id=row.id,
            status_anterior=anterior,
            status_novo=data.status,
            motivo=row.motivo_nao_desenvolvimento if data.status == "nao_sera_desenvolvida" else None,
            atendente_id=admin.id,
            mensagem_publica=msg,
        )
    )
    registrar_audit(
        db,
        "solicitacao_melhoria",
        row.id,
        "status_change",
        admin.id,
        payload={
            "de": anterior,
            "para": data.status,
            "motivo": row.motivo_nao_desenvolvimento if data.status == "nao_sera_desenvolvida" else None,
        },
    )
    db.add(row)
    db.commit()
    return _carregar(db, row.id)


def adicionar_comentario(
    db: Session,
    solicitacao_id: int,
    atendente: Atendente,
    data: SolicitacaoComentarioCreate,
) -> SolicitacaoMelhoria:
    row = _carregar(db, solicitacao_id)
    _garantir_mesma_org(row, atendente)
    is_admin = _is_admin(atendente)

    if not is_admin:
        # Cliente: só comentários públicos nas solicitações da org; bloqueado se status final.
        if not data.publico_cliente:
            raise HTTPException(status_code=403, detail="Não é possível criar notas internas")
        if row.status in STATUS_FINAIS:
            raise HTTPException(
                status_code=400,
                detail="Esta solicitação está encerrada e já não aceita respostas",
            )
        # Só o autor responde (critério #801 “seus próprios”)
        if row.autor_atendente_id != atendente.id:
            raise HTTPException(status_code=403, detail="Só o autor pode responder nesta solicitação")

    if is_admin and data.publico_cliente is False:
        publico = False
    else:
        publico = True if not is_admin else bool(data.publico_cliente)

    db.add(
        SolicitacaoMelhoriaComentario(
            solicitacao_id=row.id,
            corpo=data.corpo.strip(),
            publico_cliente=publico,
            origem="manual",
            autor_atendente_id=atendente.id,
            autor_nome=atendente.nome,
        )
    )
    db.commit()
    return _carregar(db, row.id)


def item_lista(row: SolicitacaoMelhoria, *, incluir_github: bool) -> SolicitacaoMelhoriaListaItem:
    return SolicitacaoMelhoriaListaItem(
        id=row.id,
        tipo=row.tipo,
        titulo=row.titulo,
        status=row.status,
        status_rotulo=rotulo_status(row.status),
        autor_nome=row.autor_nome,
        organizacao_id=row.organizacao_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        github_issue_number=row.github_issue_number if incluir_github else None,
    )
