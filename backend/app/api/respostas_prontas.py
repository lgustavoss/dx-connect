from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, obter_atendente_atual
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.database import get_db
from app.models import RespostaPronta, Setor
from app.models.atendente import Atendente
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.resposta_pronta import (
    RespostaProntaCreate,
    RespostaProntaRead,
    RespostaProntaUpdate,
)

router = APIRouter(prefix="/respostas-prontas", tags=["respostas-prontas"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarRespostasProntasPor(str, Enum):
    titulo = "titulo"
    ordem = "ordem"
    ativo = "ativo"


def _to_read(row: RespostaPronta) -> RespostaProntaRead:
    return RespostaProntaRead(
        id=row.id,
        titulo=row.titulo,
        corpo=row.corpo,
        setor_id=row.setor_id,
        setor_nome=row.setor.nome if row.setor else None,
        ordem=int(row.ordem or 0),
        ativo=bool(row.ativo),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validar_setor(db: Session, tenant_id: int, setor_id: int | None) -> None:
    if setor_id is None:
        return
    setor = (
        db.query(Setor)
        .filter(Setor.id == setor_id, Setor.tenant_id == tenant_id, Setor.ativo.is_(True))
        .first()
    )
    if not setor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setor inválido.")


def _assert_acesso_setor(atendente: Atendente, db: Session, setor_id: int) -> None:
    if atendente.role == "admin":
        return
    vis = ids_setores_visiveis_atendente(db, atendente)
    if setor_id not in vis:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor.")


@router.get("/disponiveis", response_model=list[RespostaProntaRead])
def listar_disponiveis(
    setor_id: int = Query(..., description="Setor do ticket"),
    busca: str | None = Query(None, description="Filtra por título ou corpo"),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    _assert_acesso_setor(atendente, db, setor_id)
    q = (
        db.query(RespostaPronta)
        .options(joinedload(RespostaPronta.setor))
        .filter(
            RespostaPronta.tenant_id == atendente.tenant_id,
            RespostaPronta.ativo.is_(True),
            or_(RespostaPronta.setor_id.is_(None), RespostaPronta.setor_id == setor_id),
        )
    )
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(RespostaPronta.titulo.ilike(term), RespostaPronta.corpo.ilike(term)))
    rows = q.order_by(RespostaPronta.ordem.asc(), RespostaPronta.titulo.asc(), RespostaPronta.id.asc()).all()
    return [_to_read(r) for r in rows]


@router.get("", response_model=ListaPaginada[RespostaProntaRead])
def listar(
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    setor_id: int | None = Query(None, description="Filtrar por setor; omitir = todos"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarRespostasProntasPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    q = db.query(RespostaPronta).options(joinedload(RespostaPronta.setor))
    if not incluir_inativos:
        q = q.filter(RespostaPronta.ativo.is_(True))
    if setor_id is not None:
        q = q.filter(or_(RespostaPronta.setor_id.is_(None), RespostaPronta.setor_id == setor_id))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(RespostaPronta.titulo.ilike(term), RespostaPronta.corpo.ilike(term)))
    total = q.count()
    if ordenar_por is None:
        order_cols = [RespostaPronta.ordem.asc(), RespostaPronta.titulo.asc(), RespostaPronta.id.asc()]
    elif ordenar_por == OrdenarRespostasProntasPor.titulo:
        order_cols = [expr_ordem(RespostaPronta.titulo, ordem), expr_ordem(RespostaPronta.id, ordem)]
    elif ordenar_por == OrdenarRespostasProntasPor.ordem:
        order_cols = [expr_ordem(RespostaPronta.ordem, ordem), expr_ordem(RespostaPronta.id, ordem)]
    else:
        order_cols = [expr_ordem(RespostaPronta.ativo, ordem), expr_ordem(RespostaPronta.id, ordem)]
    rows = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_to_read(r) for r in rows], total=total)


@router.post("", response_model=RespostaProntaRead, status_code=201)
def criar(
    data: RespostaProntaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _validar_setor(db, atendente.tenant_id, data.setor_id)
    row = RespostaPronta(
        tenant_id=atendente.tenant_id,
        setor_id=data.setor_id,
        titulo=data.titulo.strip(),
        corpo=data.corpo,
        ordem=data.ordem,
        ativo=data.ativo,
    )
    db.add(row)
    db.flush()
    registrar_audit(db, "resposta_pronta", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    row = (
        db.query(RespostaPronta)
        .options(joinedload(RespostaPronta.setor))
        .filter(RespostaPronta.id == row.id)
        .first()
    )
    return _to_read(row)


@router.get("/{resposta_id}", response_model=RespostaProntaRead)
def obter(
    resposta_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = (
        db.query(RespostaPronta)
        .options(joinedload(RespostaPronta.setor))
        .filter(RespostaPronta.id == resposta_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta pronta não encontrada.")
    return _to_read(row)


@router.patch("/{resposta_id}", response_model=RespostaProntaRead)
def atualizar(
    resposta_id: int,
    data: RespostaProntaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(RespostaPronta).filter(RespostaPronta.id == resposta_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta pronta não encontrada.")
    payload = data.model_dump(exclude_unset=True)
    if "setor_id" in payload:
        _validar_setor(db, atendente.tenant_id, payload["setor_id"])
    if "titulo" in payload and payload["titulo"] is not None:
        payload["titulo"] = payload["titulo"].strip()
    for k, v in payload.items():
        setattr(row, k, v)
    registrar_audit(db, "resposta_pronta", row.id, "update", atendente.id)
    db.commit()
    row = (
        db.query(RespostaPronta)
        .options(joinedload(RespostaPronta.setor))
        .filter(RespostaPronta.id == row.id)
        .first()
    )
    return _to_read(row)


@router.delete("/{resposta_id}", status_code=204)
def excluir(
    resposta_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(RespostaPronta).filter(RespostaPronta.id == resposta_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta pronta não encontrada.")
    registrar_audit(db, "resposta_pronta", row.id, "delete", atendente.id)
    db.delete(row)
    db.commit()
