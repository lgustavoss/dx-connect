"""Regras de negócio — solicitações de melhoria (#800–#804)."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.solicitacao_melhoria import (
    SolicitacaoMelhoria,
    SolicitacaoMelhoriaAnexo,
    SolicitacaoMelhoriaComentario,
    SolicitacaoMelhoriaHistorico,
)
from app.schemas.solicitacao_melhoria import (
    SolicitacaoAnexoRead,
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

MSG_TRIAGEM_SAAS = "A triagem de produto é feita no painel SaaS DeskRudder"


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
            joinedload(SolicitacaoMelhoria.anexos),
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


def _anexo_read(a: SolicitacaoMelhoriaAnexo) -> SolicitacaoAnexoRead:
    from app.services.solicitacao_melhoria_media import media_public_path

    return SolicitacaoAnexoRead(
        id=a.id,
        papel=a.papel,
        nome_original=a.nome_original,
        content_type=a.content_type,
        tamanho_bytes=a.tamanho_bytes,
        url=media_public_path(a.storage_key),
        created_at=a.created_at,
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
        protocolo=row.protocolo,
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
        anexos=[_anexo_read(a) for a in (row.anexos or [])],
    )


def _vincular_anexos(
    db: Session,
    row: SolicitacaoMelhoria,
    atendente: Atendente,
    ids: list[int],
) -> None:
    uniq = list(dict.fromkeys(int(i) for i in (ids or []) if int(i) > 0))
    if not uniq:
        return
    if len(uniq) > 20:
        raise HTTPException(status_code=400, detail="Demasiados anexos neste pedido")
    encontrados = (
        db.query(SolicitacaoMelhoriaAnexo)
        .filter(
            SolicitacaoMelhoriaAnexo.id.in_(uniq),
            SolicitacaoMelhoriaAnexo.autor_atendente_id == atendente.id,
        )
        .all()
    )
    if len(encontrados) != len(uniq):
        raise HTTPException(status_code=400, detail="Anexo inválido ou de outro utilizador")
    for a in encontrados:
        if a.solicitacao_id not in (None, row.id):
            raise HTTPException(status_code=400, detail="Anexo já associado a outro pedido")
        a.solicitacao_id = row.id
        db.add(a)


def guardar_media(
    db: Session,
    atendente: Atendente,
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    papel: str,
) -> SolicitacaoMelhoriaAnexo:
    from app.services import solicitacao_melhoria_media as media

    papel_n = (papel or media.PAPEL_ANEXO).strip().lower()
    if papel_n not in (media.PAPEL_INLINE, media.PAPEL_ANEXO):
        raise HTTPException(status_code=400, detail="Papel de mídia inválido")
    try:
        nome, mime = media.validar_upload(filename, content_type, len(data), papel=papel_n)
        storage_key = media.gravar_bytes(data, mimetype=mime, nome_original=nome)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError:
        raise HTTPException(status_code=500, detail="Falha ao gravar arquivo") from None
    row = SolicitacaoMelhoriaAnexo(
        solicitacao_id=None,
        autor_atendente_id=atendente.id,
        papel=papel_n,
        nome_original=nome,
        content_type=mime,
        tamanho_bytes=len(data),
        storage_key=storage_key,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def obter_anexo_por_storage(db: Session, storage_key: str) -> SolicitacaoMelhoriaAnexo | None:
    key = (storage_key or "").strip()
    if not key:
        return None
    return db.query(SolicitacaoMelhoriaAnexo).filter(SolicitacaoMelhoriaAnexo.storage_key == key).first()


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
    _vincular_anexos(db, row, atendente, data.anexo_ids)
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
    from app.services.saas_solicitacao_ingest import enfileirar_copia_saas

    enfileirar_copia_saas(db, row)
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


def aplicar_status_origem_saas(
    db: Session,
    solicitacao_id: int,
    *,
    status_novo: str,
    motivo_nao_desenvolvimento: str | None,
    atendente_id: int | None = None,
) -> SolicitacaoMelhoria | None:
    """Aplica triagem do control-plane na instância. Sem commit (o caller fecha a transação)."""
    if status_novo not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail="Status inválido")
    row = db.query(SolicitacaoMelhoria).filter(SolicitacaoMelhoria.id == solicitacao_id).first()
    if not row:
        return None
    if status_novo == "nao_sera_desenvolvida" and not (motivo_nao_desenvolvimento or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Informe o motivo quando marcar como não será desenvolvida",
        )
    anterior = row.status
    motivo = (motivo_nao_desenvolvimento or "").strip() or None
    mesmo_status = anterior == status_novo
    mesmo_motivo = (row.motivo_nao_desenvolvimento or None) == (
        motivo if status_novo == "nao_sera_desenvolvida" else row.motivo_nao_desenvolvimento
    )
    if mesmo_status and mesmo_motivo:
        return row
    row.status = status_novo
    if status_novo == "nao_sera_desenvolvida" and motivo:
        row.motivo_nao_desenvolvimento = motivo
    msg = mensagem_publica_status(status_novo, motivo=row.motivo_nao_desenvolvimento)
    if not mesmo_status:
        db.add(
            SolicitacaoMelhoriaHistorico(
                solicitacao_id=row.id,
                status_anterior=anterior,
                status_novo=status_novo,
                motivo=row.motivo_nao_desenvolvimento if status_novo == "nao_sera_desenvolvida" else None,
                atendente_id=atendente_id,
                mensagem_publica=msg,
            )
        )
        registrar_audit(
            db,
            "solicitacao_melhoria",
            row.id,
            "status_change",
            atendente_id,
            payload={
                "de": anterior,
                "para": status_novo,
                "origem": "saas",
                "motivo": row.motivo_nao_desenvolvimento if status_novo == "nao_sera_desenvolvida" else None,
            },
        )
    db.add(row)
    db.flush()
    return row


def aplicar_protocolo_origem_saas(
    db: Session,
    solicitacao_id: int,
    protocolo: str | None,
) -> SolicitacaoMelhoria | None:
    """Grava o protocolo global #S… emitido pelo control-plane. Sem commit."""
    from app.services.protocolo_mensal import normalizar_protocolo_solicitacao

    proto = normalizar_protocolo_solicitacao(protocolo)
    if not proto:
        return None
    row = db.query(SolicitacaoMelhoria).filter(SolicitacaoMelhoria.id == solicitacao_id).first()
    if not row:
        return None
    if row.protocolo == proto:
        return row
    row.protocolo = proto
    db.add(row)
    db.flush()
    return row


