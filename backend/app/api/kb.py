from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, obter_atendente_atual
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.kb import KbArticle, KbArticleStatus, KbCategory
from app.schemas.kb import (
    KbArticleBrief,
    KbArticleCreate,
    KbArticleRead,
    KbArticleUpdate,
    KbCategoryCreate,
    KbCategoryRead,
    KbCategoryUpdate,
)
from app.schemas.lista_paginada import ListaPaginada
from app.services.kb import registrar_versao_artigo, slug_disponivel

router = APIRouter(prefix="/kb", tags=["kb"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarKbArtigosPor(str, Enum):
    titulo = "titulo"
    status = "status"
    updated_at = "updated_at"
    published_at = "published_at"


def _status_str(article: KbArticle) -> str:
    if isinstance(article.status, KbArticleStatus):
        return article.status.value
    return str(article.status or KbArticleStatus.rascunho.value)


def _article_read(article: KbArticle) -> KbArticleRead:
    return KbArticleRead(
        id=article.id,
        titulo=article.titulo,
        slug=article.slug,
        category_id=article.category_id,
        category_nome=article.category.nome if article.category else None,
        status=_status_str(article),
        conteudo_markdown=article.conteudo_markdown or "",
        autor_atendente_id=article.autor_atendente_id,
        autor_nome=article.autor.nome if article.autor else None,
        published_at=article.published_at,
        archived_at=article.archived_at,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _article_brief(article: KbArticle) -> KbArticleBrief:
    return KbArticleBrief(
        id=article.id,
        titulo=article.titulo,
        slug=article.slug,
        category_id=article.category_id,
        category_nome=article.category.nome if article.category else None,
        status=_status_str(article),
        autor_nome=article.autor.nome if article.autor else None,
        published_at=article.published_at,
        updated_at=article.updated_at,
    )


def _category_read(row: KbCategory, artigos_count: int = 0) -> KbCategoryRead:
    return KbCategoryRead(
        id=row.id,
        nome=row.nome,
        slug=row.slug,
        ordem=int(row.ordem or 0),
        parent_id=row.parent_id,
        artigos_count=artigos_count,
    )


def _get_category_or_404(db: Session, tenant_id: int, category_id: int) -> KbCategory:
    row = db.query(KbCategory).filter(KbCategory.id == category_id, KbCategory.tenant_id == tenant_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    return row


def _get_article_or_404(db: Session, tenant_id: int, article_id: int) -> KbArticle:
    row = (
        db.query(KbArticle)
        .options(joinedload(KbArticle.category), joinedload(KbArticle.autor))
        .filter(KbArticle.id == article_id, KbArticle.tenant_id == tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artigo não encontrado")
    return row


# --- Categorias (admin) ---


@router.get("/categories", response_model=list[KbCategoryRead])
def listar_categorias(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    rows = (
        db.query(KbCategory, func.count(KbArticle.id).label("artigos_count"))
        .outerjoin(KbArticle, KbArticle.category_id == KbCategory.id)
        .filter(KbCategory.tenant_id == atendente.tenant_id)
        .group_by(KbCategory.id)
        .order_by(KbCategory.ordem.asc(), KbCategory.nome.asc(), KbCategory.id.asc())
        .all()
    )
    return [_category_read(cat, int(cnt or 0)) for cat, cnt in rows]


@router.post("/categories", response_model=KbCategoryRead, status_code=201)
def criar_categoria(
    data: KbCategoryCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    if data.parent_id is not None:
        _get_category_or_404(db, atendente.tenant_id, data.parent_id)
    base_slug = data.slug.strip() if data.slug and data.slug.strip() else data.nome
    slug = slug_disponivel(db, KbCategory, atendente.tenant_id, base_slug)
    row = KbCategory(
        tenant_id=atendente.tenant_id,
        nome=data.nome.strip(),
        slug=slug,
        ordem=data.ordem,
        parent_id=data.parent_id,
    )
    db.add(row)
    db.flush()
    registrar_audit(db, "kb_category", row.id, "create", atendente.id, payload={"nome": row.nome, "slug": row.slug})
    db.commit()
    db.refresh(row)
    return _category_read(row, 0)


@router.patch("/categories/{category_id}", response_model=KbCategoryRead)
def atualizar_categoria(
    category_id: int,
    data: KbCategoryUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_category_or_404(db, atendente.tenant_id, category_id)
    update = data.model_dump(exclude_unset=True)
    if "parent_id" in update and update["parent_id"] is not None:
        if update["parent_id"] == category_id:
            raise HTTPException(status_code=400, detail="Categoria não pode ser pai de si mesma.")
        _get_category_or_404(db, atendente.tenant_id, update["parent_id"])
    if "nome" in update:
        row.nome = update["nome"].strip()
    if "ordem" in update:
        row.ordem = update["ordem"]
    if "parent_id" in update:
        row.parent_id = update["parent_id"]
    if "slug" in update and update["slug"]:
        row.slug = slug_disponivel(db, KbCategory, atendente.tenant_id, update["slug"], exclude_id=row.id)
    elif "nome" in update and "slug" not in update:
        row.slug = slug_disponivel(db, KbCategory, atendente.tenant_id, row.nome, exclude_id=row.id)
    db.flush()
    cnt = db.query(func.count(KbArticle.id)).filter(KbArticle.category_id == row.id).scalar() or 0
    registrar_audit(db, "kb_category", row.id, "update", atendente.id, payload={"nome": row.nome})
    db.commit()
    db.refresh(row)
    return _category_read(row, int(cnt))


@router.delete("/categories/{category_id}", status_code=204)
def excluir_categoria(
    category_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_category_or_404(db, atendente.tenant_id, category_id)
    db.query(KbArticle).filter(KbArticle.category_id == row.id).update({KbArticle.category_id: None})
    registrar_audit(db, "kb_category", row.id, "delete", atendente.id, payload={"nome": row.nome})
    db.delete(row)
    db.commit()


# --- Artigos admin ---


@router.get("/articles", response_model=ListaPaginada[KbArticleBrief])
def listar_artigos_admin(
    busca: str | None = Query(None),
    status_filtro: str | None = Query(None, alias="status"),
    category_id: int | None = Query(None, ge=1),
    incluir_arquivados: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarKbArtigosPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.desc),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    q = (
        db.query(KbArticle)
        .options(joinedload(KbArticle.category), joinedload(KbArticle.autor))
        .filter(KbArticle.tenant_id == atendente.tenant_id)
    )
    if not incluir_arquivados:
        q = q.filter(KbArticle.status != KbArticleStatus.arquivado.value)
    if status_filtro:
        q = q.filter(KbArticle.status == status_filtro)
    if category_id is not None:
        q = q.filter(KbArticle.category_id == category_id)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(KbArticle.titulo.ilike(term), KbArticle.conteudo_markdown.ilike(term)))
    total = q.count()
    if ordenar_por is None:
        order_cols = [KbArticle.updated_at.desc(), KbArticle.id.desc()]
    elif ordenar_por == OrdenarKbArtigosPor.titulo:
        order_cols = [expr_ordem(KbArticle.titulo, ordem), expr_ordem(KbArticle.id, ordem)]
    elif ordenar_por == OrdenarKbArtigosPor.status:
        order_cols = [expr_ordem(KbArticle.status, ordem), expr_ordem(KbArticle.id, ordem)]
    elif ordenar_por == OrdenarKbArtigosPor.published_at:
        order_cols = [expr_ordem(KbArticle.published_at, ordem), expr_ordem(KbArticle.id, ordem)]
    else:
        order_cols = [expr_ordem(KbArticle.updated_at, ordem), expr_ordem(KbArticle.id, ordem)]
    rows = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_article_brief(r) for r in rows], total=total)


@router.get("/articles/consulta", response_model=list[KbArticleBrief])
def consultar_artigos_publicados(
    busca: str | None = Query(None, description="Busca em título e conteúdo (ILIKE)"),
    category_id: int | None = Query(None, ge=1),
    limit: int = Query(25, ge=1, le=50),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = (
        db.query(KbArticle)
        .options(joinedload(KbArticle.category), joinedload(KbArticle.autor))
        .filter(
            KbArticle.tenant_id == atendente.tenant_id,
            KbArticle.status == KbArticleStatus.publicado.value,
        )
    )
    if category_id is not None:
        q = q.filter(KbArticle.category_id == category_id)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(KbArticle.titulo.ilike(term), KbArticle.conteudo_markdown.ilike(term)))
    rows = q.order_by(KbArticle.titulo.asc(), KbArticle.id.asc()).limit(limit).all()
    return [_article_brief(r) for r in rows]


@router.get("/articles/publicados/{article_id}", response_model=KbArticleRead)
def ler_artigo_publicado(
    article_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = _get_article_or_404(db, atendente.tenant_id, article_id)
    if _status_str(row) != KbArticleStatus.publicado.value:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    return _article_read(row)


@router.get("/articles/{article_id}", response_model=KbArticleRead)
def obter_artigo(
    article_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    return _article_read(_get_article_or_404(db, atendente.tenant_id, article_id))


@router.post("/articles", response_model=KbArticleRead, status_code=201)
def criar_artigo(
    data: KbArticleCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    if data.category_id is not None:
        _get_category_or_404(db, atendente.tenant_id, data.category_id)
    base_slug = data.slug.strip() if data.slug and data.slug.strip() else data.titulo
    slug = slug_disponivel(db, KbArticle, atendente.tenant_id, base_slug)
    row = KbArticle(
        tenant_id=atendente.tenant_id,
        titulo=data.titulo.strip(),
        slug=slug,
        category_id=data.category_id,
        status=KbArticleStatus.rascunho,
        conteudo_markdown=data.conteudo_markdown or "",
        autor_atendente_id=atendente.id,
    )
    db.add(row)
    db.flush()
    registrar_versao_artigo(db, row, atendente.id)
    registrar_audit(db, "kb_article", row.id, "create", atendente.id, payload={"titulo": row.titulo, "slug": row.slug})
    db.commit()
    db.refresh(row)
    row = _get_article_or_404(db, atendente.tenant_id, row.id)
    return _article_read(row)


@router.patch("/articles/{article_id}", response_model=KbArticleRead)
def atualizar_artigo(
    article_id: int,
    data: KbArticleUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_article_or_404(db, atendente.tenant_id, article_id)
    if _status_str(row) == KbArticleStatus.arquivado.value:
        raise HTTPException(status_code=400, detail="Artigo arquivado não pode ser editado.")
    update = data.model_dump(exclude_unset=True)
    if "category_id" in update and update["category_id"] is not None:
        _get_category_or_404(db, atendente.tenant_id, update["category_id"])
    if "titulo" in update:
        row.titulo = update["titulo"].strip()
    if "conteudo_markdown" in update:
        row.conteudo_markdown = update["conteudo_markdown"] or ""
    if "category_id" in update:
        row.category_id = update["category_id"]
    if "slug" in update and update["slug"]:
        row.slug = slug_disponivel(db, KbArticle, atendente.tenant_id, update["slug"], exclude_id=row.id)
    elif "titulo" in update and "slug" not in update:
        row.slug = slug_disponivel(db, KbArticle, atendente.tenant_id, row.titulo, exclude_id=row.id)
    row.autor_atendente_id = atendente.id
    db.flush()
    registrar_versao_artigo(db, row, atendente.id)
    registrar_audit(db, "kb_article", row.id, "update", atendente.id, payload={"titulo": row.titulo})
    db.commit()
    row = _get_article_or_404(db, atendente.tenant_id, row.id)
    return _article_read(row)


@router.post("/articles/{article_id}/publish", response_model=KbArticleRead)
def publicar_artigo(
    article_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_article_or_404(db, atendente.tenant_id, article_id)
    if not (row.titulo or "").strip():
        raise HTTPException(status_code=400, detail="Informe o título antes de publicar.")
    row.status = KbArticleStatus.publicado
    row.published_at = datetime.now(timezone.utc)
    row.archived_at = None
    row.autor_atendente_id = atendente.id
    db.flush()
    registrar_versao_artigo(db, row, atendente.id)
    registrar_audit(db, "kb_article", row.id, "publish", atendente.id, payload={"titulo": row.titulo})
    db.commit()
    row = _get_article_or_404(db, atendente.tenant_id, row.id)
    return _article_read(row)


@router.post("/articles/{article_id}/archive", response_model=KbArticleRead)
def arquivar_artigo(
    article_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_article_or_404(db, atendente.tenant_id, article_id)
    row.status = KbArticleStatus.arquivado
    row.archived_at = datetime.now(timezone.utc)
    row.autor_atendente_id = atendente.id
    db.flush()
    registrar_versao_artigo(db, row, atendente.id)
    registrar_audit(db, "kb_article", row.id, "archive", atendente.id, payload={"titulo": row.titulo})
    db.commit()
    row = _get_article_or_404(db, atendente.tenant_id, row.id)
    return _article_read(row)
