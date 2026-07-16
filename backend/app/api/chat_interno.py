from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings

from app.core.auth import obter_atendente_atual
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.database import get_db
from app.models.atendente import Atendente
from app.models.chat_interno import TIPO_CONVERSA_GRUPO, TIPO_MENSAGEM_TEXTO, ConversaInterna, MensagemInterna
from app.services import chat_interno_media_storage as media_storage
from app.schemas.chat_interno import (
    ConversaDiretaCreate,
    ConversaGrupoCreate,
    ConversaInboxRead,
    ConversaRead,
    GrupoParticipantesUpdate,
    MencaoMensagemRead,
    MensagemInternaCreate,
    MensagemInternaRead,
    MensagemInternaUpdate,
    MensagensInternasPaginaRead,
    ParticipanteGrupoRead,
    ReacaoMensagemCreate,
    ReacaoMensagemRead,
)
from app.services import chat_interno as chat_svc

router = APIRouter(prefix="/chat-interno", tags=["chat-interno"])


def _assert_acesso_setor(atendente: Atendente, db: Session, setor_id: int) -> None:
    if atendente.role == "admin":
        return
    vis = ids_setores_visiveis_atendente(db, atendente)
    if setor_id not in vis:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor.")


def _to_conversa_read(db: Session, conversa: ConversaInterna, atendente: Atendente) -> ConversaRead:
    titulo = chat_svc.titulo_conversa(db, conversa, atendente.id)
    participantes: list[ParticipanteGrupoRead] | None = None
    sou_admin_grupo = False
    if conversa.tipo == TIPO_CONVERSA_GRUPO:
        participantes = [
            ParticipanteGrupoRead(atendente_id=a.id, nome=a.nome, papel=papel)  # type: ignore[arg-type]
            for a, papel in chat_svc.listar_participantes_grupo(db, conversa.id)
        ]
        sou_admin_grupo = chat_svc.is_admin_grupo(db, conversa.id, atendente.id)
    return ConversaRead(
        id=conversa.id,
        tipo=conversa.tipo,  # type: ignore[arg-type]
        setor_id=conversa.setor_id,
        setor_nome=conversa.setor.nome if conversa.setor else None,
        titulo=titulo,
        participantes=participantes,
        sou_admin_grupo=sou_admin_grupo,
        created_at=conversa.created_at,
    )


def _to_mensagem_read(mensagem, *, conversa: ConversaInterna, atendente: Atendente, db: Session) -> MensagemInternaRead:
    tipo = mensagem.tipo_midia or TIPO_MENSAGEM_TEXTO
    status = chat_svc.status_entrega_mensagem(db, conversa, mensagem, atendente.id)
    reacoes = [
        ReacaoMensagemRead(emoji=r.emoji, count=r.count, reagiu_eu=r.reagiu_eu)
        for r in chat_svc.agregar_reacoes_mensagem(db, mensagem.id, atendente.id)
    ]
    mencoes = [
        MencaoMensagemRead(
            tipo=m["tipo"],  # type: ignore[arg-type]
            atendente_id=m.get("atendente_id"),
            rotulo=m.get("rotulo"),
        )
        for m in chat_svc.mencoes_para_leitura(getattr(mensagem, "mencoes", None))
    ]
    perms = chat_svc.permissoes_mensagem(db, conversa, mensagem, atendente)
    return MensagemInternaRead(
        id=mensagem.id,
        conversa_id=mensagem.conversa_id,
        atendente_id=mensagem.atendente_id,
        atendente_nome=mensagem.atendente.nome if mensagem.atendente else None,
        corpo=chat_svc.corpo_mensagem_para_leitura(mensagem),
        tipo_midia=tipo,  # type: ignore[arg-type]
        mimetype=mensagem.mimetype,
        nome_arquivo=mensagem.nome_arquivo,
        tamanho_bytes=mensagem.tamanho_bytes,
        midia_disponivel=bool(mensagem.storage_key) and not chat_svc.mensagem_esta_apagada(mensagem),
        status_entrega=status,  # type: ignore[arg-type]
        apagada=chat_svc.mensagem_esta_apagada(mensagem),
        editada=mensagem.editada_em is not None,
        reacoes=reacoes,
        mencoes=mencoes,
        pode_editar=perms.pode_editar,
        pode_apagar_para_todos=perms.pode_apagar_para_todos,
        pode_apagar_para_mim=perms.pode_apagar_para_mim,
        reply_to_message_id=getattr(mensagem, "reply_to_message_id", None),
        reply_preview=getattr(mensagem, "reply_preview", None),
        reply_autor_nome=getattr(mensagem, "reply_autor_nome", None),
        created_at=mensagem.created_at,
        editada_em=mensagem.editada_em,
    )


def _emit_apos_mensagem(db: Session, conversa: ConversaInterna, mensagem, atendente_id: int) -> None:
    from app.services.realtime_emit import emit_chat_interno_mensagem

    emit_chat_interno_mensagem(
        db,
        conversa,
        mensagem,
        exclude_atendente_id=atendente_id,
    )


def _emit_mensagem_atualizada(db: Session, conversa: ConversaInterna, mensagem, *, acao: str) -> None:
    from app.services.realtime_emit import emit_chat_interno_mensagem_atualizada

    emit_chat_interno_mensagem_atualizada(db, conversa, mensagem, acao=acao)


def _obter_mensagem_na_conversa(
    db: Session,
    conversa_id: int,
    mensagem_id: int,
) -> MensagemInterna:
    mensagem = chat_svc.obter_mensagem_por_id(db, conversa_id, mensagem_id)
    if not mensagem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem não encontrada.")
    return mensagem


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


@router.get("/conversas/{conversa_id}", response_model=ConversaRead)
def obter_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)
    return _to_conversa_read(db, conversa, atendente)


