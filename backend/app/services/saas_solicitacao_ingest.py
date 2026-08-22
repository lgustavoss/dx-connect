"""Ingest e fila unificada de solicitações de produto no control-plane (#855)."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.cliente_saas import ClienteSaaS
from app.models.saas_solicitacao_produto import SaasSolicitacaoProduto, SaasSolicitacaoProdutoAnexo
from app.models.solicitacao_melhoria import SolicitacaoMelhoria, SolicitacaoMelhoriaAnexo
from app.models.webhook_outbox import WebhookOutbox
from app.schemas.saas_solicitacao import (
    SaasSolicitacaoAnexoRead,
    SaasSolicitacaoComentarioRead,
    SaasSolicitacaoDetalhe,
    SaasSolicitacaoIngest,
    SaasSolicitacaoListaItem,
)
from app.services.protocolo_mensal import gerar_protocolo_solicitacao
from app.services.solicitacao_melhoria_copy import rotulo_status
from app.services.ticket_closed_webhook import STATUS_PENDENTE, _dedup_ja_processado, _utcnow

logger = logging.getLogger(__name__)

EVENT_SAAS_SOLICITACAO = "saas.solicitacao"
EVENT_SAAS_SOLICITACAO_MEDIA = "saas.solicitacao.media"


def hash_ingest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_confere(stored_hash: str | None, token: str) -> bool:
    if not stored_hash or not token:
        return False
    got = hash_ingest_token(token)
    if len(got) != len(stored_hash):
        return False
    return secrets.compare_digest(got, stored_hash)


def ingest_url_publica() -> str:
    explicit = (settings.SAAS_INGEST_PUBLIC_URL or "").strip()
    if explicit:
        return explicit.rstrip("/")
    base = (settings.SAAS_PROVISION_BASE_DOMAIN or "deskrudder.com.br").strip().lstrip(".")
    return f"https://api.{base}/v1/saas/ingest/solicitacoes"


def instance_slug_local() -> str:
    slug = (settings.SAAS_INSTANCE_SLUG or "").strip().lower()
    if slug:
        return slug
    host = (settings.CLIENT_APP_HOST or "").strip().lower()
    if host:
        return host.split(".")[0]
    return "local"


def gerar_e_gravar_token(row: ClienteSaaS) -> str:
    token = secrets.token_urlsafe(32)
    row.ingest_token_hash = hash_ingest_token(token)
    return token


def autenticar_ingest_por_token(db: Session, token: str) -> ClienteSaaS:
    """Identifica a licença só pelo token (GET sync não envia slug no body)."""
    raw = (token or "").strip()
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")
    digest = hash_ingest_token(raw)
    row = db.query(ClienteSaaS).filter(ClienteSaaS.ingest_token_hash == digest).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")
    return row


def autenticar_ingest(db: Session, *, slug: str, token: str) -> ClienteSaaS:
    slug_n = (slug or "").strip().lower()
    if not slug_n or not (token or "").strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")
    row = db.query(ClienteSaaS).filter(ClienteSaaS.slug == slug_n).first()
    if not row or not token_confere(row.ingest_token_hash, token.strip()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")
    return row


def _protocolo_para_fila(
    db: Session,
    existente: SaasSolicitacaoProduto | None,
) -> str:
    """O número #S é emitido só no control-plane (sequência única do Postgres SaaS)."""
    if existente and (existente.protocolo or "").strip():
        return existente.protocolo
    return gerar_protocolo_solicitacao(db)


