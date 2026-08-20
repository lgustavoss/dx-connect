"""API de controle de ponto (#761 / #766 / #767 / #768)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import exigir_admin, obter_atendente_atual
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.ponto import (
    PontoAjusteCreate,
    PontoAjusteUpdate,
    PontoAnularBody,
    PontoBatidaAdminItem,
    PontoBatidaRead,
    PontoBaterRequest,
    PontoCalendarioRead,
    PontoEstadoRead,
    PontoHistoricoRead,
    PontoHojeRead,
)
from app.services import ponto as ponto_svc

router = APIRouter(prefix="/ponto", tags=["ponto"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/bater", response_model=PontoBatidaRead)
def bater_ponto(
    data: PontoBaterRequest,
    request: Request,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    ip, ua = _client_meta(request)
    batida = ponto_svc.bater(
        db,
        atendente,
        data.tipo,
        origem=data.origem,
        ip=ip,
        user_agent=ua,
    )
    return PontoBatidaRead.model_validate(batida)


@router.get("/me", response_model=PontoEstadoRead)
def meu_estado(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return ponto_svc.estado_atual(db, atendente)


@router.get("/me/batidas", response_model=PontoHistoricoRead)
def meu_historico(
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return ponto_svc.historico(db, atendente, desde=desde, ate=ate, offset=offset, limit=limit)


@router.get("/me/calendario", response_model=PontoCalendarioRead)
def meu_calendario(
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ponto_svc.exigir_acesso_ponto(atendente)
    return ponto_svc.calendario(db, atendente, ano, mes)


@router.get("/batidas/export.csv")
def exportar_csv(
    atendente_id: int | None = Query(None),
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    conteudo = ponto_svc.export_csv_admin(
        db, admin, atendente_id=atendente_id, desde=desde, ate=ate
    )
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ponto_batidas.csv"'},
    )


@router.get("/batidas", response_model=ListaPaginada[PontoBatidaAdminItem])
def listar_batidas_admin(
    atendente_id: int | None = Query(None),
    desde: date | None = Query(None),
    ate: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    itens, total = ponto_svc.listar_batidas_admin(
        db,
        admin,
        atendente_id=atendente_id,
        desde=desde,
        ate=ate,
        offset=offset,
        limit=limit,
    )
    return ListaPaginada(items=itens, total=total)


@router.post("/batidas", response_model=PontoBatidaRead, status_code=201)
def criar_batida_admin(
    data: PontoAjusteCreate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    batida = ponto_svc.admin_criar_batida(
        db,
        admin,
        atendente_id=data.atendente_id,
        tipo=data.tipo,
        registrado_em=data.registrado_em,
        motivo=data.motivo.strip(),
    )
    return PontoBatidaRead.model_validate(batida)


@router.patch("/batidas/{batida_id}", response_model=PontoBatidaRead)
def atualizar_batida_admin(
    batida_id: int,
    data: PontoAjusteUpdate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    batida = ponto_svc.admin_atualizar_batida(
        db,
        admin,
        batida_id,
        tipo=data.tipo,
        registrado_em=data.registrado_em,
        motivo=data.motivo.strip(),
    )
    return PontoBatidaRead.model_validate(batida)


@router.post("/batidas/{batida_id}/anular", response_model=PontoBatidaRead)
def anular_batida_admin(
    batida_id: int,
    data: PontoAnularBody,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    batida = ponto_svc.admin_anular_batida(db, admin, batida_id, motivo=data.motivo.strip())
    return PontoBatidaRead.model_validate(batida)


@router.get("/calendario", response_model=PontoCalendarioRead)
def calendario_admin(
    atendente_id: int = Query(...),
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    alvo = (
        db.query(Atendente)
        .filter(Atendente.id == atendente_id, Atendente.tenant_id == admin.tenant_id)
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    return ponto_svc.calendario(db, alvo, ano, mes)


@router.get("/hoje", response_model=PontoHojeRead)
def visao_hoje(
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    return ponto_svc.visao_hoje(db, admin)
