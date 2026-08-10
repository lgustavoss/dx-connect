"""API admin SaaS — clientes / licenças DeskRudder (#522 / #524 / #528).

Só disponível quando `SAAS_CONTROL_PLANE=true` (instância comercial).
"""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import registrar_audit
from app.core.auth import exigir_saas_ops
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.cliente_saas import ClienteSaaS
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.saas import (
    ClienteSaaSConfirmarProvisionamento,
    ClienteSaaSCreate,
    ClienteSaaSRead,
    ClienteSaaSRegistrarInstancia,
    ClienteSaaSRenovar,
    ClienteSaaSUpdate,
    SaasResumoRead,
)
from app.services import saas_clientes as svc
from app.services import saas_renovacoes
from app.services.saas_resumo import obter_resumo

router = APIRouter(prefix="/saas", tags=["saas"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarClientesSaaSPor(str, Enum):
    nome = "nome"
    slug = "slug"
    status = "status"
    data_renovacao = "data_renovacao"


def exigir_saas_control_plane() -> None:
    if not settings.SAAS_CONTROL_PLANE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Painel SaaS não disponível nesta instância",
        )


def _http_from_saas(exc: svc.SaasErro) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _read(row: ClienteSaaS) -> ClienteSaaSRead:
    return ClienteSaaSRead.model_validate(svc.serializar_cliente(row))


@router.get("/resumo", response_model=SaasResumoRead)
def resumo(
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return obter_resumo(db)


@router.get("/clientes", response_model=ListaPaginada[ClienteSaaSRead])
def listar(
    busca: str | None = Query(None, description="Filtra por nome, slug ou e-mail de contacto"),
    status_filtro: str | None = Query(None, alias="status", description="Filtra por status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarClientesSaaSPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    q = db.query(ClienteSaaS)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(
            (ClienteSaaS.nome.ilike(term))
            | (ClienteSaaS.slug.ilike(term))
            | (ClienteSaaS.contato_email.ilike(term))
            | (ClienteSaaS.contato_nome.ilike(term))
        )
    if status_filtro and status_filtro.strip():
        q = q.filter(ClienteSaaS.status == status_filtro.strip().lower())
    total = q.count()
    if ordenar_por is None:
        order_cols = [ClienteSaaS.nome.asc(), ClienteSaaS.id.asc()]
    elif ordenar_por == OrdenarClientesSaaSPor.nome:
        order_cols = [expr_ordem(ClienteSaaS.nome, ordem), expr_ordem(ClienteSaaS.id, ordem)]
    elif ordenar_por == OrdenarClientesSaaSPor.slug:
        order_cols = [expr_ordem(ClienteSaaS.slug, ordem), expr_ordem(ClienteSaaS.id, ordem)]
    elif ordenar_por == OrdenarClientesSaaSPor.status:
        order_cols = [expr_ordem(ClienteSaaS.status, ordem), expr_ordem(ClienteSaaS.id, ordem)]
    else:
        order_cols = [expr_ordem(ClienteSaaS.data_renovacao, ordem), expr_ordem(ClienteSaaS.id, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_read(i) for i in items], total=total)


@router.post("/clientes", response_model=ClienteSaaSRead, status_code=201)
def criar(
    data: ClienteSaaSCreate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.criar(db, data)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.get("/clientes/{cliente_id}", response_model=ClienteSaaSRead)
def obter(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    try:
        return _read(svc.obter(db, cliente_id))
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e


@router.patch("/clientes/{cliente_id}", response_model=ClienteSaaSRead)
def atualizar(
    cliente_id: int,
    data: ClienteSaaSUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.atualizar(db, cliente_id, data)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/suspender", response_model=ClienteSaaSRead)
def suspender(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.suspender(db, cliente_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "suspender", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/reativar", response_model=ClienteSaaSRead)
def reativar(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.reativar(db, cliente_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "reativar", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/renovar", response_model=ClienteSaaSRead)
def renovar(
    cliente_id: int,
    data: ClienteSaaSRenovar,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_renovacoes.renovar(
            db,
            cliente_id,
            dias=data.dias,
            nova_data=data.nova_data,
        )
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "renovar", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/registrar-instancia", response_model=ClienteSaaSRead)
def registrar_instancia(
    cliente_id: int,
    data: ClienteSaaSRegistrarInstancia,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.registrar_instancia(db, cliente_id, data)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "registrar_instancia", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/solicitar-provisionamento", response_model=ClienteSaaSRead)
def solicitar_provisionamento(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.solicitar_provisionamento(db, cliente_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "solicitar_provisionamento", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/confirmar-provisionamento", response_model=ClienteSaaSRead)
def confirmar_provisionamento(
    cliente_id: int,
    data: ClienteSaaSConfirmarProvisionamento | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    body = data or ClienteSaaSConfirmarProvisionamento()
    try:
        row = svc.confirmar_provisionamento(db, cliente_id, instancia_url=body.instancia_url)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "confirmar_provisionamento", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)
