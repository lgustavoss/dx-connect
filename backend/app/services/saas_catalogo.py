"""Catálogo comercial de planos e módulos SaaS (control-plane)."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.models.saas_plano import SaasModulo, SaasPlano, SaasPlanoModulo
from app.schemas.saas import (
    SaasModuloCreate,
    SaasModuloUpdate,
    SaasPlanoCreate,
    SaasPlanoUpdate,
)
from app.services.saas_clientes import SaasErro


def obter_modulo(db: Session, modulo_id: int) -> SaasModulo:
    row = db.query(SaasModulo).filter(SaasModulo.id == modulo_id).first()
    if not row:
        raise SaasErro("Módulo não encontrado", 404)
    return row


def listar_modulos(db: Session, *, ativo: bool | None = None) -> list[SaasModulo]:
    q = db.query(SaasModulo)
    if ativo is not None:
        q = q.filter(SaasModulo.ativo.is_(ativo))
    return q.order_by(SaasModulo.nome.asc(), SaasModulo.id.asc()).all()


def criar_modulo(db: Session, data: SaasModuloCreate) -> SaasModulo:
    if db.query(SaasModulo).filter(SaasModulo.codigo == data.codigo).first():
        raise SaasErro("Já existe um módulo com este código", 409)
    row = SaasModulo(codigo=data.codigo, nome=data.nome, descricao=data.descricao, ativo=True)
    db.add(row)
    db.flush()
    return row


def atualizar_modulo(db: Session, modulo_id: int, data: SaasModuloUpdate) -> SaasModulo:
    row = obter_modulo(db, modulo_id)
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(row, k, v)
    db.flush()
    return row


def ativar_modulo(db: Session, modulo_id: int) -> SaasModulo:
    row = obter_modulo(db, modulo_id)
    if row.ativo:
        raise SaasErro("Módulo já está activo")
    row.ativo = True
    db.flush()
    return row


def desativar_modulo(db: Session, modulo_id: int) -> SaasModulo:
    row = obter_modulo(db, modulo_id)
    if not row.ativo:
        raise SaasErro("Módulo já está inactivo")
    row.ativo = False
    db.flush()
    return row


def obter_plano(db: Session, plano_id: int) -> SaasPlano:
    row = (
        db.query(SaasPlano)
        .options(joinedload(SaasPlano.modulos_links).joinedload(SaasPlanoModulo.modulo))
        .filter(SaasPlano.id == plano_id)
        .first()
    )
    if not row:
        raise SaasErro("Plano não encontrado", 404)
    return row


def listar_planos(db: Session, *, ativo: bool | None = None) -> list[SaasPlano]:
    q = db.query(SaasPlano).options(
        joinedload(SaasPlano.modulos_links).joinedload(SaasPlanoModulo.modulo)
    )
    if ativo is not None:
        q = q.filter(SaasPlano.ativo.is_(ativo))
    return q.order_by(SaasPlano.ordem.asc(), SaasPlano.nome.asc(), SaasPlano.id.asc()).all()


def _resolver_modulos(db: Session, modulo_ids: list[int]) -> list[SaasModulo]:
    if not modulo_ids:
        return []
    uniq = list(dict.fromkeys(modulo_ids))
    rows = db.query(SaasModulo).filter(SaasModulo.id.in_(uniq)).all()
    if len(rows) != len(uniq):
        raise SaasErro("Um ou mais módulos não existem")
    by_id = {r.id: r for r in rows}
    return [by_id[i] for i in uniq]


def _set_modulos(db: Session, plano: SaasPlano, modulo_ids: list[int]) -> None:
    mods = _resolver_modulos(db, modulo_ids)
    plano.modulos_links.clear()
    db.flush()
    for m in mods:
        plano.modulos_links.append(SaasPlanoModulo(plano_id=plano.id, modulo_id=m.id))
    db.flush()


def criar_plano(db: Session, data: SaasPlanoCreate) -> SaasPlano:
    if db.query(SaasPlano).filter(SaasPlano.codigo == data.codigo).first():
        raise SaasErro("Já existe um plano com este código", 409)
    row = SaasPlano(
        codigo=data.codigo,
        nome=data.nome,
        descricao=data.descricao,
        ordem=data.ordem or 0,
        preco_mensal=data.preco_mensal,
        max_postos=data.max_postos,
        max_usuarios=data.max_usuarios,
        ativo=True,
    )
    db.add(row)
    db.flush()
    _set_modulos(db, row, data.modulo_ids)
    return obter_plano(db, row.id)


def atualizar_plano(db: Session, plano_id: int, data: SaasPlanoUpdate) -> SaasPlano:
    row = obter_plano(db, plano_id)
    payload = data.model_dump(exclude_unset=True)
    modulo_ids = payload.pop("modulo_ids", None)
    for k, v in payload.items():
        setattr(row, k, v)
    if modulo_ids is not None:
        _set_modulos(db, row, modulo_ids)
    db.flush()
    return obter_plano(db, row.id)


def ativar_plano(db: Session, plano_id: int) -> SaasPlano:
    row = obter_plano(db, plano_id)
    if row.ativo:
        raise SaasErro("Plano já está activo")
    row.ativo = True
    db.flush()
    return row


def desativar_plano(db: Session, plano_id: int) -> SaasPlano:
    row = obter_plano(db, plano_id)
    if not row.ativo:
        raise SaasErro("Plano já está inactivo")
    row.ativo = False
    db.flush()
    return row


def serializar_plano(row: SaasPlano) -> dict:
    mods = []
    for link in row.modulos_links or []:
        m = link.modulo
        if m is None:
            continue
        mods.append({"id": m.id, "codigo": m.codigo, "nome": m.nome, "ativo": bool(m.ativo)})
    preco = row.preco_mensal
    return {
        "id": row.id,
        "codigo": row.codigo,
        "nome": row.nome,
        "descricao": row.descricao,
        "ativo": bool(row.ativo),
        "ordem": int(row.ordem or 0),
        "preco_mensal": float(preco) if preco is not None else None,
        "max_postos": row.max_postos,
        "max_usuarios": row.max_usuarios,
        "modulos": mods,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def obter_plano_por_codigo(db: Session, codigo: str) -> SaasPlano | None:
    return db.query(SaasPlano).filter(SaasPlano.codigo == codigo.strip().lower()).first()


def aplicar_plano_em_cliente(
    db: Session,
    *,
    plano_id: int | None,
    plano_actual_id: int | None = None,
    permitir_inactivo_se_actual: bool = True,
) -> tuple[int | None, str | None, list[str], int | None, int | None]:
    """Valida e devolve (plano_id, nome, códigos módulos, max_postos, max_usuarios)."""
    if plano_id is None:
        return None, None, [], None, None
    plano = (
        db.query(SaasPlano)
        .options(joinedload(SaasPlano.modulos_links).joinedload(SaasPlanoModulo.modulo))
        .filter(SaasPlano.id == plano_id)
        .first()
    )
    if not plano:
        raise SaasErro("Plano não encontrado", 404)
    if not plano.ativo:
        if not (permitir_inactivo_se_actual and plano_actual_id == plano.id):
            raise SaasErro("Plano inactivo — escolha um plano activo")
    codigos: list[str] = []
    for link in plano.modulos_links or []:
        if link.modulo and link.modulo.codigo:
            codigos.append(link.modulo.codigo)
    return plano.id, plano.nome, codigos, plano.max_postos, plano.max_usuarios


def sincronizar_snapshot_licenca(db: Session, row) -> None:
    """Actualiza modulos_snapshot e limites a partir do plano_id actual."""
    from app.models.cliente_saas import ClienteSaaS

    if not isinstance(row, ClienteSaaS):
        return
    if not row.plano_id:
        row.modulos_snapshot = []
        row.max_postos = None
        row.max_usuarios = None
        return
    _pid, _nome, codigos, max_p, max_u = aplicar_plano_em_cliente(
        db,
        plano_id=row.plano_id,
        plano_actual_id=row.plano_id,
        permitir_inactivo_se_actual=True,
    )
    row.modulos_snapshot = codigos
    row.max_postos = max_p
    row.max_usuarios = max_u
    db.flush()


_ACTION_LABELS = {
    "create": "Licença criada",
    "create_from_lead": "Criada a partir de lead",
    "update": "Dados actualizados",
    "suspender": "Suspensa",
    "reativar": "Reactivada",
    "renovar": "Renovada",
    "registrar_instancia": "URL sincronizada",
    "solicitar_provisionamento": "Provisionamento solicitado",
    "confirmar_provisionamento": "Provisionamento confirmado",
    "aprovar": "Aprovada (go-live)",
    "rejeitar": "Rejeitada",
    "confirmar_stack": "Stack confirmada",
    "reenviar_entrega": "E-mail de entrega reenviado",
}


def listar_timeline(db: Session, cliente_id: int, *, limit: int = 50) -> list[dict]:
    from app.models.audit_log import AuditLog

    rows = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "cliente_saas", AuditLog.entity_id == cliente_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "action": r.action,
                "label": _ACTION_LABELS.get(r.action, r.action),
                "atendente_id": r.atendente_id,
                "payload": r.payload_json,
                "created_at": r.created_at,
            }
        )
    return out
