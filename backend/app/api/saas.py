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
    ClienteSaaSAprovar,
    ClienteSaaSConfirmarProvisionamento,
    ClienteSaaSCreate,
    ClienteSaaSRead,
    ClienteSaaSRegistrarInstancia,
    ClienteSaaSRejeitar,
    ClienteSaaSRenovar,
    ClienteSaaSUpdate,
    SaasModuloCreate,
    SaasModuloRead,
    SaasModuloUpdate,
    SaasPlanoCreate,
    SaasPlanoRead,
    SaasPlanoUpdate,
    SaasResumoRead,
    SaasTimelineEvent,
)
from app.schemas.system import ReleaseNotesRead
from app.schemas.saas_solicitacao import ClienteSaaSIngestTokenRead
from app.services import saas_aprovacao
from app.services import saas_catalogo
from app.services import saas_clientes as svc
from app.services import saas_renovacoes
from app.services.saas_resumo import obter_resumo
from app.services.system_release import release_notes_payload

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


@router.get("/release-notes", response_model=ReleaseNotesRead)
def obter_saas_release_notes(
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    """Notas da versão — todos os bullets, com ``product`` para tags (#920)."""
    return ReleaseNotesRead(**release_notes_payload(product=None))


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
    plano_id: int | None = Query(None, description="Filtra por plano comercial"),
    aprovacao_status: str | None = Query(None, description="pendente | aprovado | rejeitado"),
    provisionamento_status: str | None = Query(
        None, description="pendente | em_progresso | aguardando_ops | sucesso | falha"
    ),
    provisionamento_fila: bool | None = Query(
        None, description="true = estados de fila (pendente/em_progresso/aguardando_ops/falha)"
    ),
    vencendo: bool | None = Query(None, description="true = renovação dentro da janela de alerta"),
    vencidas: bool | None = Query(None, description="true = renovação já passou (trial/ativo)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarClientesSaaSPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    from datetime import date, timedelta

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
    if plano_id is not None:
        q = q.filter(ClienteSaaS.plano_id == plano_id)
    if aprovacao_status and aprovacao_status.strip():
        q = q.filter(ClienteSaaS.aprovacao_status == aprovacao_status.strip().lower())
    if provisionamento_fila:
        q = q.filter(
            ClienteSaaS.provisionamento_status.in_(
                ("pendente", "em_progresso", "aguardando_ops", "falha")
            )
        )
    elif provisionamento_status and provisionamento_status.strip():
        q = q.filter(ClienteSaaS.provisionamento_status == provisionamento_status.strip().lower())

    if vencendo or vencidas:
        hoje = date.today()
        q = q.filter(
            ClienteSaaS.status.in_(("trial", "ativo")),
            ClienteSaaS.data_renovacao.isnot(None),
        )
        if vencendo:
            janela = max(1, int(settings.SAAS_RENEWAL_ALERT_DAYS_BEFORE or 14))
            limite = hoje + timedelta(days=janela)
            q = q.filter(ClienteSaaS.data_renovacao >= hoje, ClienteSaaS.data_renovacao <= limite)
        if vencidas:
            q = q.filter(ClienteSaaS.data_renovacao < hoje)

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


@router.get("/clientes/{cliente_id}/timeline", response_model=list[SaasTimelineEvent])
def timeline_cliente(
    cliente_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    try:
        svc.obter(db, cliente_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    from app.services import saas_catalogo

    return [SaasTimelineEvent.model_validate(e) for e in saas_catalogo.listar_timeline(db, cliente_id, limit=limit)]


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


@router.post(
    "/clientes/{cliente_id}/gerar-token-ingest",
    response_model=ClienteSaaSIngestTokenRead,
)
def gerar_token_ingest(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    """Gera (ou roda) o token instância→SaaS. O plaintext só sai nesta resposta."""
    from app.services.saas_solicitacao_ingest import (
        garantir_token_e_escrever_env,
        ingest_url_publica,
    )

    try:
        row = svc.obter(db, cliente_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    token = garantir_token_e_escrever_env(row, forcar_novo=True)
    registrar_audit(db, "cliente_saas", cliente_id, "gerar_token_ingest", atendente.id)
    db.commit()
    db.refresh(row)
    return ClienteSaaSIngestTokenRead(
        slug=row.slug,
        token=token or "",
        ingest_url=ingest_url_publica(),
        ingest_token_configurado=True,
    )


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


@router.post("/clientes/{cliente_id}/aprovar", response_model=ClienteSaaSRead)
def aprovar(
    cliente_id: int,
    data: ClienteSaaSAprovar | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    body = data or ClienteSaaSAprovar()
    try:
        row = saas_aprovacao.aprovar(
            db,
            cliente_id,
            notas=body.notas,
            ativar=body.ativar,
            provisionar=body.provisionar,
            plano_id=body.plano_id,
        )
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "aprovar", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/rejeitar", response_model=ClienteSaaSRead)
def rejeitar(
    cliente_id: int,
    data: ClienteSaaSRejeitar | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    body = data or ClienteSaaSRejeitar()
    try:
        row = saas_aprovacao.rejeitar(db, cliente_id, notas=body.notas)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "rejeitar", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/confirmar-stack", response_model=ClienteSaaSRead)
def confirmar_stack(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.confirmar_stack(db, cliente_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "confirmar_stack", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/clientes/{cliente_id}/reenviar-entrega", response_model=ClienteSaaSRead)
def reenviar_entrega(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = svc.reenviar_entrega(db, cliente_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "cliente_saas", cliente_id, "reenviar_entrega", atendente.id)
    db.commit()
    db.refresh(row)
    return _read(row)


def _read_plano(row) -> SaasPlanoRead:
    return SaasPlanoRead.model_validate(saas_catalogo.serializar_plano(row))


@router.get("/planos", response_model=list[SaasPlanoRead])
def listar_planos(
    ativo: bool | None = Query(None, description="Filtra por activo/inactivo"),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return [_read_plano(p) for p in saas_catalogo.listar_planos(db, ativo=ativo)]


@router.post("/planos", response_model=SaasPlanoRead, status_code=201)
def criar_plano(
    data: SaasPlanoCreate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.criar_plano(db, data)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_plano", row.id, "create", atendente.id)
    db.commit()
    return _read_plano(saas_catalogo.obter_plano(db, row.id))


@router.get("/planos/{plano_id}", response_model=SaasPlanoRead)
def obter_plano(
    plano_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    try:
        return _read_plano(saas_catalogo.obter_plano(db, plano_id))
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e


@router.patch("/planos/{plano_id}", response_model=SaasPlanoRead)
def atualizar_plano(
    plano_id: int,
    data: SaasPlanoUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.atualizar_plano(db, plano_id, data)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_plano", plano_id, "update", atendente.id)
    db.commit()
    return _read_plano(row)


@router.post("/planos/{plano_id}/ativar", response_model=SaasPlanoRead)
def ativar_plano(
    plano_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.ativar_plano(db, plano_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_plano", plano_id, "ativar", atendente.id)
    db.commit()
    return _read_plano(row)


@router.post("/planos/{plano_id}/desativar", response_model=SaasPlanoRead)
def desativar_plano(
    plano_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.desativar_plano(db, plano_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_plano", plano_id, "desativar", atendente.id)
    db.commit()
    return _read_plano(row)


@router.get("/modulos", response_model=list[SaasModuloRead])
def listar_modulos(
    ativo: bool | None = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return [SaasModuloRead.model_validate(m) for m in saas_catalogo.listar_modulos(db, ativo=ativo)]


@router.post("/modulos", response_model=SaasModuloRead, status_code=201)
def criar_modulo(
    data: SaasModuloCreate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.criar_modulo(db, data)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_modulo", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return SaasModuloRead.model_validate(row)


@router.get("/modulos/{modulo_id}", response_model=SaasModuloRead)
def obter_modulo(
    modulo_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    try:
        return SaasModuloRead.model_validate(saas_catalogo.obter_modulo(db, modulo_id))
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e


@router.patch("/modulos/{modulo_id}", response_model=SaasModuloRead)
def atualizar_modulo(
    modulo_id: int,
    data: SaasModuloUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.atualizar_modulo(db, modulo_id, data)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_modulo", modulo_id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return SaasModuloRead.model_validate(row)


@router.post("/modulos/{modulo_id}/ativar", response_model=SaasModuloRead)
def ativar_modulo(
    modulo_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.ativar_modulo(db, modulo_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_modulo", modulo_id, "ativar", atendente.id)
    db.commit()
    db.refresh(row)
    return SaasModuloRead.model_validate(row)


@router.post("/modulos/{modulo_id}/desativar", response_model=SaasModuloRead)
def desativar_modulo(
    modulo_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    try:
        row = saas_catalogo.desativar_modulo(db, modulo_id)
    except svc.SaasErro as e:
        raise _http_from_saas(e) from e
    registrar_audit(db, "saas_modulo", modulo_id, "desativar", atendente.id)
    db.commit()
    db.refresh(row)
    return SaasModuloRead.model_validate(row)
