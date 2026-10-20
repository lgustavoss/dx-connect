from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import exigir_permissao
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.rustdesk import (
    RustdeskConfiguracaoRead,
    RustdeskDesvincularIn,
    RustdeskDesvincularOut,
    RustdeskExcluirOut,
    RustdeskListaRead,
    RustdeskVincularIn,
    RustdeskVincularOut,
)
from app.services import rustdesk_peers as svc

router = APIRouter(prefix="/rustdesk", tags=["rustdesk"])

_FILTROS = {"todos", "online", "offline", "sem_vinculo", "vinculado"}


@router.get("/configuracao", response_model=RustdeskConfiguracaoRead)
def ler_configuracao(
    _: Atendente = Depends(exigir_permissao("rustdesk.monitorar")),
):
    return svc.configuracao_cliente()


@router.get("/peers", response_model=RustdeskListaRead)
def listar_peers(
    filtro: str = Query("todos"),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_permissao("rustdesk.monitorar")),
):
    if filtro not in _FILTROS:
        filtro = "todos"
    return svc.listar(db, filtro)


@router.post("/peers/{rustdesk_id}/vincular", response_model=RustdeskVincularOut)
def vincular_peer(
    rustdesk_id: str,
    body: RustdeskVincularIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("empresas.editar")),
):
    return svc.vincular(db, rustdesk_id, body.pdv_id, body.confirmar_substituicao, atendente)


@router.post("/peers/{rustdesk_id}/desvincular", response_model=RustdeskDesvincularOut)
def desvincular_peer(
    rustdesk_id: str,
    body: RustdeskDesvincularIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("empresas.editar")),
):
    return svc.desvincular(db, rustdesk_id, body.pdv_id, atendente)


@router.post("/peers/{rustdesk_id}/excluir", response_model=RustdeskExcluirOut)
def excluir_peer(
    rustdesk_id: str,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("empresas.editar")),
):
    return svc.excluir(db, rustdesk_id, atendente)
