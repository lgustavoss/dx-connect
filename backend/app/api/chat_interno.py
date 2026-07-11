from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings

from app.core.auth import obter_atendente_atual
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.database import get_db
from app.models.atendente import Atendente
from app.models.chat_interno import TIPO_MENSAGEM_TEXTO, ConversaInterna
from app.services import chat_interno_media_storage as media_storage
from app.schemas.chat_interno import (
    ConversaDiretaCreate,
    ConversaInboxRead,
    ConversaRead,
    MensagemInternaCreate,
    MensagemInternaRead,
)
from app.schemas.lista_paginada import ListaPaginada
from app.services import chat_interno as chat_svc

router = APIRouter(prefix="/chat-interno", tags=["chat-interno"])

_MAX_MENSAGENS = 100
_DEFAULT_MENSAGENS = 50


def _assert_acesso_setor(atendente: Atendente, db: Session, setor_id: int) -> None:
    if atendente.role == "admin":
        return
    vis = ids_setores_visiveis_atendente(db, atendente)
    if setor_id not in vis:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor.")


def _to_conversa_read(db: Session, conversa: ConversaInterna, atendente: Atendente) -> ConversaRead:
    titulo = chat_svc.titulo_conversa(db, conversa, atendente.id)
    return ConversaRead(
        id=conversa.id,
        tipo=conversa.tipo,  # type: ignore[arg-type]
        setor_id=conversa.setor_id,
        setor_nome=conversa.setor.nome if conversa.setor else None,
        titulo=titulo,
        created_at=conversa.created_at,
    )


def _to_mensagem_read(mensagem, *, conversa: ConversaInterna, atendente: Atendente, db: Session) -> MensagemInternaRead:
    tipo = mensagem.tipo_midia or TIPO_MENSAGEM_TEXTO
    status = chat_svc.status_entrega_mensagem(db, conversa, mensagem, atendente.id)
    return MensagemInternaRead(
        id=mensagem.id,
        conversa_id=mensagem.conversa_id,
        atendente_id=mensagem.atendente_id,
        atendente_nome=mensagem.atendente.nome if mensagem.atendente else None,
        corpo=mensagem.corpo,
        tipo_midia=tipo,  # type: ignore[arg-type]
        mimetype=mensagem.mimetype,
        nome_arquivo=mensagem.nome_arquivo,
        tamanho_bytes=mensagem.tamanho_bytes,
        midia_disponivel=bool(mensagem.storage_key),
        status_entrega=status,  # type: ignore[arg-type]
        created_at=mensagem.created_at,
    )


def _emit_apos_mensagem(db: Session, conversa: ConversaInterna, mensagem, atendente_id: int) -> None:
    from app.services.realtime_emit import emit_chat_interno_mensagem

    emit_chat_interno_mensagem(
        db,
        conversa,
        mensagem,
        exclude_atendente_id=atendente_id,
    )


def _obter_conversa_ou_404(db: Session, conversa_id: int) -> ConversaInterna:
    conversa = chat_svc.obter_conversa_por_id(db, conversa_id)
    if not conversa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    return conversa


def _exigir_acesso_conversa(db: Session, atendente: Atendente, conversa: ConversaInterna) -> None:
    if not chat_svc.pode_acessar_conversa(db, atendente, conversa):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para esta conversa.")


def _map_chat_erro(exc: chat_svc.ChatInternoErro) -> HTTPException:
    detail = str(exc)
    code = status.HTTP_403_FORBIDDEN if "permissão" in detail.lower() else status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=detail)


