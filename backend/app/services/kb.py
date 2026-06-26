"""Helpers da base de conhecimento."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from app.models.kb import KbArticle, KbArticleStatus, KbArticleVersion, KbCategory


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