def upsert_from_payload(
    db: Session,
    data: SaasSolicitacaoIngest,
    *,
    cliente: ClienteSaaS | None,
) -> SaasSolicitacaoProduto:
    slug = data.instance_slug.strip().lower()
    existente = (
        db.query(SaasSolicitacaoProduto)
        .filter(
            SaasSolicitacaoProduto.instance_slug == slug,
            SaasSolicitacaoProduto.origem_solicitacao_id == data.origem_solicitacao_id,
        )
        .first()
    )
    created_at = data.created_at
    protocolo = _protocolo_para_fila(db, existente)
    if existente:
        existente.tipo = data.tipo
        existente.titulo = data.titulo.strip()
        existente.descricao = data.descricao.strip()
        # Status/motivo ficam com a triagem SaaS (#856); a instância não é fonte de verdade.
        existente.versao_contexto = (data.versao_contexto or "").strip() or None
        existente.autor_nome = (data.autor_nome or "").strip() or None
        existente.protocolo = protocolo
        if created_at is not None:
            existente.created_at_origem = created_at
        if cliente is not None:
            existente.cliente_saas_id = cliente.id
        db.add(existente)
        db.flush()
        return existente

    row = SaasSolicitacaoProduto(
        cliente_saas_id=cliente.id if cliente is not None else None,
        instance_slug=slug,
        origem_solicitacao_id=data.origem_solicitacao_id,
        tipo=data.tipo,
        titulo=data.titulo.strip(),
        descricao=data.descricao.strip(),
        status=(data.status or "aberta").strip() or "aberta",
        versao_contexto=(data.versao_contexto or "").strip() or None,
        autor_nome=(data.autor_nome or "").strip() or None,
        created_at_origem=created_at,
        ingested_at=datetime.now(timezone.utc),
        protocolo=protocolo,
        triagem_atualizada_em=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def _payload_from_row(row: SolicitacaoMelhoria, slug: str) -> SaasSolicitacaoIngest:
    created = row.created_at or datetime.now(timezone.utc)
    return SaasSolicitacaoIngest(
        instance_slug=slug,
        origem_solicitacao_id=int(row.id),
        tipo=row.tipo if row.tipo in ("sugestao", "problema") else "sugestao",
        titulo=row.titulo,
        descricao=row.descricao,
        status=row.status or "aberta",
        versao_contexto=row.versao_contexto,
        autor_nome=row.autor_nome,
        created_at=created,
    )


def _enfileirar_outbox(db: Session, payload: SaasSolicitacaoIngest, url: str) -> None:
    dedup_key = f"{EVENT_SAAS_SOLICITACAO}:{payload.instance_slug}:{payload.origem_solicitacao_id}"
    if _dedup_ja_processado(db, dedup_key):
        return
    body = payload.model_dump(mode="json")
    db.add(
        WebhookOutbox(
            event_type=EVENT_SAAS_SOLICITACAO,
            dedup_key=dedup_key,
            target_url=url,
            payload_json=json.dumps(body, ensure_ascii=False, default=str),
            status=STATUS_PENDENTE,
            scheduled_at=_utcnow(),
        )
    )
    db.flush()


def _enfileirar_outbox_media(
    db: Session,
    *,
    slug: str,
    origem_id: int,
    anexo: SolicitacaoMelhoriaAnexo,
    ingest_url: str,
) -> None:
    key = (anexo.storage_key or "").strip()
    if not key:
        return
    dedup_key = f"{EVENT_SAAS_SOLICITACAO_MEDIA}:{slug}:{origem_id}:{key}"
    if _dedup_ja_processado(db, dedup_key):
        return
    target = f"{ingest_url.rstrip('/')}/{origem_id}/media"
    body = {
        "origem_solicitacao_id": origem_id,
        "storage_key": key,
        "papel": anexo.papel,
        "nome_original": anexo.nome_original,
        "content_type": anexo.content_type,
    }
    db.add(
        WebhookOutbox(
            event_type=EVENT_SAAS_SOLICITACAO_MEDIA,
            dedup_key=dedup_key,
            target_url=target,
            payload_json=json.dumps(body, ensure_ascii=False),
            status=STATUS_PENDENTE,
            scheduled_at=_utcnow() + timedelta(seconds=2),
        )
    )
    db.flush()


def _upsert_saas_anexo(
    db: Session,
    dest: SaasSolicitacaoProduto,
    *,
    papel: str,
    nome_original: str,
    content_type: str | None,
    tamanho_bytes: int,
    storage_key: str,
) -> SaasSolicitacaoProdutoAnexo:
    existente = (
        db.query(SaasSolicitacaoProdutoAnexo)
        .filter(
            SaasSolicitacaoProdutoAnexo.solicitacao_id == dest.id,
            SaasSolicitacaoProdutoAnexo.storage_key == storage_key,
        )
        .first()
    )
    if existente:
        existente.papel = papel
        existente.nome_original = nome_original
        existente.content_type = content_type
        existente.tamanho_bytes = tamanho_bytes
        db.add(existente)
        db.flush()
        return existente
    row = SaasSolicitacaoProdutoAnexo(
        solicitacao_id=dest.id,
        papel=papel,
        nome_original=nome_original,
        content_type=content_type,
        tamanho_bytes=tamanho_bytes,
        storage_key=storage_key,
    )
    db.add(row)
    db.flush()
    return row


def _copiar_anexos_locais(db: Session, origem: SolicitacaoMelhoria, dest: SaasSolicitacaoProduto) -> None:
    anexos = (
        db.query(SolicitacaoMelhoriaAnexo)
        .filter(SolicitacaoMelhoriaAnexo.solicitacao_id == origem.id)
        .order_by(SolicitacaoMelhoriaAnexo.created_at.asc())
        .all()
    )
    for a in anexos:
        key = (a.storage_key or "").strip()
        if not key:
            continue
        _upsert_saas_anexo(
            db,
            dest,
            papel=a.papel or "anexo",
            nome_original=a.nome_original,
            content_type=a.content_type,
            tamanho_bytes=int(a.tamanho_bytes or 0),
            storage_key=key,
        )


def receber_media_ingest(
    db: Session,
    *,
    cliente: ClienteSaaS,
    origem_solicitacao_id: int,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    papel: str,
    storage_key: str,
) -> SaasSolicitacaoProdutoAnexo:
    from app.services import solicitacao_melhoria_media as media

    dest = (
        db.query(SaasSolicitacaoProduto)
        .filter(
            SaasSolicitacaoProduto.instance_slug == (cliente.slug or "").strip().lower(),
            SaasSolicitacaoProduto.origem_solicitacao_id == origem_solicitacao_id,
        )
        .first()
    )
    if dest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação ainda não ingerida",
        )
    papel_n = (papel or media.PAPEL_ANEXO).strip().lower()
    if papel_n not in (media.PAPEL_INLINE, media.PAPEL_ANEXO):
        raise HTTPException(status_code=400, detail="Papel de mídia inválido")
    try:
        nome, mime = media.validar_upload(filename, content_type, len(data), papel=papel_n)
        key = media.gravar_com_chave(data, storage_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao gravar arquivo") from None
    return _upsert_saas_anexo(
        db,
        dest,
        papel=papel_n,
        nome_original=nome,
        content_type=mime,
        tamanho_bytes=len(data),
        storage_key=key,
    )


def obter_anexo_saas_por_storage(db: Session, storage_key: str) -> SaasSolicitacaoProdutoAnexo | None:
    key = (storage_key or "").strip()
    if not key:
        return None
    return (
        db.query(SaasSolicitacaoProdutoAnexo)
        .filter(SaasSolicitacaoProdutoAnexo.storage_key == key)
        .first()
    )


def anexo_read(a: SaasSolicitacaoProdutoAnexo) -> SaasSolicitacaoAnexoRead:
    from app.services.solicitacao_melhoria_media import media_public_path

    return SaasSolicitacaoAnexoRead(
        id=a.id,
        papel=a.papel,
        nome_original=a.nome_original,
        content_type=a.content_type,
        tamanho_bytes=a.tamanho_bytes,
        url=media_public_path(a.storage_key),
    )


def enfileirar_copia_saas(db: Session, row: SolicitacaoMelhoria) -> None:
    """Cópia para o control-plane. Falha nunca deve impedir o pedido local."""
    try:
        slug = instance_slug_local()
        payload = _payload_from_row(row, slug)
        if settings.SAAS_CONTROL_PLANE:
            cliente = db.query(ClienteSaaS).filter(ClienteSaaS.slug == slug).first()
            dest = upsert_from_payload(db, payload, cliente=cliente)
            if dest.protocolo:
                row.protocolo = dest.protocolo
                db.add(row)
            _copiar_anexos_locais(db, row, dest)
            return
        url = (settings.SAAS_CONTROL_PLANE_INGEST_URL or "").strip()
        token = (settings.SAAS_INSTANCE_INGEST_TOKEN or "").strip()
        slug_cfg = (settings.SAAS_INSTANCE_SLUG or "").strip()
        if not url or not token or not slug_cfg:
            return
        _enfileirar_outbox(db, payload, url)
        anexos = (
            db.query(SolicitacaoMelhoriaAnexo)
            .filter(SolicitacaoMelhoriaAnexo.solicitacao_id == row.id)
            .all()
        )
        for a in anexos:
            _enfileirar_outbox_media(
                db,
                slug=slug,
                origem_id=int(row.id),
                anexo=a,
                ingest_url=url,
            )
    except Exception:
        logger.exception(
            "Falha ao enfileirar cópia SaaS da solicitação id=%s (pedido local mantém-se)",
            getattr(row, "id", None),
        )


def item_lista(
    row: SaasSolicitacaoProduto,
    *,
    peso_clientes: int = 1,
    pedidos_grupo: int = 1,
) -> SaasSolicitacaoListaItem:
    cliente = row.cliente
    return SaasSolicitacaoListaItem(
        id=row.id,
        cliente_saas_id=row.cliente_saas_id,
        cliente_nome=cliente.nome if cliente is not None else None,
        instance_slug=row.instance_slug,
        origem_solicitacao_id=row.origem_solicitacao_id,
        protocolo=row.protocolo,
        tipo=row.tipo,
        titulo=row.titulo,
        status=row.status,
        status_rotulo=rotulo_status(row.status),
        versao_contexto=row.versao_contexto,
        autor_nome=row.autor_nome,
        created_at_origem=row.created_at_origem,
        ingested_at=row.ingested_at,
        github_issue_number=row.github_issue_number,
        github_issue_url=row.github_issue_url,
        peso_clientes=peso_clientes,
        pedidos_grupo=pedidos_grupo,
    )


def detalhe(db: Session, row: SaasSolicitacaoProduto) -> SaasSolicitacaoDetalhe:
    from app.services import saas_solicitacao_grupo as grupo

    pesos = grupo.pesos_por_id(db, [row])
    pc, pg = pesos.get(row.id, (1, 1))
    base = item_lista(row, peso_clientes=pc, pedidos_grupo=pg)
    comentarios = [
        SaasSolicitacaoComentarioRead(
            id=c.id,
            corpo=c.corpo,
            publico_cliente=c.publico_cliente,
            autor_nome=c.autor_nome,
            created_at=c.created_at,
        )
        for c in (row.comentarios or [])
    ]
    anexos_rows = (
        db.query(SaasSolicitacaoProdutoAnexo)
        .filter(SaasSolicitacaoProdutoAnexo.solicitacao_id == row.id)
        .order_by(SaasSolicitacaoProdutoAnexo.created_at.asc())
        .all()
    )
    anexos = [anexo_read(a) for a in anexos_rows]
    return SaasSolicitacaoDetalhe(
        **base.model_dump(),
        descricao=row.descricao,
        motivo_nao_desenvolvimento=row.motivo_nao_desenvolvimento,
        triagem_atualizada_em=row.triagem_atualizada_em,
        comentarios=comentarios,
        anexos=anexos,
        github_repo=row.github_repo,
        grupo=[grupo.membro_read(m) for m in grupo.membros(db, row)],
        texto_github_demanda=grupo.texto_github_demanda(db, row),
    )


def obter(db: Session, solicitacao_id: int) -> SaasSolicitacaoProduto:
    row = (
        db.query(SaasSolicitacaoProduto)
        .options(
            joinedload(SaasSolicitacaoProduto.cliente),
            joinedload(SaasSolicitacaoProduto.comentarios),
            joinedload(SaasSolicitacaoProduto.anexos),
        )
        .filter(SaasSolicitacaoProduto.id == solicitacao_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return row


def query_base(db: Session):
    return db.query(SaasSolicitacaoProduto)


def _repo_root() -> Path:
    if (settings.SAAS_REPO_ROOT or "").strip():
        return Path(settings.SAAS_REPO_ROOT.strip())
    return Path(__file__).resolve().parents[3]


def _set_env_line(text: str, key: str, value: str) -> str:
    line = f"{key}={value}"
    prefix = f"{key}="
    if prefix in text:
        lines = [line if ln.startswith(prefix) else ln for ln in text.splitlines()]
        return "\n".join(lines) + "\n"
    return text.rstrip() + f"\n{line}\n"


def escrever_ingest_no_client_env(row: ClienteSaaS, *, token: str | None = None) -> None:
    """Grava slug/URL (e token se gerado agora) no client.env da instância."""
    root = _repo_root()
    env_path = root / "deploy" / "clients" / row.slug / "client.env"
    if not env_path.is_file():
        return
    text = env_path.read_text(encoding="utf-8")
    text = _set_env_line(text, "SAAS_INSTANCE_SLUG", row.slug)
    text = _set_env_line(text, "SAAS_CONTROL_PLANE_INGEST_URL", ingest_url_publica())
    if token:
        text = _set_env_line(text, "SAAS_INSTANCE_INGEST_TOKEN", token)
    env_path.write_text(text, encoding="utf-8")
    logger.info("Ingest SaaS escrito em %s (slug=%s)", env_path, row.slug)


def garantir_token_e_escrever_env(row: ClienteSaaS, *, forcar_novo: bool = False) -> str | None:
    token = None
    if forcar_novo or not (row.ingest_token_hash or "").strip():
        token = gerar_e_gravar_token(row)
    escrever_ingest_no_client_env(row, token=token)
    return token