@router.post("/conversas/grupo", response_model=ConversaRead, status_code=status.HTTP_201_CREATED)
def criar_conversa_grupo(
    body: ConversaGrupoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    try:
        conversa = chat_svc.criar_conversa_grupo(
            db,
            atendente.tenant_id,
            atendente,
            body.titulo,
            body.atendente_ids,
        )
        db.commit()
        db.refresh(conversa)
        return _to_conversa_read(db, conversa, atendente)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.patch("/conversas/{conversa_id}/participantes", response_model=ConversaRead)
def atualizar_participantes_grupo(
    conversa_id: int,
    body: GrupoParticipantesUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)
    try:
        conversa = chat_svc.atualizar_participantes_grupo(
            db,
            conversa,
            atendente,
            adicionar=body.adicionar,
            remover=body.remover,
            promover_admin=body.promover_admin,
            rebaixar_admin=body.rebaixar_admin,
        )
        db.commit()
        db.refresh(conversa)
        return _to_conversa_read(db, conversa, atendente)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.get("/conversas/{conversa_id}/mensagens", response_model=MensagensInternasPaginaRead)
def listar_mensagens(
    conversa_id: int,
    antes_de_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)

    rows, total, tem_mais_antigas = chat_svc.listar_mensagens(
        db, conversa_id, atendente.id, antes_de_id=antes_de_id
    )
    return MensagensInternasPaginaRead(
        items=[_to_mensagem_read(m, conversa=conversa, atendente=atendente, db=db) for m in rows],
        total=total,
        tem_mais_antigas=tem_mais_antigas,
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
        mensagem = chat_svc.enviar_mensagem(
            db,
            conversa,
            atendente,
            body.corpo,
            reply_to_message_id=body.reply_to_message_id,
            mencoes=[m.model_dump() for m in body.mencoes] if body.mencoes else None,
        )
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
    reply_to_message_id: int | None = Form(None),
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
            reply_to_message_id=reply_to_message_id,
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
    if not mensagem or not mensagem.storage_key or chat_svc.mensagem_esta_apagada(mensagem):
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
        mensagem = chat_svc.enviar_mensagem(
            db,
            conversa,
            atendente,
            body.corpo,
            reply_to_message_id=body.reply_to_message_id,
            mencoes=[m.model_dump() for m in body.mencoes] if body.mencoes else None,
        )
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
    reply_to_message_id: int | None = Form(None),
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
            reply_to_message_id=reply_to_message_id,
        )
        db.commit()
        db.refresh(mensagem)
        _emit_apos_mensagem(db, conversa, mensagem, atendente.id)
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.patch("/conversas/{conversa_id}/mensagens/{mensagem_id}", response_model=MensagemInternaRead)
def editar_mensagem(
    conversa_id: int,
    mensagem_id: int,
    body: MensagemInternaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)
    mensagem = _obter_mensagem_na_conversa(db, conversa_id, mensagem_id)
    try:
        chat_svc.editar_mensagem(
            db,
            conversa,
            mensagem,
            atendente,
            body.corpo,
            mencoes=[m.model_dump() for m in body.mencoes] if body.mencoes is not None else None,
        )
        db.commit()
        db.refresh(mensagem)
        _emit_mensagem_atualizada(db, conversa, mensagem, acao="editada")
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.delete("/conversas/{conversa_id}/mensagens/{mensagem_id}")
def apagar_mensagem(
    conversa_id: int,
    mensagem_id: int,
    escopo: Literal["todos", "para_mim"] = Query(
        "todos",
        description="todos = apagar para todos (até 5 min); para_mim = ocultar só para você",
    ),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)
    mensagem = _obter_mensagem_na_conversa(db, conversa_id, mensagem_id)
    try:
        resultado = chat_svc.apagar_mensagem(db, conversa, mensagem, atendente, escopo=escopo)
        db.commit()
        if escopo == "para_mim":
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        db.refresh(mensagem)
        _emit_mensagem_atualizada(db, conversa, mensagem, acao="apagada")
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.post("/conversas/{conversa_id}/limpar", status_code=status.HTTP_204_NO_CONTENT)
def limpar_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    try:
        chat_svc.limpar_conversa_para_atendente(db, conversa, atendente)
        db.commit()
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.put(
    "/conversas/{conversa_id}/mensagens/{mensagem_id}/reacoes",
    response_model=MensagemInternaRead,
)
def definir_reacao_mensagem(
    conversa_id: int,
    mensagem_id: int,
    body: ReacaoMensagemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)
    mensagem = _obter_mensagem_na_conversa(db, conversa_id, mensagem_id)
    try:
        chat_svc.definir_reacao_mensagem(db, conversa, mensagem, atendente, body.emoji)
        db.commit()
        db.refresh(mensagem)
        _emit_mensagem_atualizada(db, conversa, mensagem, acao="reacao")
        return _to_mensagem_read(mensagem, conversa=conversa, atendente=atendente, db=db)
    except chat_svc.ChatInternoErro as exc:
        raise _map_chat_erro(exc) from exc


@router.delete(
    "/conversas/{conversa_id}/mensagens/{mensagem_id}/reacoes",
    response_model=MensagemInternaRead,
)
def remover_reacao_mensagem(
    conversa_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    conversa = _obter_conversa_ou_404(db, conversa_id)
    if conversa.tenant_id != atendente.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    _exigir_acesso_conversa(db, atendente, conversa)
    mensagem = _obter_mensagem_na_conversa(db, conversa_id, mensagem_id)
    try:
        chat_svc.remover_reacao_mensagem(db, conversa, mensagem, atendente)
        db.commit()
        db.refresh(mensagem)
        _emit_mensagem_atualizada(db, conversa, mensagem, acao="reacao")
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
