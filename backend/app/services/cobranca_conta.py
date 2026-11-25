"""Contas bancárias de cobrança na instância do cliente (#1392)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.boleto_pool import CobrancaContaBancaria
from app.schemas.cobranca_conta import CobrancaContaLista, CobrancaContaRead, CobrancaContaUpsert
from app.services.secret_box import encrypt_str


def _to_read(row: CobrancaContaBancaria) -> CobrancaContaRead:
    return CobrancaContaRead(
        id=row.id,
        apelido=row.apelido,
        banco_codigo=row.banco_codigo,
        banco_nome=row.banco_nome,
        agencia=row.agencia,
        agencia_dv=row.agencia_dv,
        conta=row.conta,
        conta_dv=row.conta_dv,
        carteira=row.carteira,
        titular_nome=row.titular_nome,
        titular_documento=row.titular_documento,
        ativo=bool(row.ativo),
        padrao=bool(row.padrao),
        tem_token=bool((row.boleto_cloud_token_cifrado or "").strip()),
        notas=row.notas,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def listar(db: Session) -> CobrancaContaLista:
    rows = (
        db.query(CobrancaContaBancaria)
        .order_by(
            CobrancaContaBancaria.padrao.desc(),
            CobrancaContaBancaria.apelido.asc(),
            CobrancaContaBancaria.id.asc(),
        )
        .all()
    )
    return CobrancaContaLista(items=[_to_read(r) for r in rows], total=len(rows))


def obter(db: Session, conta_id: int) -> CobrancaContaBancaria:
    row = db.query(CobrancaContaBancaria).filter(CobrancaContaBancaria.id == conta_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada.")
    return row


def _aplicar(row: CobrancaContaBancaria, data: CobrancaContaUpsert) -> None:
    apelido = (data.apelido or "").strip()
    if not apelido:
        raise HTTPException(status_code=400, detail="Informe o apelido da conta.")
    row.apelido = apelido
    row.banco_codigo = (data.banco_codigo or "").strip() or None
    row.banco_nome = (data.banco_nome or "").strip() or None
    row.agencia = (data.agencia or "").strip() or None
    row.agencia_dv = (data.agencia_dv or "").strip() or None
    row.conta = (data.conta or "").strip() or None
    row.conta_dv = (data.conta_dv or "").strip() or None
    row.carteira = (data.carteira or "").strip() or None
    row.titular_nome = (data.titular_nome or "").strip() or None
    row.titular_documento = (data.titular_documento or "").strip() or None
    row.ativo = data.ativo
    row.padrao = data.padrao
    row.notas = (data.notas or "").strip() or None
    token = (data.boleto_cloud_token or "").strip()
    if token:
        row.boleto_cloud_token_cifrado = encrypt_str(token)


def _garantir_unico_padrao(db: Session, row: CobrancaContaBancaria) -> None:
    if not row.padrao:
        return
    (
        db.query(CobrancaContaBancaria)
        .filter(CobrancaContaBancaria.id != row.id, CobrancaContaBancaria.padrao.is_(True))
        .update({"padrao": False}, synchronize_session=False)
    )


def criar(db: Session, data: CobrancaContaUpsert) -> CobrancaContaRead:
    row = CobrancaContaBancaria()
    _aplicar(row, data)
    db.add(row)
    db.flush()
    _garantir_unico_padrao(db, row)
    db.commit()
    db.refresh(row)
    return _to_read(row)


def atualizar(db: Session, conta_id: int, data: CobrancaContaUpsert) -> CobrancaContaRead:
    row = obter(db, conta_id)
    _aplicar(row, data)
    _garantir_unico_padrao(db, row)
    db.commit()
    db.refresh(row)
    return _to_read(row)


def desativar(db: Session, conta_id: int) -> CobrancaContaRead:
    row = obter(db, conta_id)
    row.ativo = False
    row.padrao = False
    db.commit()
    db.refresh(row)
    return _to_read(row)
