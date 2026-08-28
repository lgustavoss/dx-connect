"""Justificativas de ponto (#774)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.ponto_justificativa import PontoJustificativa
from app.schemas.ponto import PontoJustificativaRead
from app.services import ponto as ponto_svc

TIPOS = frozenset({"falta", "esquecimento", "folga_com_ponto", "outro"})


def _to_read(j: PontoJustificativa) -> PontoJustificativaRead:
    nome = j.atendente.nome if j.atendente else None
    tem = bool(getattr(j, "anexo_storage_key", None))
    return PontoJustificativaRead(
        id=j.id,
        atendente_id=j.atendente_id,
        atendente_nome=nome,
        data_ref=j.data_ref,
        tipo=j.tipo,
        motivo=j.motivo,
        estado=j.estado,
        decisao_motivo=j.decisao_motivo,
        decidido_por_id=j.decidido_por_id,
        decidido_em=j.decidido_em,
        tem_anexo=tem,
        anexo_nome=getattr(j, "anexo_nome", None) if tem else None,
        anexo_content_type=getattr(j, "anexo_content_type", None) if tem else None,
        anexo_tamanho_bytes=getattr(j, "anexo_tamanho_bytes", None) if tem else None,
        created_at=j.created_at,
    )


def criar(
    db: Session,
    atendente: Atendente,
    *,
    data_ref,
    tipo: str,
    motivo: str,
    anexo_nome: str | None = None,
    anexo_content_type: str | None = None,
    anexo_storage_key: str | None = None,
    anexo_tamanho_bytes: int | None = None,
) -> PontoJustificativaRead:
    ponto_svc.exigir_acesso_ponto(atendente)
    if tipo not in TIPOS:
        raise HTTPException(status_code=400, detail="Tipo de justificativa inválido")
    row = PontoJustificativa(
        tenant_id=atendente.tenant_id,
        atendente_id=atendente.id,
        data_ref=data_ref,
        tipo=tipo,
        motivo=motivo.strip(),
        estado="pendente",
        anexo_nome=anexo_nome,
        anexo_content_type=anexo_content_type,
        anexo_storage_key=anexo_storage_key,
        anexo_tamanho_bytes=anexo_tamanho_bytes,
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_justificativa",
        row.id,
        "create",
        atendente.id,
        payload={
            "data_ref": str(data_ref),
            "tipo": tipo,
            "motivo": motivo.strip(),
            "tem_anexo": bool(anexo_storage_key),
        },
    )
    db.commit()
    db.refresh(row)
    row = (
        db.query(PontoJustificativa)
        .options(joinedload(PontoJustificativa.atendente))
        .filter(PontoJustificativa.id == row.id)
        .first()
    )
    assert row is not None
    return _to_read(row)


def listar_me(db: Session, atendente: Atendente) -> list[PontoJustificativaRead]:
    ponto_svc.exigir_acesso_ponto(atendente)
    rows = (
        db.query(PontoJustificativa)
        .options(joinedload(PontoJustificativa.atendente))
        .filter(PontoJustificativa.atendente_id == atendente.id)
        .order_by(PontoJustificativa.created_at.desc())
        .limit(100)
        .all()
    )
    return [_to_read(r) for r in rows]


def listar_admin(
    db: Session,
    admin: Atendente,
    *,
    estado: str | None = "pendente",
) -> list[PontoJustificativaRead]:
    q = (
        db.query(PontoJustificativa)
        .options(joinedload(PontoJustificativa.atendente))
        .filter(PontoJustificativa.tenant_id == admin.tenant_id)
    )
    if estado:
        q = q.filter(PontoJustificativa.estado == estado)
    rows = q.order_by(PontoJustificativa.created_at.asc()).limit(200).all()
    return [_to_read(r) for r in rows]


def obter_para_anexo(
    db: Session,
    *,
    justificativa_id: int,
    tenant_id: int,
    solicitante: Atendente,
) -> PontoJustificativa:
    row = (
        db.query(PontoJustificativa)
        .filter(
            PontoJustificativa.id == justificativa_id,
            PontoJustificativa.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Justificativa não encontrada")
    if solicitante.role != "admin" and row.atendente_id != solicitante.id:
        raise HTTPException(status_code=403, detail="Sem permissão para este anexo")
    if not row.anexo_storage_key:
        raise HTTPException(status_code=404, detail="Esta justificativa não tem anexo")
    return row


def decidir(
    db: Session,
    admin: Atendente,
    justificativa_id: int,
    *,
    estado: str,
    decisao_motivo: str,
    aplicar_batidas: list | None = None,
) -> PontoJustificativaRead:
    if estado not in ("aprovada", "rejeitada"):
        raise HTTPException(status_code=400, detail="Estado de decisão inválido")
    row = (
        db.query(PontoJustificativa)
        .options(joinedload(PontoJustificativa.atendente))
        .filter(
            PontoJustificativa.id == justificativa_id,
            PontoJustificativa.tenant_id == admin.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Justificativa não encontrada")
    if row.estado != "pendente":
        raise HTTPException(status_code=400, detail="Justificativa já foi decidida")

    row.estado = estado
    row.decisao_motivo = decisao_motivo.strip()
    row.decidido_por_id = admin.id
    row.decidido_em = datetime.now(timezone.utc)

    if estado == "aprovada" and aplicar_batidas:
        for item in aplicar_batidas:
            ponto_svc.admin_criar_batida(
                db,
                admin,
                atendente_id=row.atendente_id,
                tipo=item.tipo,
                registrado_em=item.registrado_em,
                motivo=f"Justificativa #{row.id}: {item.motivo}",
                commit=False,
            )

    registrar_audit(
        db,
        "ponto_justificativa",
        row.id,
        f"decidir_{estado}",
        admin.id,
        payload={
            "decisao_motivo": decisao_motivo.strip(),
            "aplicar_batidas": len(aplicar_batidas or []),
        },
    )
    db.commit()
    db.refresh(row)
    return _to_read(row)
