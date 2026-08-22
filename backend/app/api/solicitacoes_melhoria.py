"""API de solicitações de melhoria (#799 / #800–#807)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import exigir_admin, obter_atendente_atual
from app.models.atendente import Atendente
from app.schemas.solicitacao_melhoria import (
    SolicitacaoAnexoRead,
    SolicitacaoComentarioCreate,
    SolicitacaoMelhoriaCreate,
    SolicitacaoMelhoriaListaItem,
    SolicitacaoMelhoriaRead,
    SolicitacaoMelhoriaStatusUpdate,
)
from app.services import solicitacao_melhoria as svc
from app.services import solicitacao_melhoria_github as gh_svc
from app.services import solicitacao_melhoria_media as media

router = APIRouter(prefix="/solicitacoes-melhoria", tags=["solicitacoes-melhoria"])

_MIME_INLINE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}


def _file_response(path: Path, nome: str, content_type: str | None) -> FileResponse:
    ext = path.suffix.lower()
    mt = (content_type or "").split(";", 1)[0].strip() or _MIME_INLINE.get(ext, "application/octet-stream")
    inline = mt.startswith("image/") or mt.startswith("video/") or mt == "application/pdf"
    return FileResponse(
        path=str(path),
        media_type=mt,
        filename=nome,
        content_disposition_type="inline" if inline else "attachment",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/media", response_model=SolicitacaoAnexoRead, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    papel: str = Form("anexo"),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    data = await file.read()
    row = svc.guardar_media(
        db,
        atendente,
        data=data,
        filename=file.filename,
        content_type=file.content_type,
        papel=papel,
    )
    return svc._anexo_read(row)


@router.get("/media/{storage_key}")
def servir_media(storage_key: str, db: Session = Depends(get_db)):
    """UUID no path é o segredo; necessário para <img> no markdown (sem header Authorization)."""
    row = svc.obter_anexo_por_storage(db, storage_key)
    if not row:
        from app.services.saas_solicitacao_ingest import obter_anexo_saas_por_storage

        row = obter_anexo_saas_por_storage(db, storage_key)
    if not row:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado")
    p = media.caminho_absoluto(row.storage_key)
    if not p:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado no disco")
    return _file_response(p, row.nome_original, row.content_type)


@router.post("", response_model=SolicitacaoMelhoriaRead)
def criar_solicitacao(
    data: SolicitacaoMelhoriaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = svc.criar(db, atendente, data)
    return svc.serializar(row, incluir_github=False, incluir_internos=False)


@router.get("/minhas", response_model=list[SolicitacaoMelhoriaListaItem])
def listar_minhas(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    rows = svc.listar_minhas(db, atendente)
    return [svc.item_lista(r, incluir_github=False) for r in rows]


@router.get("/admin", response_model=list[SolicitacaoMelhoriaListaItem])
def listar_admin(
    status: str | None = Query(None),
    tipo: str | None = Query(None),
    organizacao_id: int | None = Query(None),
    desde: datetime | None = Query(None),
    ate: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rows = svc.listar_admin(
        db, status_filtro=status, tipo=tipo, organizacao_id=organizacao_id, desde=desde, ate=ate
    )
    return [svc.item_lista(r, incluir_github=True) for r in rows]


@router.get("/{solicitacao_id}", response_model=SolicitacaoMelhoriaRead)
def obter(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = svc.obter_para_leitura(db, solicitacao_id, atendente)
    admin = atendente.role == "admin"
    return svc.serializar(row, incluir_github=admin, incluir_internos=admin)


@router.patch("/{solicitacao_id}/status", response_model=SolicitacaoMelhoriaRead)
def alterar_status(
    solicitacao_id: int,
    data: SolicitacaoMelhoriaStatusUpdate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    row = svc.alterar_status(db, solicitacao_id, admin, data)
    return svc.serializar(row, incluir_github=True, incluir_internos=True)


@router.post("/{solicitacao_id}/comentarios", response_model=SolicitacaoMelhoriaRead)
def comentar(
    solicitacao_id: int,
    data: SolicitacaoComentarioCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = svc.adicionar_comentario(db, solicitacao_id, atendente, data)
    admin = atendente.role == "admin"
    return svc.serializar(row, incluir_github=admin, incluir_internos=admin)


@router.post("/{solicitacao_id}/github", response_model=SolicitacaoMelhoriaRead)
def criar_github(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    row = svc.obter_para_leitura(db, solicitacao_id, admin)
    row = gh_svc.criar_issue(db, row, admin)
    return svc.serializar(row, incluir_github=True, incluir_internos=True)


@router.post("/{solicitacao_id}/github/sincronizar", response_model=SolicitacaoMelhoriaRead)
def sync_github(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    row = svc.obter_para_leitura(db, solicitacao_id, admin)
    row = gh_svc.sincronizar_issue(db, row, admin)
    return svc.serializar(row, incluir_github=True, incluir_internos=True)
