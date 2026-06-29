"""Helpers da base de conhecimento."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session, joinedload

from app.models.kb import KbArticle, KbArticleStatus, KbArticleVersion, KbCategory, KbArticleMotivoLink


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.strip())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^\w\s-]", "", ascii_text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return (slug[:80] if slug else "item")


def slug_disponivel(
    db: Session,
    model: type[KbCategory] | type[KbArticle],
    tenant_id: int,
    base: str,
    *,
    exclude_id: int | None = None,
) -> str:
    candidato = slugify(base)
    sufixo = 2
    while True:
        q = db.query(model.id).filter(model.tenant_id == tenant_id, model.slug == candidato)
        if exclude_id is not None:
            q = q.filter(model.id != exclude_id)
        if q.first() is None:
            return candidato
        candidato = f"{slugify(base)[:70]}-{sufixo}"
        sufixo += 1


def registrar_versao_artigo(db: Session, article: KbArticle, atendente_id: int | None) -> None:
    status_val = article.status.value if isinstance(article.status, KbArticleStatus) else str(article.status)
    db.add(
        KbArticleVersion(
            article_id=article.id,
            titulo=article.titulo,
            conteudo_markdown=article.conteudo_markdown or "",
            status=status_val,
            autor_atendente_id=atendente_id,
        )
    )


_MAX_SUGESTOES = 5


def listar_artigos_sugeridos(
    db: Session,
    tenant_id: int,
    *,
    motivo_id: int | None = None,
    natureza_id: int | None = None,
    incluir_interno_only: bool = True,
) -> list[KbArticle]:
    """Artigos publicados vinculados ao motivo e/ou natureza (máx. 5)."""
    from app.models.ticket_classificacao import TicketMotivo

    if motivo_id is None and natureza_id is None:
        return []

    natureza_filtro = natureza_id
    if motivo_id is not None:
        motivo = (
            db.query(TicketMotivo)
            .filter(TicketMotivo.id == motivo_id, TicketMotivo.ativo.is_(True))
            .first()
        )
        if not motivo:
            return []
        natureza_filtro = motivo.natureza_id

    link_filters = []
    if motivo_id is not None:
        link_filters.append(KbArticleMotivoLink.motivo_id == motivo_id)
    if natureza_filtro is not None:
        link_filters.append(
            (KbArticleMotivoLink.motivo_id.is_(None))
            & (KbArticleMotivoLink.natureza_id == natureza_filtro)
        )

    from sqlalchemy import or_

    q = (
        db.query(KbArticle, KbArticleMotivoLink.ordem)
        .join(KbArticleMotivoLink, KbArticleMotivoLink.article_id == KbArticle.id)
        .options(joinedload(KbArticle.category).joinedload(KbCategory.parent))
        .filter(
            KbArticle.tenant_id == tenant_id,
            KbArticleMotivoLink.tenant_id == tenant_id,
            KbArticle.status == KbArticleStatus.publicado.value,
            or_(*link_filters),
        )
    )
    if not incluir_interno_only:
        q = q.filter(KbArticle.interno_only.is_(False))

    rows = q.order_by(KbArticleMotivoLink.ordem.asc(), KbArticle.titulo.asc(), KbArticle.id.asc()).all()

    vistos: set[int] = set()
    resultado: list[KbArticle] = []
    for art, _ordem in rows:
        if art.id in vistos:
            continue
        vistos.add(art.id)
        resultado.append(art)
        if len(resultado) >= _MAX_SUGESTOES:
            break
    return resultado
