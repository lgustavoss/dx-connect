"""Galeria pessoal de figurinhas do atendente (#S202610-0001)."""

from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.whatsapp_chats import _pode_ver_chat
from app.core.auth import obter_atendente_atual
from app.database import get_db
from app.models.atendente import Atendente
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.models.whatsapp_figurinha_favorita import WhatsappFigurinhaFavorita
from app.services import whatsapp_media_retencao as wpp_midia_retencao
from app.services.whatsapp_media_storage import (
    caminho_absoluto_arquivo,
    gravar_bytes_em_disco,
    remover_arquivo_local,
)

router = APIRouter(prefix="/whatsapp/figurinhas", tags=["whatsapp-figurinhas"])

MAX_FIGURINHAS_POR_ATENDENTE = 300


class FigurinhaFavoritaRead(BaseModel):
    id: int
    mimetype: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FigurinhaDeMensagemCreate(BaseModel):
    chat_id: int
    mensagem_id: int


def _da_galeria(db: Session, atendente: Atendente, figurinha_id: int) -> WhatsappFigurinhaFavorita:
    f = (
        db.query(WhatsappFigurinhaFavorita)
        .filter(
            WhatsappFigurinhaFavorita.id == figurinha_id,
            WhatsappFigurinhaFavorita.atendente_id == atendente.id,
        )
        .first()
    )
    if not f:
        raise HTTPException(status_code=404, detail="Figurinha não encontrada")
    return f


@router.get("", response_model=list[FigurinhaFavoritaRead])
def listar_figurinhas(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return (
        db.query(WhatsappFigurinhaFavorita)
        .filter(WhatsappFigurinhaFavorita.atendente_id == atendente.id)
        .order_by(WhatsappFigurinhaFavorita.created_at.desc(), WhatsappFigurinhaFavorita.id.desc())
        .all()
    )


@router.post("/de-mensagem", response_model=FigurinhaFavoritaRead)
def salvar_figurinha_de_mensagem(
    body: FigurinhaDeMensagemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == body.chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if not _pode_ver_chat(db, atendente, c):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este chat")
    m = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == c.id, WhatsappMensagem.id == body.mensagem_id)
        .first()
    )
    if not m or m.tipo_midia != "figurinha":
        raise HTTPException(status_code=404, detail="Figurinha não encontrada nesta conversa")
    try:
        origem = wpp_midia_retencao.obter_arquivo_midia(db, m, c)
    except wpp_midia_retencao.MidiaIndisponivelErro:
        raise HTTPException(status_code=410, detail=wpp_midia_retencao.MSG_MIDIA_INDISPONIVEL)
    except wpp_midia_retencao.MidiaTemporariamenteIndisponivelErro:
        raise HTTPException(status_code=503, detail=wpp_midia_retencao.MSG_MIDIA_TEMPORARIA)

    data = origem.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    existente = (
        db.query(WhatsappFigurinhaFavorita)
        .filter(WhatsappFigurinhaFavorita.atendente_id == atendente.id, WhatsappFigurinhaFavorita.sha256 == sha)
        .first()
    )
    if existente:
        return existente
    total = db.query(WhatsappFigurinhaFavorita).filter(WhatsappFigurinhaFavorita.atendente_id == atendente.id).count()
    if total >= MAX_FIGURINHAS_POR_ATENDENTE:
        raise HTTPException(
            status_code=400,
            detail=f"Sua galeria já tem {MAX_FIGURINHAS_POR_ATENDENTE} figurinhas. Remova alguma para adicionar outra.",
        )
    mimetype = (m.mimetype or "image/webp").split(";")[0].strip()
    nome = gravar_bytes_em_disco(data, mimetype)
    if not nome:
        raise HTTPException(status_code=500, detail="Não foi possível salvar a figurinha.")
    f = WhatsappFigurinhaFavorita(atendente_id=atendente.id, arquivo_nome=nome, mimetype=mimetype, sha256=sha)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@router.get("/{figurinha_id}/arquivo")
def obter_arquivo_figurinha(
    figurinha_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    f = _da_galeria(db, atendente, figurinha_id)
    path = caminho_absoluto_arquivo(f.arquivo_nome)
    if not path:
        raise HTTPException(status_code=410, detail="Arquivo da figurinha não está mais disponível.")
    return FileResponse(path, media_type=f.mimetype, filename=f"figurinha-{f.id}{path.suffix}")


@router.delete("/{figurinha_id}", status_code=204)
def remover_figurinha(
    figurinha_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    f = _da_galeria(db, atendente, figurinha_id)
    nome = f.arquivo_nome
    db.delete(f)
    db.commit()
    remover_arquivo_local(nome)
