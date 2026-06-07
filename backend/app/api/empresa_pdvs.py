from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, obter_atendente_atual
from app.database import get_db
from app.models import Empresa
from app.models.atendente import Atendente
from app.models.empresa_pdv import EmpresaPdv, PdvRotulo, PdvTipoAcessoRemoto
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.pdv import (
    EmpresaPdvCreate,
    EmpresaPdvCredencialRead,
    EmpresaPdvRead,
    EmpresaPdvUpdate,
)
from app.services.empresa_pdv_rules import validar_papel_principal_auxiliar
from app.services.secret_box import decrypt_str, encrypt_str

router = APIRouter(prefix="/empresas", tags=["empresa-pdvs"])


def _empresa_or_404(db: Session, empresa_id: int) -> Empresa:
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    return emp


def _to_read(row: EmpresaPdv) -> EmpresaPdvRead:
    return EmpresaPdvRead(
        id=row.id,
        empresa_id=row.empresa_id,
        codigo=row.codigo,
        rotulo_id=row.rotulo_id,
        rotulo_nome=row.rotulo.nome if row.rotulo else None,
        papel=row.papel,
        usa_tef=bool(row.usa_tef),
        tipo_acesso_remoto_id=row.tipo_acesso_remoto_id,
        tipo_acesso_remoto_nome=row.tipo_acesso_remoto.nome if row.tipo_acesso_remoto else None,
        acesso_remoto_id=row.acesso_remoto_id,
        observacoes=row.observacoes,
        ativo=bool(row.ativo),
        tem_senha_remota=bool(row.acesso_remoto_senha_cifrada),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validar_refs(db: Session, data: EmpresaPdvCreate | EmpresaPdvUpdate, empresa_id: int) -> None:
    rotulo_id = getattr(data, "rotulo_id", None)
    if rotulo_id is not None:
        rot = db.query(PdvRotulo).filter(PdvRotulo.id == rotulo_id, PdvRotulo.ativo.is_(True)).first()
        if not rot:
            raise HTTPException(status_code=400, detail="Rótulo de dispositivo inválido ou inativo.")
    tipo_id = getattr(data, "tipo_acesso_remoto_id", None)
    if tipo_id is not None:
        tipo = (
            db.query(PdvTipoAcessoRemoto)
            .filter(PdvTipoAcessoRemoto.id == tipo_id, PdvTipoAcessoRemoto.ativo.is_(True))
            .first()
        )
        if not tipo:
            raise HTTPException(status_code=400, detail="Tipo de acesso remoto inválido ou inativo.")


@router.get("/{empresa_id}/pdvs", response_model=ListaPaginada[EmpresaPdvRead])
def listar_pdvs(
    empresa_id: int,
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    _empresa_or_404(db, empresa_id)
    q = (
        db.query(EmpresaPdv)
        .options(joinedload(EmpresaPdv.rotulo), joinedload(EmpresaPdv.tipo_acesso_remoto))
        .filter(EmpresaPdv.empresa_id == empresa_id)
    )
    if not incluir_inativos:
        q = q.filter(EmpresaPdv.ativo.is_(True))
    rows = q.order_by(EmpresaPdv.codigo.asc(), EmpresaPdv.id.asc()).all()
    return ListaPaginada(items=[_to_read(r) for r in rows], total=len(rows))


@router.post("/{empresa_id}/pdvs", response_model=EmpresaPdvRead, status_code=201)
def criar_pdv(
    empresa_id: int,
    data: EmpresaPdvCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _empresa_or_404(db, empresa_id)
    _validar_refs(db, data, empresa_id)
    codigo = data.codigo.strip()
    if db.query(EmpresaPdv).filter(EmpresaPdv.empresa_id == empresa_id, EmpresaPdv.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Já existe um PDV com este código nesta empresa.")
    senha_cifrada = None
    if data.acesso_remoto_senha and data.acesso_remoto_senha.strip():
        senha_cifrada = encrypt_str(data.acesso_remoto_senha.strip())
    row = EmpresaPdv(
        empresa_id=empresa_id,
        codigo=codigo,
        rotulo_id=data.rotulo_id,
        papel=data.papel,
        usa_tef=data.usa_tef,
        tipo_acesso_remoto_id=data.tipo_acesso_remoto_id,
        acesso_remoto_id=(data.acesso_remoto_id or "").strip() or None,
        acesso_remoto_senha_cifrada=senha_cifrada,
        observacoes=(data.observacoes or "").strip() or None,
        ativo=data.ativo,
    )
    db.add(row)
    db.flush()
    try:
        validar_papel_principal_auxiliar(db, empresa_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    registrar_audit(db, "empresa_pdv", row.id, "create", atendente.id)
    db.commit()
    row = (
        db.query(EmpresaPdv)
        .options(joinedload(EmpresaPdv.rotulo), joinedload(EmpresaPdv.tipo_acesso_remoto))
        .filter(EmpresaPdv.id == row.id)
        .first()
    )
    return _to_read(row)


@router.patch("/{empresa_id}/pdvs/{pdv_id}", response_model=EmpresaPdvRead)
def atualizar_pdv(
    empresa_id: int,
    pdv_id: int,
    data: EmpresaPdvUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _empresa_or_404(db, empresa_id)
    row = (
        db.query(EmpresaPdv)
        .options(joinedload(EmpresaPdv.rotulo), joinedload(EmpresaPdv.tipo_acesso_remoto))
        .filter(EmpresaPdv.id == pdv_id, EmpresaPdv.empresa_id == empresa_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="PDV não encontrado")
    payload = data.model_dump(exclude_unset=True)
    senha = payload.pop("acesso_remoto_senha", None)
    _validar_refs(db, data, empresa_id)
    for k, v in payload.items():
        setattr(row, k, v)
    if senha is not None:
        row.acesso_remoto_senha_cifrada = encrypt_str(senha.strip()) if senha.strip() else None
    db.flush()
    try:
        validar_papel_principal_auxiliar(db, empresa_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    registrar_audit(db, "empresa_pdv", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return _to_read(row)


@router.get("/{empresa_id}/pdvs/{pdv_id}/credencial", response_model=EmpresaPdvCredencialRead)
def revelar_credencial(
    empresa_id: int,
    pdv_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _empresa_or_404(db, empresa_id)
    row = db.query(EmpresaPdv).filter(EmpresaPdv.id == pdv_id, EmpresaPdv.empresa_id == empresa_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="PDV não encontrado")
    if not row.acesso_remoto_senha_cifrada:
        raise HTTPException(status_code=404, detail="Este PDV não possui senha cadastrada.")
    try:
        senha = decrypt_str(row.acesso_remoto_senha_cifrada)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Não foi possível decifrar a credencial.") from e
    registrar_audit(db, "empresa_pdv", row.id, "reveal_credential", atendente.id)
    db.commit()
    return EmpresaPdvCredencialRead(acesso_remoto_senha=senha)