def aplicar_comentario_origem_saas(
    db: Session,
    solicitacao_id: int,
    *,
    corpo: str,
    origem_externa_id: str,
    autor_nome: str | None,
) -> SolicitacaoMelhoriaComentario | None:
    """Comentário público vindo do SaaS. Idempotente por origem_externa_id. Sem commit."""
    texto = (corpo or "").strip()
    if not texto:
        return None
    row = db.query(SolicitacaoMelhoria).filter(SolicitacaoMelhoria.id == solicitacao_id).first()
    if not row:
        return None
    ja = (
        db.query(SolicitacaoMelhoriaComentario)
        .filter(SolicitacaoMelhoriaComentario.origem_externa_id == origem_externa_id)
        .first()
    )
    if ja:
        return ja
    c = SolicitacaoMelhoriaComentario(
        solicitacao_id=row.id,
        corpo=texto,
        publico_cliente=True,
        origem="saas",
        origem_externa_id=origem_externa_id,
        autor_atendente_id=None,
        autor_nome=(autor_nome or "").strip() or "DeskRudder",
    )
    db.add(c)
    db.flush()
    return c


def alterar_status(
    db: Session,
    solicitacao_id: int,
    _admin: Atendente,
    data: SolicitacaoMelhoriaStatusUpdate,
) -> SolicitacaoMelhoria:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_TRIAGEM_SAAS)


def adicionar_comentario(
    db: Session,
    solicitacao_id: int,
    atendente: Atendente,
    data: SolicitacaoComentarioCreate,
) -> SolicitacaoMelhoria:
    row = _carregar(db, solicitacao_id)
    _garantir_mesma_org(row, atendente)
    is_admin = _is_admin(atendente)
    if is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_TRIAGEM_SAAS)

    if not data.publico_cliente:
        raise HTTPException(status_code=403, detail="Não é possível criar notas internas")
    if row.status in STATUS_FINAIS:
        raise HTTPException(
            status_code=400,
            detail="Esta solicitação está encerrada e já não aceita respostas",
        )
    if row.autor_atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Só o autor pode responder nesta solicitação")

    db.add(
        SolicitacaoMelhoriaComentario(
            solicitacao_id=row.id,
            corpo=data.corpo.strip(),
            publico_cliente=True,
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
        protocolo=row.protocolo,
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
