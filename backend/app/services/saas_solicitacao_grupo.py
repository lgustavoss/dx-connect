"""Grupo de pedidos iguais na fila SaaS — só ops, nunca vai à instância do cliente."""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.saas_solicitacao_produto import SaasSolicitacaoProduto
from app.schemas.saas_solicitacao import SaasSolicitacaoGrupoMembro
from app.services import saas_solicitacao_ingest as ingest
from app.services.protocolo_mensal import normalizar_protocolo_solicitacao
from app.services.solicitacao_melhoria_copy import rotulo_status


def _gid(row: SaasSolicitacaoProduto) -> int:
    return int(row.grupo_id) if row.grupo_id else int(row.id)


def membros(db: Session, row: SaasSolicitacaoProduto) -> list[SaasSolicitacaoProduto]:
    if not row.grupo_id:
        return [row]
    return (
        db.query(SaasSolicitacaoProduto)
        .options(joinedload(SaasSolicitacaoProduto.cliente))
        .filter(SaasSolicitacaoProduto.grupo_id == row.grupo_id)
        .order_by(SaasSolicitacaoProduto.id.asc())
        .all()
    )


def pesos_por_id(db: Session, rows: list[SaasSolicitacaoProduto]) -> dict[int, tuple[int, int]]:
    """id → (clientes distintos, pedidos no grupo)."""
    out = {r.id: (1, 1) for r in rows}
    gids = {r.grupo_id for r in rows if r.grupo_id}
    if not gids:
        return out
    todos = (
        db.query(SaasSolicitacaoProduto)
        .filter(SaasSolicitacaoProduto.grupo_id.in_(gids))
        .all()
    )
    por: dict[int, list[SaasSolicitacaoProduto]] = defaultdict(list)
    for m in todos:
        if m.grupo_id:
            por[m.grupo_id].append(m)
    for r in rows:
        if not r.grupo_id:
            continue
        ms = por.get(r.grupo_id) or [r]
        slugs = {m.instance_slug for m in ms}
        out[r.id] = (len(slugs), len(ms))
    return out


def membro_read(row: SaasSolicitacaoProduto) -> SaasSolicitacaoGrupoMembro:
    cliente = row.cliente
    return SaasSolicitacaoGrupoMembro(
        id=row.id,
        protocolo=row.protocolo,
        instance_slug=row.instance_slug,
        cliente_nome=cliente.nome if cliente is not None else None,
        titulo=row.titulo,
        status_rotulo=rotulo_status(row.status),
    )


def texto_github_demanda(db: Session, row: SaasSolicitacaoProduto) -> str:
    ms = membros(db, row)
    slugs = sorted({m.instance_slug for m in ms})
    n = len(slugs)
    cab = f"{n} cliente pediu o mesmo." if n == 1 else f"{n} clientes pediram o mesmo."
    protos = ", ".join(m.protocolo for m in ms if m.protocolo)
    linhas = []
    for m in ms:
        nome = m.cliente.nome if m.cliente is not None else m.instance_slug
        proto = m.protocolo or f"id-{m.id}"
        linhas.append(f"- {proto} · {nome} ({m.instance_slug})")
    bloco_proto = f"Protocolos: {protos}" if protos else "Protocolos: (ainda sem número)"
    return "\n".join([cab, "", bloco_proto, "", *linhas])


def _resolver_alvo(
    db: Session,
    *,
    solicitacao_id: int | None,
    protocolo: str | None,
) -> SaasSolicitacaoProduto:
    if solicitacao_id is not None:
        return ingest.obter(db, int(solicitacao_id))
    proto = normalizar_protocolo_solicitacao(protocolo)
    if not proto:
        raise HTTPException(status_code=400, detail="Indique o pedido (id ou protocolo)")
    row = db.query(SaasSolicitacaoProduto).filter(SaasSolicitacaoProduto.protocolo == proto).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return row


def _copiar_github_do_grupo(membros_rows: list[SaasSolicitacaoProduto]) -> None:
    fonte = next((m for m in membros_rows if m.github_issue_url), None)
    if fonte is None:
        return
    for m in membros_rows:
        if m.github_issue_url:
            continue
        m.github_repo = fonte.github_repo
        m.github_issue_number = fonte.github_issue_number
        m.github_issue_url = fonte.github_issue_url


def aplicar_github_no_grupo(
    db: Session,
    row: SaasSolicitacaoProduto,
    *,
    repo: str | None,
    number: int | None,
    url: str | None,
) -> None:
    for m in membros(db, row):
        m.github_repo = repo
        m.github_issue_number = number
        m.github_issue_url = url
        db.add(m)


def vincular(
    db: Session,
    origem_id: int,
    *,
    solicitacao_id: int | None,
    protocolo: str | None,
) -> SaasSolicitacaoProduto:
    a = ingest.obter(db, origem_id)
    b = _resolver_alvo(db, solicitacao_id=solicitacao_id, protocolo=protocolo)
    if a.id == b.id:
        raise HTTPException(status_code=400, detail="Não dá para vincular um pedido a si próprio")
    ga, gb = _gid(a), _gid(b)
    keep = min(ga, gb)
    ids_merge = {ga, gb}
    candidatos = (
        db.query(SaasSolicitacaoProduto)
        .options(joinedload(SaasSolicitacaoProduto.cliente))
        .filter(
            or_(
                SaasSolicitacaoProduto.grupo_id.in_(ids_merge),
                SaasSolicitacaoProduto.id.in_(ids_merge),
            )
        )
        .all()
    )
    for r in candidatos:
        r.grupo_id = keep
        db.add(r)
    _copiar_github_do_grupo(candidatos)
    db.commit()
    return ingest.obter(db, a.id)


def desvincular(db: Session, origem_id: int, membro_id: int) -> SaasSolicitacaoProduto:
    a = ingest.obter(db, origem_id)
    b = ingest.obter(db, membro_id)
    gid = a.grupo_id
    if not gid or b.grupo_id != gid:
        raise HTTPException(status_code=400, detail="Estes pedidos não estão no mesmo grupo")
    b.grupo_id = None
    db.add(b)
    rest = (
        db.query(SaasSolicitacaoProduto)
        .filter(SaasSolicitacaoProduto.grupo_id == gid)
        .all()
    )
    if len(rest) <= 1:
        for r in rest:
            r.grupo_id = None
            db.add(r)
    db.commit()
    return ingest.obter(db, a.id)
