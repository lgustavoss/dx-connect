"""Troca / cobertura de plantão (#970)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.ponto_cobertura import PontoCobertura
from app.schemas.ponto import PontoCoberturaRead
from app.services import escala as escala_svc
from app.services import ponto as ponto_svc

ESTADOS = frozenset(
    {"pendente_cobertor", "pendente_admin", "aprovada", "rejeitada", "cancelada"}
)


def _to_read(row: PontoCobertura) -> PontoCoberturaRead:
    return PontoCoberturaRead(
        id=row.id,
        solicitante_id=row.solicitante_id,
        solicitante_nome=row.solicitante.nome if row.solicitante else None,
        cobertor_id=row.cobertor_id,
        cobertor_nome=row.cobertor.nome if row.cobertor else None,
        data_ref=row.data_ref,
        motivo=row.motivo,
        estado=row.estado,
        origem=row.origem or "solicitacao",
        resposta_cobertor=row.resposta_cobertor,
        respondido_em=row.respondido_em,
        decidido_por_id=row.decidido_por_id,
        decidido_em=row.decidido_em,
        decisao_motivo=row.decisao_motivo,
        created_at=row.created_at,
    )


def _carregar(db: Session, cobertura_id: int) -> PontoCobertura:
    row = (
        db.query(PontoCobertura)
        .options(
            joinedload(PontoCobertura.solicitante),
            joinedload(PontoCobertura.cobertor),
        )
        .filter(PontoCobertura.id == cobertura_id)
        .first()
    )
    assert row is not None
    return row


def papel_cobertura_aprovada(db: Session, atendente_id: int, dia: date) -> str | None:
    """Retorna 'solicitante' | 'cobertor' se houver cobertura aprovada no dia."""
    row = (
        db.query(PontoCobertura)
        .filter(
            PontoCobertura.estado == "aprovada",
            PontoCobertura.data_ref == dia,
            or_(
                PontoCobertura.solicitante_id == atendente_id,
                PontoCobertura.cobertor_id == atendente_id,
            ),
        )
        .order_by(PontoCobertura.id.desc())
        .first()
    )
    if not row:
        return None
    if row.solicitante_id == atendente_id:
        return "solicitante"
    return "cobertor"


def eh_dia_esperado_efetivo(db: Session, atendente: Atendente, dia: date) -> bool:
    """Dia esperado após coberturas aprovadas (#970)."""
    papel = papel_cobertura_aprovada(db, atendente.id, dia)
    if papel == "solicitante":
        return False
    if papel == "cobertor":
        return True
    if not escala_svc.escala_configurada(atendente):
        return False
    return escala_svc.eh_dia_de_trabalho(atendente, dia)


def mapa_papeis_periodo(
    db: Session, atendente_id: int, *, desde: date, ate: date
) -> dict[date, str]:
    rows = (
        db.query(PontoCobertura)
        .filter(
            PontoCobertura.estado == "aprovada",
            PontoCobertura.data_ref >= desde,
            PontoCobertura.data_ref <= ate,
            or_(
                PontoCobertura.solicitante_id == atendente_id,
                PontoCobertura.cobertor_id == atendente_id,
            ),
        )
        .all()
    )
    out: dict[date, str] = {}
    for r in rows:
        out[r.data_ref] = "solicitante" if r.solicitante_id == atendente_id else "cobertor"
    return out


def _atendente_tenant(db: Session, tenant_id: int, atendente_id: int) -> Atendente:
    a = (
        db.query(Atendente)
        .filter(
            Atendente.id == atendente_id,
            Atendente.tenant_id == tenant_id,
            Atendente.role != "saas_ops",
            Atendente.ativo.is_(True),
        )
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Atendente não encontrado")
    return a


def solicitar(
    db: Session,
    solicitante: Atendente,
    *,
    cobertor_id: int,
    data_ref: date,
    motivo: str | None = None,
) -> PontoCoberturaRead:
    ponto_svc.exigir_acesso_ponto(solicitante)
    if cobertor_id == solicitante.id:
        raise HTTPException(status_code=400, detail="Escolha outro colaborador para cobrir.")
    cobertor = _atendente_tenant(db, solicitante.tenant_id, cobertor_id)
    if data_ref < date.today():
        raise HTTPException(status_code=400, detail="A data da cobertura deve ser hoje ou futura.")
    existente = (
        db.query(PontoCobertura)
        .filter(
            PontoCobertura.tenant_id == solicitante.tenant_id,
            PontoCobertura.data_ref == data_ref,
            PontoCobertura.estado.in_(("pendente_cobertor", "pendente_admin", "aprovada")),
            or_(
                PontoCobertura.solicitante_id.in_((solicitante.id, cobertor.id)),
                PontoCobertura.cobertor_id.in_((solicitante.id, cobertor.id)),
            ),
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe cobertura pendente ou aprovada envolvendo estes colaboradores nesta data.",
        )
    row = PontoCobertura(
        tenant_id=solicitante.tenant_id,
        solicitante_id=solicitante.id,
        cobertor_id=cobertor.id,
        data_ref=data_ref,
        motivo=(motivo or "").strip()[:1000] or None,
        estado="pendente_cobertor",
        origem="solicitacao",
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_cobertura",
        row.id,
        "create",
        solicitante.id,
        payload={
            "cobertor_id": cobertor.id,
            "data_ref": str(data_ref),
            "estado": "pendente_cobertor",
        },
    )
    db.commit()
    return _to_read(_carregar(db, row.id))


def responder_cobertor(
    db: Session,
    cobertor: Atendente,
    cobertura_id: int,
    *,
    aceitar: bool,
) -> PontoCoberturaRead:
    ponto_svc.exigir_acesso_ponto(cobertor)
    row = (
        db.query(PontoCobertura)
        .filter(
            PontoCobertura.id == cobertura_id,
            PontoCobertura.tenant_id == cobertor.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cobertura não encontrada")
    if row.cobertor_id != cobertor.id:
        raise HTTPException(status_code=403, detail="Só o cobertor pode responder este pedido.")
    if row.estado != "pendente_cobertor":
        raise HTTPException(status_code=400, detail="Este pedido já foi respondido.")
    row.respondido_em = datetime.now(timezone.utc)
    if aceitar:
        row.resposta_cobertor = "aceita"
        row.estado = "pendente_admin"
    else:
        row.resposta_cobertor = "recusa"
        row.estado = "rejeitada"
        row.decisao_motivo = "Recusado pelo cobertor"
        row.decidido_em = row.respondido_em
    registrar_audit(
        db,
        "ponto_cobertura",
        row.id,
        "responder_cobertor",
        cobertor.id,
        payload={"aceitar": aceitar, "estado": row.estado},
    )
    db.commit()
    return _to_read(_carregar(db, row.id))


def decidir_admin(
    db: Session,
    admin: Atendente,
    cobertura_id: int,
    *,
    aprovar: bool,
    decisao_motivo: str | None = None,
) -> PontoCoberturaRead:
    row = (
        db.query(PontoCobertura)
        .filter(
            PontoCobertura.id == cobertura_id,
            PontoCobertura.tenant_id == admin.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cobertura não encontrada")
    if row.estado not in ("pendente_admin", "pendente_cobertor"):
        raise HTTPException(status_code=400, detail="Este pedido já foi decidido.")
    row.decidido_por_id = admin.id
    row.decidido_em = datetime.now(timezone.utc)
    row.decisao_motivo = (decisao_motivo or "").strip()[:1000] or None
    if aprovar:
        row.estado = "aprovada"
        if not row.decisao_motivo:
            row.decisao_motivo = "Homologado pelo administrador"
        if row.resposta_cobertor is None:
            row.resposta_cobertor = "aceita"
            row.respondido_em = row.decidido_em
    else:
        row.estado = "rejeitada"
        if not row.decisao_motivo:
            row.decisao_motivo = "Negado pelo administrador"
    registrar_audit(
        db,
        "ponto_cobertura",
        row.id,
        "decidir",
        admin.id,
        payload={"estado": row.estado},
    )
    db.commit()
    return _to_read(_carregar(db, row.id))


def conceder_admin(
    db: Session,
    admin: Atendente,
    *,
    solicitante_id: int,
    cobertor_id: int,
    data_ref: date,
    motivo: str | None = None,
) -> PontoCoberturaRead:
    if solicitante_id == cobertor_id:
        raise HTTPException(status_code=400, detail="Solicitante e cobertor devem ser diferentes.")
    sol = _atendente_tenant(db, admin.tenant_id, solicitante_id)
    cob = _atendente_tenant(db, admin.tenant_id, cobertor_id)
    agora = datetime.now(timezone.utc)
    row = PontoCobertura(
        tenant_id=admin.tenant_id,
        solicitante_id=sol.id,
        cobertor_id=cob.id,
        data_ref=data_ref,
        motivo=(motivo or "").strip()[:1000] or "Cobertura agendada pelo administrador.",
        estado="aprovada",
        origem="admin",
        resposta_cobertor="aceita",
        respondido_em=agora,
        decidido_por_id=admin.id,
        decidido_em=agora,
        decisao_motivo="Agendamento direto",
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_cobertura",
        row.id,
        "conceder",
        admin.id,
        payload={
            "solicitante_id": sol.id,
            "cobertor_id": cob.id,
            "data_ref": str(data_ref),
        },
    )
    db.commit()
    return _to_read(_carregar(db, row.id))


def listar_colegas(db: Session, atendente: Atendente) -> list[dict]:
    """Colaboradores ativos do tenant (exceto eu) para pedir cobertura."""
    ponto_svc.exigir_acesso_ponto(atendente)
    rows = (
        db.query(Atendente)
        .filter(
            Atendente.tenant_id == atendente.tenant_id,
            Atendente.id != atendente.id,
            Atendente.ativo.is_(True),
            Atendente.role != "saas_ops",
        )
        .order_by(Atendente.nome.asc())
        .limit(200)
        .all()
    )
    return [{"id": a.id, "nome": a.nome} for a in rows]


def listar_me(db: Session, atendente: Atendente) -> list[PontoCoberturaRead]:
    ponto_svc.exigir_acesso_ponto(atendente)
    rows = (
        db.query(PontoCobertura)
        .options(
            joinedload(PontoCobertura.solicitante),
            joinedload(PontoCobertura.cobertor),
        )
        .filter(
            or_(
                PontoCobertura.solicitante_id == atendente.id,
                PontoCobertura.cobertor_id == atendente.id,
            )
        )
        .order_by(PontoCobertura.data_ref.desc(), PontoCobertura.id.desc())
        .limit(100)
        .all()
    )
    return [_to_read(r) for r in rows]


def listar_admin(
    db: Session,
    admin: Atendente,
    *,
    estado: str | None = "pendente_admin",
) -> list[PontoCoberturaRead]:
    q = (
        db.query(PontoCobertura)
        .options(
            joinedload(PontoCobertura.solicitante),
            joinedload(PontoCobertura.cobertor),
        )
        .filter(PontoCobertura.tenant_id == admin.tenant_id)
    )
    if estado:
        if estado == "pendente":
            q = q.filter(PontoCobertura.estado.in_(("pendente_cobertor", "pendente_admin")))
        else:
            if estado not in ESTADOS:
                raise HTTPException(status_code=400, detail="Estado inválido.")
            q = q.filter(PontoCobertura.estado == estado)
    rows = q.order_by(PontoCobertura.created_at.asc()).limit(200).all()
    return [_to_read(r) for r in rows]
