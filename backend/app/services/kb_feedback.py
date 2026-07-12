"""Feedback público de utilidade em artigos KB (#469)."""

from __future__ import annotations

import hashlib

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.kb import KbArticle, KbArticleFeedbackVote, KbArticleStatus, KbPortalSettings


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def _portal_feedback_habilitado(db: Session, tenant_id: int) -> bool:
    row = db.query(KbPortalSettings).filter(KbPortalSettings.tenant_id == tenant_id).first()
    if not row:
        return True
    return bool(row.feedback_habilitado)


def _artigo_publico_por_slug(db: Session, tenant_id: int, slug: str) -> KbArticle | None:
    return (
        db.query(KbArticle)
        .filter(
            KbArticle.tenant_id == tenant_id,
            KbArticle.slug == slug,
            KbArticle.status == KbArticleStatus.publicado.value,
            KbArticle.interno_only.is_(False),
        )
        .first()
    )


def registrar_feedback_artigo_publico(
    db: Session,
    *,
    tenant_id: int,
    slug: str,
    util: bool,
    ip: str,
) -> dict:
    if not _portal_feedback_habilitado(db, tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Avaliação de artigos desabilitada.")

    article = _artigo_publico_por_slug(db, tenant_id, slug)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artigo não encontrado")

    ip_digest = hash_ip(ip)
    existente = (
        db.query(KbArticleFeedbackVote)
        .filter(
            KbArticleFeedbackVote.article_id == article.id,
            KbArticleFeedbackVote.ip_hash == ip_digest,
        )
        .first()
    )
    if existente:
        return {
            "util": bool(existente.util),
            "ja_avaliado": True,
            "feedback_util_count": int(article.feedback_util_count or 0),
            "feedback_nao_util_count": int(article.feedback_nao_util_count or 0),
        }

    vote = KbArticleFeedbackVote(
        tenant_id=tenant_id,
        article_id=article.id,
        ip_hash=ip_digest,
        util=util,
    )
    db.add(vote)
    if util:
        article.feedback_util_count = int(article.feedback_util_count or 0) + 1
    else:
        article.feedback_nao_util_count = int(article.feedback_nao_util_count or 0) + 1
    db.commit()
    db.refresh(article)

    return {
        "util": util,
        "ja_avaliado": False,
        "feedback_util_count": int(article.feedback_util_count or 0),
        "feedback_nao_util_count": int(article.feedback_nao_util_count or 0),
    }