@router.get("/conversas", response_model=list[ConversaInboxRead])
def listar_conversas(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    resumos = chat_svc.listar_conversas_inbox(db, atendente)
    return [
        ConversaInboxRead(
            id=r.conversa.id,
            tipo=r.conversa.tipo,  # type: ignore[arg-type]
            titulo=r.titulo,
            setor_id=r.conversa.setor_id,
            ultima_mensagem_corpo=r.ultima_mensagem_corpo,
            ultima_mensagem_em=r.ultima_mensagem_em,
            nao_lidas_count=r.nao_lidas_count,
            created_at=r.conversa.created_at,
        )
        for r in resumos
    ]


@router.post("/conversas/direta", response_model=ConversaRead, status_code=status.HTTP_201_CREATED)
def criar_ou_obter_conversa_direta(
    body: ConversaDiretaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    try:
        chat_svc.validar_atendente_destino(db, atendente.tenant_id, body.atendente_id)
        conversa = chat_svc.obter_ou_criar_conversa_direta(
            db,
            atendente.tenant_id,
            atendente.id,
            body.atendente_id,
        )
        db.commit()
        db.refresh(conversa)
        return _to_conversa_read(db, conversa, atendente)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.get("/conversas/{conversa_id}/mensagens", response_model=ListaPaginada[MensagemInternaRead])
def listar_mensagens(
    conversa_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_MENSAGENS, ge=1, le=_MAX_MENSAGENS),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)

    rows, total = chat_svc.listar_mensagens(db, conversa_id, offset=offset, limit=limit)
    return ListaPaginada(
        items=[_to_mensagem_read(m, conversa=conversa, atendente=atendente, db=db) for m in rows],
        total=total,
    )


@router.post(
    "/conversas/{conversa_id}/mensagens",
    response_model=MensagemInternaRead,
    status_code=status.HTTP_201_CREATED,
)
def enviar_mensagem(
    conversa_id: int,
    body: MensagemInternaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    try:
        mensagem = chat_svc.enviar_mensagem(db, conversa, atendente, body.corpo)
        db.commit()
        db.refresh(mensagem)
        _emit_apos_mensagem(db, conversa, mensagem, atendente.id)
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.post(
    "/conversas/{conversa_id}/mensagens/midia",
    response_model=MensagemInternaRead,
    status_code=status.HTTP_201_CREATED,
)
async def enviar_mensagem_midia(
    conversa_id: int,
    file: UploadFile = File(...),
    mediatipo: str = Form(..., description="imagem | video | audio | documento"),
    caption: str = Form(""),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    data = await file.read()
    if len(data) > settings.CHAT_INTERNO_MEDIA_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o tamanho máximo permitido.")

    mime = (file.content_type or "application/octet-stream").split(";")[0].strip()
    try:
        mensagem = chat_svc.enviar_mensagem_midia(
            db,
            conversa,
            atendente,
            tipo_midia=mediatipo,
            data=data,
            mimetype=mime,
            nome_original=file.filename,
            caption=caption,
        )
        db.commit()
        db.refresh(mensagem)
        _emit_apos_mensagem(db, conversa, mensagem, atendente.id)
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.get("/conversas/{conversa_id}/mensagens/{mensagem_id}/download")
def download_mensagem_midia(
    conversa_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)

    mensagem = chat_svc.obter_mensagem_por_id(db, conversa_id, mensagem_id)
    if not mensagem or not mensagem.storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mídia não encontrada.")

    path = media_storage.caminho_absoluto_arquivo(mensagem.storage_key)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")

    media_type = mensagem.mimetype or "application/octet-stream"
    filename = mensagem.nome_arquivo or path.name
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/setores/{setor_id}/canal", response_model=ConversaRead)
def obter_canal_setor(
    setor_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    _assert_acesso_setor(atendente, db, setor_id)
    try:
        conversa = chat_svc.obter_ou_criar_canal_setor(db, atendente.tenant_id, setor_id)
        db.commit()
        db.refresh(conversa)
        return _to_conversa_read(db, conversa, atendente)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.post(
    "/setores/{setor_id}/canal/mensagens",
    response_model=MensagemInternaRead,
    status_code=status.HTTP_201_CREATED,
)
def publicar_no_canal_setor(
    setor_id: int,
    body: MensagemInternaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    if not chat_svc.pode_publicar_no_canal(db, atendente, setor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor.")
    try:
        conversa = chat_svc.obter_ou_criar_canal_setor(db, atendente.tenant_id, setor_id)
        mensagem = chat_svc.enviar_mensagem(db, conversa, atendente, body.corpo)
        db.commit()
        db.refresh(mensagem)
        _emit_apos_mensagem(db, conversa, mensagem, atendente.id)
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.post(
    "/setores/{setor_id}/canal/mensagens/midia",
    response_model=MensagemInternaRead,
    status_code=status.HTTP_201_CREATED,
)
async def publicar_midia_no_canal_setor(
    setor_id: int,
    file: UploadFile = File(...),
    mediatipo: str = Form(..., description="imagem | video | audio | documento"),
    caption: str = Form(""),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    if not chat_svc.pode_publicar_no_canal(db, atendente, setor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor.")

    data = await file.read()
    if len(data) > settings.CHAT_INTERNO_MEDIA_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o tamanho máximo permitido.")

    mime = (file.content_type or "application/octet-stream").split(";")[0].strip()
    try:
        conversa = chat_svc.obter_ou_criar_canal_setor(db, atendente.tenant_id, setor_id)
        mensagem = chat_svc.enviar_mensagem_midia(
            db,
            conversa,
            atendente,
            tipo_midia=mediatipo,
            data=data,
            mimetype=mime,
            nome_original=file.filename,
            caption=caption,
        )
        db.commit()
        db.refresh(mensagem)
        _emit_apos_mensagem(db, conversa, mensagem, atendente.id)
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.post("/conversas/{conversa_id}/visto", status_code=status.HTTP_204_NO_CONTENT)
def marcar_visto(
    conversa_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    try:
        chat_svc.marcar_visto(db, conversa, atendente)
        db.commit()
        from app.services.realtime_emit import emit_chat_interno_lido, emit_notificacao_contagem

        emit_chat_interno_lido(db, conversa, atendente.id)
        emit_notificacao_contagem(db, [atendente.id])
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc
