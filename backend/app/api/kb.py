from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, obter_atendente_atual
from app.core.kb_public_rate_limit import (
    check_kb_public_chat_rate_limit,
    check_kb_public_feedback_rate_limit,
    check_kb_public_rate_limit,
)
from app.core.tenant_context import TenantIdDep
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.empresa_sistema import EmpresaSistema
from app.models.kb import KbArticle, KbArticleMotivoLink, KbArticleStatus, KbArticleVersion, KbCategory, KbPortalSettings
from app.models.portal_chat import PortalChat, PortalMensagem
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.schemas.kb import (
    KbArticleBrief,
    KbArticleCreate,
    KbArticleFeedbackBody,
    KbArticleFeedbackRead,
    KbArticleRead,
    KbArticleUpdate,
    KbArticleVersionDetail,
    KbArticleVersionRead,
    KbArticleMotivoLinkItem,
    KbArticleMotivoLinksUpdate,
    KbCategoryCreate,
    KbCategoryRead,
    KbCategoryReorder,
    KbCategoryUpdate,
    KbImageUploadResponse,
    KbPortalSettingsRead,
    KbPortalSettingsUpdate,
    KbPublicBrandingRead,
)
from app.schemas.portal_chat import (
    PortalChatMensagemCreate,
    PortalChatMensagemRead,
    PortalChatPublicSessionRead,
    PortalChatRead,
    PortalChatSessionCreate,
    PortalChatSessionRead,
)
from app.schemas.lista_paginada import ListaPaginada
from app.services.instancia_branding import branding_kb_publico as montar_branding_kb_publico
from app.services.kb import listar_artigos_sugeridos, registrar_versao_artigo, slug_disponivel
from app.services.kb_feedback import registrar_feedback_artigo_publico
from app.core.login_protection import client_ip
from app.services.system_logo_storage import caminho_absoluto_logo
from app.services.kb_media_storage import caminho_absoluto_imagem, gravar_imagem_bytes
from app.config import settings
from app.services.portal_chat import (
    VISITOR_TOKEN_HEADER,
    chat_por_token,
    criar_ou_retomar_sessao_visitante,
    listar_mensagens_chat,
    portal_chat_habilitado,
    registrar_mensagem_midia_visitante,
    registrar_mensagem_visitante,
    serializar_chat,
)
from app.services.realtime_emit import emit_portal_chat_fila_from_model, emit_portal_chat_mensagem_from_models
from app.services.whatsapp_media_storage import caminho_absoluto_arquivo, gravar_bytes_em_disco

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


def _category_nome_exibicao(cat: KbCategory | None) -> str | None:
    if not cat:
        return None
    if cat.parent_id and cat.parent:
        return f"{cat.parent.nome} › {cat.nome}"
    return cat.nome


def _article_read(article: KbArticle) -> KbArticleRead:
    return KbArticleRead(
        id=article.id,
        titulo=article.titulo,
        slug=article.slug,
        category_id=article.category_id,
        category_nome=_category_nome_exibicao(article.category),
        status=_status_str(article),
        conteudo_markdown=article.conteudo_markdown or "",
        interno_only=bool(article.interno_only),
        autor_atendente_id=article.autor_atendente_id,
        autor_nome=article.autor.nome if article.autor else None,
        published_at=article.published_at,
        archived_at=article.archived_at,
        feedback_util_count=int(article.feedback_util_count or 0),
        feedback_nao_util_count=int(article.feedback_nao_util_count or 0),
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _article_brief(article: KbArticle) -> KbArticleBrief:
    return KbArticleBrief(
        id=article.id,
        titulo=article.titulo,
        slug=article.slug,
        category_id=article.category_id,
        category_nome=_category_nome_exibicao(article.category),
        status=_status_str(article),
        interno_only=bool(article.interno_only),
        autor_nome=article.autor.nome if article.autor else None,
        published_at=article.published_at,
        updated_at=article.updated_at,
    )


def _versao_read(row: KbArticleVersion) -> KbArticleVersionRead:
    return KbArticleVersionRead(
        id=row.id,
        article_id=row.article_id,
        titulo=row.titulo,
        status=row.status,
        autor_atendente_id=row.autor_atendente_id,
        autor_nome=row.autor.nome if row.autor else None,
        created_at=row.created_at,
    )


def _versao_detail(row: KbArticleVersion) -> KbArticleVersionDetail:
    base = _versao_read(row)
    return KbArticleVersionDetail(
        **base.model_dump(),
        conteudo_markdown=row.conteudo_markdown or "",
    )


def _category_read(
    row: KbCategory,
    artigos_count: int = 0,
    *,
    parent_nome: str | None = None,
) -> KbCategoryRead:
    pn = parent_nome
    if pn is None and row.parent is not None:
        pn = row.parent.nome
    return KbCategoryRead(
        id=row.id,
        nome=row.nome,
        slug=row.slug,
        ordem=int(row.ordem or 0),
        parent_id=row.parent_id,
        parent_nome=pn,
        artigos_count=artigos_count,
    )


def _category_reads_agregadas(
    rows: list[tuple[KbCategory, int]],
) -> list[KbCategoryRead]:
    """Monta resposta de listagens com GROUP BY (sem joinedload do pai — incompatível no Postgres)."""
    nomes = {cat.id: cat.nome for cat, _ in rows}
    return [
        _category_read(
            cat,
            int(cnt or 0),
            parent_nome=nomes.get(cat.parent_id) if cat.parent_id else None,
        )
        for cat, cnt in rows
    ]


def _assert_parent_categoria_valida(
    db: Session,
    tenant_id: int,
    parent_id: int | None,
    *,
    categoria_id: int | None = None,
) -> None:
    if parent_id is None:
        return
    if categoria_id is not None and parent_id == categoria_id:
        raise HTTPException(status_code=400, detail="Categoria não pode ser pai de si mesma.")
    parent = _get_category_or_404(db, tenant_id, parent_id)
    if parent.parent_id is not None:
        raise HTTPException(status_code=400, detail="Só é permitido um nível de subcategoria.")
    if categoria_id is not None:
        filhos = (
            db.query(func.count(KbCategory.id))
            .filter(KbCategory.parent_id == categoria_id, KbCategory.tenant_id == tenant_id)
            .scalar()
            or 0
        )
        if int(filhos) > 0:
            raise HTTPException(
                status_code=400,
                detail="Categoria com subcategorias não pode virar subcategoria.",
            )


def _get_category_or_404(db: Session, tenant_id: int, category_id: int) -> KbCategory:
    row = db.query(KbCategory).filter(KbCategory.id == category_id, KbCategory.tenant_id == tenant_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    return row


def _get_article_or_404(db: Session, tenant_id: int, article_id: int) -> KbArticle:
    row = (
        db.query(KbArticle)
        .options(joinedload(KbArticle.category).joinedload(KbCategory.parent), joinedload(KbArticle.autor))
        .filter(KbArticle.id == article_id, KbArticle.tenant_id == tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artigo não encontrado")
    return row


def _motivo_link_read(link: KbArticleMotivoLink) -> KbArticleMotivoLinkItem:
    return KbArticleMotivoLinkItem(
        id=link.id,
        motivo_id=link.motivo_id,
        natureza_id=link.natureza_id,
        ordem=int(link.ordem or 0),
        motivo_nome=link.motivo.nome if link.motivo else None,
        natureza_nome=link.natureza.nome if link.natureza else None,
    )


def _assert_motivo_link_item_valido(db: Session, item: KbArticleMotivoLinkItem) -> tuple[int | None, int | None]:
    if item.motivo_id is not None and item.natureza_id is not None:
        raise HTTPException(status_code=400, detail="Informe motivo ou natureza, não ambos no mesmo vínculo.")
    if item.motivo_id is None and item.natureza_id is None:
        raise HTTPException(status_code=400, detail="Cada vínculo precisa de motivo ou natureza.")
    if item.motivo_id is not None:
        mot = db.query(TicketMotivo).filter(TicketMotivo.id == item.motivo_id, TicketMotivo.ativo.is_(True)).first()
        if not mot:
            raise HTTPException(status_code=400, detail=f"Motivo {item.motivo_id} não encontrado.")
        return item.motivo_id, None
    nat = db.query(TicketNatureza).filter(TicketNatureza.id == item.natureza_id, TicketNatureza.ativo.is_(True)).first()
    if not nat:
        raise HTTPException(status_code=400, detail=f"Natureza {item.natureza_id} não encontrada.")
    return None, item.natureza_id


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
    return _category_reads_agregadas(rows)


@router.post("/categories", response_model=KbCategoryRead, status_code=201)
def criar_categoria(
    data: KbCategoryCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    if data.parent_id is not None:
        _assert_parent_categoria_valida(db, atendente.tenant_id, data.parent_id)
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
    row = (
        db.query(KbCategory)
        .options(joinedload(KbCategory.parent))
        .filter(KbCategory.id == row.id, KbCategory.tenant_id == atendente.tenant_id)
        .first()
    )
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
    if "parent_id" in update:
        _assert_parent_categoria_valida(
            db,
            atendente.tenant_id,
            update["parent_id"],
            categoria_id=category_id,
        )
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
    row = (
        db.query(KbCategory)
        .options(joinedload(KbCategory.parent))
        .filter(KbCategory.id == row.id, KbCategory.tenant_id == atendente.tenant_id)
        .first()
    )
    cnt = db.query(func.count(KbArticle.id)).filter(KbArticle.category_id == row.id).scalar() or 0
    return _category_read(row, int(cnt))


@router.delete("/categories/{category_id}", status_code=204)
def excluir_categoria(
    category_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_category_or_404(db, atendente.tenant_id, category_id)
    subcategorias = (
        db.query(func.count(KbCategory.id))
        .filter(KbCategory.parent_id == row.id, KbCategory.tenant_id == atendente.tenant_id)
        .scalar()
        or 0
    )
    if int(subcategorias) > 0:
        raise HTTPException(
            status_code=400,
            detail="Exclua ou mova as subcategorias antes de excluir esta categoria.",
        )
    db.query(KbArticle).filter(KbArticle.category_id == row.id).update({KbArticle.category_id: None})
    registrar_audit(db, "kb_category", row.id, "delete", atendente.id, payload={"nome": row.nome})
    db.delete(row)
    db.commit()


@router.put("/categories/reorder", response_model=list[KbCategoryRead])
def reordenar_categorias(
    data: KbCategoryReorder,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    ids = [item.id for item in data.items]
    rows = (
        db.query(KbCategory)
        .filter(KbCategory.tenant_id == atendente.tenant_id, KbCategory.id.in_(ids))
        .all()
    )
    if len(rows) != len(ids):
        raise HTTPException(status_code=400, detail="Uma ou mais categorias não encontradas.")
    ordem_por_id = {item.id: item.ordem for item in data.items}
    for row in rows:
        row.ordem = ordem_por_id[row.id]
    registrar_audit(db, "kb_category", 0, "reorder", atendente.id)
    db.commit()
    listed = (
        db.query(KbCategory, func.count(KbArticle.id).label("artigos_count"))
        .outerjoin(KbArticle, KbArticle.category_id == KbCategory.id)
        .filter(KbCategory.tenant_id == atendente.tenant_id)
        .group_by(KbCategory.id)
        .order_by(KbCategory.ordem.asc(), KbCategory.nome.asc(), KbCategory.id.asc())
        .all()
    )
    return _category_reads_agregadas(listed)


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
        .options(joinedload(KbArticle.category).joinedload(KbCategory.parent), joinedload(KbArticle.autor))
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
        .options(joinedload(KbArticle.category).joinedload(KbCategory.parent), joinedload(KbArticle.autor))
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


@router.get("/suggestions", response_model=list[KbArticleBrief])
def sugestoes_artigos(
    motivo_id: int | None = Query(None, ge=1),
    natureza_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    if motivo_id is None and natureza_id is None:
        raise HTTPException(status_code=400, detail="Informe motivo_id ou natureza_id.")
    arts = listar_artigos_sugeridos(
        db,
        atendente.tenant_id,
        motivo_id=motivo_id,
        natureza_id=natureza_id,
        incluir_interno_only=True,
    )
    return [_article_brief(a) for a in arts]


@router.get("/articles/{article_id}/motivo-links", response_model=list[KbArticleMotivoLinkItem])
def listar_vinculos_motivo_artigo(
    article_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _get_article_or_404(db, atendente.tenant_id, article_id)
    rows = (
        db.query(KbArticleMotivoLink)
        .options(joinedload(KbArticleMotivoLink.motivo), joinedload(KbArticleMotivoLink.natureza))
        .filter(
            KbArticleMotivoLink.tenant_id == atendente.tenant_id,
            KbArticleMotivoLink.article_id == article_id,
        )
        .order_by(KbArticleMotivoLink.ordem.asc(), KbArticleMotivoLink.id.asc())
        .all()
    )
    return [_motivo_link_read(r) for r in rows]


@router.put("/articles/{article_id}/motivo-links", response_model=list[KbArticleMotivoLinkItem])
def atualizar_vinculos_motivo_artigo(
    article_id: int,
    data: KbArticleMotivoLinksUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _get_article_or_404(db, atendente.tenant_id, article_id)
    vistos_motivo: set[int] = set()
    vistos_natureza: set[int] = set()
    novos: list[KbArticleMotivoLink] = []
    for idx, item in enumerate(data.links):
        motivo_id, nat_id = _assert_motivo_link_item_valido(db, item)
        if motivo_id is not None:
            if motivo_id in vistos_motivo:
                raise HTTPException(status_code=400, detail="Motivo duplicado na lista de vínculos.")
            vistos_motivo.add(motivo_id)
        else:
            assert nat_id is not None
            if nat_id in vistos_natureza:
                raise HTTPException(status_code=400, detail="Natureza duplicada na lista de vínculos.")
            vistos_natureza.add(nat_id)
        novos.append(
            KbArticleMotivoLink(
                tenant_id=atendente.tenant_id,
                article_id=article_id,
                motivo_id=motivo_id,
                natureza_id=nat_id,
                ordem=item.ordem if item.ordem is not None else idx,
            )
        )
    db.query(KbArticleMotivoLink).filter(
        KbArticleMotivoLink.tenant_id == atendente.tenant_id,
        KbArticleMotivoLink.article_id == article_id,
    ).delete(synchronize_session=False)
    for row in novos:
        db.add(row)
    registrar_audit(
        db,
        "kb_article",
        article_id,
        "motivo_links_update",
        atendente.id,
        payload={"count": len(novos)},
    )
    db.commit()
    rows = (
        db.query(KbArticleMotivoLink)
        .options(joinedload(KbArticleMotivoLink.motivo), joinedload(KbArticleMotivoLink.natureza))
        .filter(
            KbArticleMotivoLink.tenant_id == atendente.tenant_id,
            KbArticleMotivoLink.article_id == article_id,
        )
        .order_by(KbArticleMotivoLink.ordem.asc(), KbArticleMotivoLink.id.asc())
        .all()
    )
    return [_motivo_link_read(r) for r in rows]


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
        interno_only=data.interno_only,
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
    if "interno_only" in update:
        row.interno_only = bool(update["interno_only"])
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


@router.get("/articles/{article_id}/versions", response_model=list[KbArticleVersionRead])
def listar_versoes_artigo(
    article_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _get_article_or_404(db, atendente.tenant_id, article_id)
    rows = (
        db.query(KbArticleVersion)
        .options(joinedload(KbArticleVersion.autor))
        .filter(KbArticleVersion.article_id == article_id)
        .order_by(KbArticleVersion.id.desc())
        .limit(50)
        .all()
    )
    return [_versao_read(r) for r in rows]


@router.get("/articles/{article_id}/versions/{version_id}", response_model=KbArticleVersionDetail)
def obter_versao_artigo(
    article_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _get_article_or_404(db, atendente.tenant_id, article_id)
    row = (
        db.query(KbArticleVersion)
        .options(joinedload(KbArticleVersion.autor))
        .filter(KbArticleVersion.id == version_id, KbArticleVersion.article_id == article_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    return _versao_detail(row)


@router.post("/images", response_model=KbImageUploadResponse, status_code=201)
async def upload_imagem_kb(
    file: UploadFile = File(...),
    atendente: Atendente = Depends(exigir_admin),
):
    data = await file.read()
    saved = gravar_imagem_bytes(data, file.content_type)
    if not saved:
        raise HTTPException(status_code=400, detail="Imagem inválida ou excede o tamanho máximo (2 MB).")
    filename, _ = saved
    return KbImageUploadResponse(url=f"/v1/kb/images/{filename}", filename=filename)


@router.get("/images/{filename}")
def servir_imagem_kb(
    filename: str,
    request: Request,
    _tenant_id: TenantIdDep,
):
    check_kb_public_rate_limit(request)
    p = caminho_absoluto_imagem(filename)
    if not p:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    ext = p.suffix.lower()
    mt = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(p),
        media_type=mt,
        filename=p.name,
        headers={"Cache-Control": "public, max-age=86400"},
    )


# --- Leitura pública (portal / integrações; #295) ---


def _public_cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "public, max-age=60"


def _empresa_sistema_row(db: Session) -> EmpresaSistema | None:
    return db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()


def _portal_settings_row(db: Session, tenant_id: int) -> KbPortalSettings | None:
    return db.query(KbPortalSettings).filter(KbPortalSettings.tenant_id == tenant_id).first()


def _get_or_create_portal_settings(db: Session, tenant_id: int) -> KbPortalSettings:
    row = _portal_settings_row(db, tenant_id)
    if row:
        return row
    row = KbPortalSettings(tenant_id=tenant_id)
    db.add(row)
    db.flush()
    return row


def _portal_settings_read(row: KbPortalSettings) -> KbPortalSettingsRead:
    cor_header = row.cor_header or "#0B2D4A"
    return KbPortalSettingsRead(
        portal_titulo=row.portal_titulo,
        texto_boas_vindas=row.texto_boas_vindas,
        cor_header=cor_header,
        cor_sidebar=(row.cor_sidebar or cor_header),
        cor_primaria=row.cor_primaria or "#0D9488",
        cor_texto_header=row.cor_texto_header or "#FFFFFF",
        cor_texto_corpo=row.cor_texto_corpo or "#0F172A",
        cor_fundo=row.cor_fundo or "#F8FAFC",
        cor_link=row.cor_link,
        exibir_marca_deskrudder=bool(row.exibir_marca_deskrudder),
        feedback_habilitado=bool(row.feedback_habilitado),
        chat_habilitado=bool(row.chat_habilitado),
        chat_setor_id=row.chat_setor_id,
        chat_texto_boas_vindas=row.chat_texto_boas_vindas,
        public_url_preview="/kb",
    )


@router.get("/portal-settings", response_model=KbPortalSettingsRead)
def obter_portal_settings(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_or_create_portal_settings(db, atendente.tenant_id)
    db.commit()
    return _portal_settings_read(row)


@router.put("/portal-settings", response_model=KbPortalSettingsRead)
def atualizar_portal_settings(
    data: KbPortalSettingsUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = _get_or_create_portal_settings(db, atendente.tenant_id)
    update = data.model_dump(exclude_unset=True)
    if "portal_titulo" in update and update["portal_titulo"] is not None:
        update["portal_titulo"] = update["portal_titulo"].strip() or None
    if "texto_boas_vindas" in update and update["texto_boas_vindas"] is not None:
        update["texto_boas_vindas"] = update["texto_boas_vindas"].strip() or None
    if "chat_texto_boas_vindas" in update and update["chat_texto_boas_vindas"] is not None:
        update["chat_texto_boas_vindas"] = update["chat_texto_boas_vindas"].strip() or None
    if update.get("chat_habilitado") and not update.get("chat_setor_id") and row.chat_setor_id is None:
        if "chat_setor_id" not in update or update.get("chat_setor_id") is None:
            raise HTTPException(
                status_code=400,
                detail="Selecione o setor de atendimento para habilitar o chat do portal.",
            )
    for key, val in update.items():
        setattr(row, key, val)
    registrar_audit(db, "kb_portal_settings", row.id, "update", atendente.id, payload=update)
    db.commit()
    db.refresh(row)
    return _portal_settings_read(row)


@router.get("/public/branding", response_model=KbPublicBrandingRead)
def branding_kb_publico_endpoint(
    request: Request,
    response: Response,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    _ = tenant_id
    out = montar_branding_kb_publico(db, tenant_id)
    _public_cache_headers(response)
    return out


@router.get("/public/logo")
def logo_kb_publico(
    request: Request,
    response: Response,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    _ = tenant_id
    row = _empresa_sistema_row(db)
    if not row or not row.logo_filename:
        raise HTTPException(status_code=404, detail="Logo não definido.")
    p = caminho_absoluto_logo(row.logo_filename)
    if not p:
        raise HTTPException(status_code=404, detail="Logo não encontrado.")
    mt = (row.logo_mimetype or "").strip() or "application/octet-stream"
    _public_cache_headers(response)
    return FileResponse(
        path=str(p),
        media_type=mt,
        filename=p.name,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/public/categories", response_model=list[KbCategoryRead])
def listar_categorias_publicas(
    request: Request,
    response: Response,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    rows = (
        db.query(KbCategory, func.count(KbArticle.id).label("artigos_count"))
        .outerjoin(
            KbArticle,
            (KbArticle.category_id == KbCategory.id)
            & (KbArticle.status == KbArticleStatus.publicado.value)
            & (KbArticle.interno_only.is_(False))
            & (KbArticle.tenant_id == tenant_id),
        )
        .filter(KbCategory.tenant_id == tenant_id)
        .group_by(KbCategory.id)
        .order_by(KbCategory.ordem.asc(), KbCategory.nome.asc(), KbCategory.id.asc())
        .all()
    )
    _public_cache_headers(response)
    return _category_reads_agregadas(rows)


@router.get("/public/articles", response_model=list[KbArticleBrief])
def listar_artigos_publicos(
    request: Request,
    response: Response,
    tenant_id: TenantIdDep,
    busca: str | None = Query(None),
    category_id: int | None = Query(None, ge=1),
    limit: int = Query(25, ge=1, le=50),
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    q = (
        db.query(KbArticle)
        .options(joinedload(KbArticle.category).joinedload(KbCategory.parent), joinedload(KbArticle.autor))
        .filter(
            KbArticle.tenant_id == tenant_id,
            KbArticle.status == KbArticleStatus.publicado.value,
            KbArticle.interno_only.is_(False),
        )
    )
    if category_id is not None:
        q = q.filter(KbArticle.category_id == category_id)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(KbArticle.titulo.ilike(term), KbArticle.conteudo_markdown.ilike(term)))
    rows = q.order_by(KbArticle.titulo.asc(), KbArticle.id.asc()).limit(limit).all()
    _public_cache_headers(response)
    return [_article_brief(r) for r in rows]


@router.get("/public/suggestions", response_model=list[KbArticleBrief])
def sugestoes_artigos_publicas(
    request: Request,
    response: Response,
    tenant_id: TenantIdDep,
    motivo_id: int | None = Query(None, ge=1),
    natureza_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    if motivo_id is None and natureza_id is None:
        raise HTTPException(status_code=400, detail="Informe motivo_id ou natureza_id.")
    arts = listar_artigos_sugeridos(
        db,
        tenant_id,
        motivo_id=motivo_id,
        natureza_id=natureza_id,
        incluir_interno_only=False,
    )
    _public_cache_headers(response)
    return [_article_brief(a) for a in arts]


@router.get("/public/articles/{slug}", response_model=KbArticleRead)
def obter_artigo_publico_por_slug(
    slug: str,
    request: Request,
    response: Response,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    row = (
        db.query(KbArticle)
        .options(joinedload(KbArticle.category).joinedload(KbCategory.parent), joinedload(KbArticle.autor))
        .filter(
            KbArticle.tenant_id == tenant_id,
            KbArticle.slug == slug,
            KbArticle.status == KbArticleStatus.publicado.value,
            KbArticle.interno_only.is_(False),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    _public_cache_headers(response)
    return _article_read(row)


@router.post("/public/articles/{slug}/feedback", response_model=KbArticleFeedbackRead)
def enviar_feedback_artigo_publico(
    slug: str,
    body: KbArticleFeedbackBody,
    request: Request,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    check_kb_public_feedback_rate_limit(request)
    result = registrar_feedback_artigo_publico(
        db,
        tenant_id=tenant_id,
        slug=slug,
        util=body.util,
        ip=client_ip(request),
    )
    return KbArticleFeedbackRead(**result)


def _portal_mensagem_read(m: PortalMensagem) -> PortalChatMensagemRead:
    midia_ok = bool(m.midia_nome_arquivo and str(m.midia_nome_arquivo).strip())
    return PortalChatMensagemRead(
        id=m.id,
        chat_id=m.chat_id,
        direcao=m.direcao,
        corpo=m.corpo,
        tipo_midia=m.tipo_midia or "texto",
        mimetype=m.mimetype,
        midia_disponivel=midia_ok,
        atendente_id=m.atendente_id,
        atendente_nome=m.atendente.nome if m.atendente else None,
        evento_sistema=m.evento_sistema,
        created_at=m.created_at,
    )


def _portal_public_session_read(db: Session, chat: PortalChat) -> PortalChatPublicSessionRead:
    msgs = listar_mensagens_chat(db, chat.id, limit=100)
    return PortalChatPublicSessionRead(
        protocolo=chat.protocolo,
        estado=chat.estado,
        visitante_nome=chat.visitante_nome,
        mensagens=[_portal_mensagem_read(m) for m in msgs],
    )


def _visitor_token_from_request(request: Request) -> str | None:
    token = (request.headers.get(VISITOR_TOKEN_HEADER) or "").strip()
    return token or None


@router.post("/public/chat/session", response_model=PortalChatSessionRead)
def iniciar_sessao_chat_publico(
    body: PortalChatSessionCreate,
    request: Request,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    check_kb_public_chat_rate_limit(request)
    token_existente = _visitor_token_from_request(request)
    token, chat, retomado = criar_ou_retomar_sessao_visitante(
        db,
        tenant_id=tenant_id,
        visitante_nome=body.visitante_nome,
        visitante_email=body.visitante_email,
        token_existente=token_existente,
    )
    db.commit()
    db.refresh(chat)
    if not retomado:
        emit_portal_chat_fila_from_model(db, chat, estado_anterior=None)
        ultima = (
            db.query(PortalMensagem)
            .options(joinedload(PortalMensagem.atendente))
            .filter(PortalMensagem.chat_id == chat.id)
            .order_by(PortalMensagem.id.desc())
            .first()
        )
        if ultima and ultima.evento_sistema == "auto_espera":
            emit_portal_chat_mensagem_from_models(db, chat, ultima)
    msgs = listar_mensagens_chat(db, chat.id, limit=100)
    chat_loaded = (
        db.query(PortalChat)
        .options(joinedload(PortalChat.setor), joinedload(PortalChat.atendente))
        .filter(PortalChat.id == chat.id)
        .first()
    )
    assert chat_loaded is not None
    chat_data = serializar_chat(db, chat_loaded)
    return PortalChatSessionRead(
        visitor_token=token,
        chat=PortalChatRead(**chat_data),
        mensagens=[_portal_mensagem_read(m) for m in msgs],
    )


@router.get("/public/chat", response_model=PortalChatPublicSessionRead)
def obter_sessao_chat_publico(
    request: Request,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    if not portal_chat_habilitado(db, tenant_id):
        raise HTTPException(status_code=403, detail="Chat do portal desabilitado.")
    token = _visitor_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sessão do visitante não informada.")
    chat = chat_por_token(db, tenant_id, token)
    if not chat:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return _portal_public_session_read(db, chat)


@router.get("/public/chat/mensagens", response_model=list[PortalChatMensagemRead])
def listar_mensagens_chat_publico(
    request: Request,
    tenant_id: TenantIdDep,
    since_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    if not portal_chat_habilitado(db, tenant_id):
        raise HTTPException(status_code=403, detail="Chat do portal desabilitado.")
    token = _visitor_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sessão do visitante não informada.")
    chat = chat_por_token(db, tenant_id, token)
    if not chat:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    rows = listar_mensagens_chat(db, chat.id, since_id=since_id, limit=100)
    return [_portal_mensagem_read(m) for m in rows]


@router.post("/public/chat/mensagens", response_model=PortalChatMensagemRead)
def enviar_mensagem_chat_publico(
    body: PortalChatMensagemCreate,
    request: Request,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    check_kb_public_chat_rate_limit(request)
    token = _visitor_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sessão do visitante não informada.")
    chat = chat_por_token(db, tenant_id, token)
    if not chat:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    estado_antes = chat.estado
    msg = registrar_mensagem_visitante(db, chat, body.corpo)
    db.commit()
    db.refresh(msg)
    db.refresh(chat)
    msg = (
        db.query(PortalMensagem)
        .options(joinedload(PortalMensagem.atendente))
        .filter(PortalMensagem.id == msg.id)
        .first()
    )
    assert msg is not None
    emit_portal_chat_mensagem_from_models(db, chat, msg)
    if estado_antes == "aguardando_avaliacao" and chat.estado == "encerrado":
        ultima = (
            db.query(PortalMensagem)
            .options(joinedload(PortalMensagem.atendente))
            .filter(PortalMensagem.chat_id == chat.id)
            .order_by(PortalMensagem.id.desc())
            .first()
        )
        if ultima and ultima.id != msg.id:
            emit_portal_chat_mensagem_from_models(db, chat, ultima)
    return _portal_mensagem_read(msg)


@router.get("/public/chat/mensagens/{mensagem_id}/midia")
def obter_midia_chat_publico(
    mensagem_id: int,
    request: Request,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
):
    check_kb_public_rate_limit(request)
    token = _visitor_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sessão do visitante não informada.")
    chat = chat_por_token(db, tenant_id, token)
    if not chat:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    m = (
        db.query(PortalMensagem)
        .filter(PortalMensagem.chat_id == chat.id, PortalMensagem.id == mensagem_id)
        .first()
    )
    if not m or not m.midia_nome_arquivo:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    path = caminho_absoluto_arquivo(m.midia_nome_arquivo)
    if not path:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado em disco")
    media_type = m.mimetype or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.post("/public/chat/mensagens/midia", response_model=PortalChatMensagemRead, status_code=201)
async def enviar_midia_chat_publico(
    request: Request,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    mediatipo: str = Form(..., description="imagem | video | audio | documento"),
    caption: str = Form(""),
):
    check_kb_public_rate_limit(request)
    check_kb_public_chat_rate_limit(request)
    token = _visitor_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sessão do visitante não informada.")
    chat = chat_por_token(db, tenant_id, token)
    if not chat:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    data = await file.read()
    if len(data) > settings.WHATSAPP_MEDIA_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Ficheiro excede o tamanho máximo permitido.")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    mime = (file.content_type or "application/octet-stream").split(";")[0].strip()
    tipo = (mediatipo or "documento").strip().lower()
    if tipo in ("image", "imagem"):
        tipo = "imagem"
    nome_guardado = gravar_bytes_em_disco(data, mime)
    if not nome_guardado:
        raise HTTPException(status_code=500, detail="Não foi possível guardar o ficheiro em disco.")
    msg = registrar_mensagem_midia_visitante(
        db,
        chat,
        tipo_midia=tipo,
        mimetype=mime,
        midia_nome_arquivo=nome_guardado,
        caption=caption,
    )
    db.commit()
    db.refresh(msg)
    msg = (
        db.query(PortalMensagem)
        .options(joinedload(PortalMensagem.atendente))
        .filter(PortalMensagem.id == msg.id)
        .first()
    )
    assert msg is not None
    emit_portal_chat_mensagem_from_models(db, chat, msg)
    return _portal_mensagem_read(msg)
