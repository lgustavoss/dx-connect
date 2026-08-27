"""Catálogo comercial de planos e módulos SaaS (control-plane)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.saas_plano import SaasModulo, SaasPlano, SaasPlanoModulo
from app.schemas.saas import (
    SaasModuloCreate,
    SaasModuloUpdate,
    SaasPlanoCreate,
    SaasPlanoUpdate,
)
from app.services.saas_clientes import SaasErro


def _num(v) -> float:
    if v is None:
        return 0.0
    return float(v)


def soma_preco_modulos(mods: list[SaasModulo]) -> float:
    return round(sum(_num(m.preco_mensal) for m in mods), 2)


def preco_extra_usuarios(
    *,
    usuarios_inclusos: int,
    preco_usuario_extra: float | Decimal | None,
    usuarios_contratados: int | None,
) -> float:
    if usuarios_contratados is None:
        return 0.0
    inclusos = max(0, int(usuarios_inclusos or 0))
    extra = max(0, int(usuarios_contratados) - inclusos)
    return round(extra * _num(preco_usuario_extra), 2)


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
    row = SaasModulo(
        codigo=data.codigo,
        nome=data.nome,
        descricao=data.descricao,
        preco_mensal=data.preco_mensal,
        ativo=True,
    )
    db.add(row)
    db.flush()
    return row


def atualizar_modulo(db: Session, modulo_id: int, data: SaasModuloUpdate) -> SaasModulo:
    row = obter_modulo(db, modulo_id)
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(row, k, v)
    db.flush()
    if "preco_mensal" in payload:
        _recalcular_planos_com_modulo(db, row.id)
    return row


def ativar_modulo(db: Session, modulo_id: int) -> SaasModulo:
    row = obter_modulo(db, modulo_id)
    if row.ativo:
        raise SaasErro("Módulo já está ativo")
    row.ativo = True
    db.flush()
    return row


def desativar_modulo(db: Session, modulo_id: int) -> SaasModulo:
    row = obter_modulo(db, modulo_id)
    if not row.ativo:
        raise SaasErro("Módulo já está inativo")
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


def resolver_modulos_por_codigos(db: Session, codigos: list[str]) -> list[SaasModulo]:
    if not codigos:
        return []
    uniq = list(dict.fromkeys([c.strip().lower() for c in codigos if c and c.strip()]))
    rows = db.query(SaasModulo).filter(SaasModulo.codigo.in_(uniq)).all()
    by_cod = {r.codigo: r for r in rows}
    missing = [c for c in uniq if c not in by_cod]
    if missing:
        raise SaasErro(f"Módulos inválidos: {', '.join(missing)}")
    return [by_cod[c] for c in uniq]


def _modulos_do_plano(plano: SaasPlano) -> list[SaasModulo]:
    out: list[SaasModulo] = []
    for link in plano.modulos_links or []:
        if link.modulo is not None:
            out.append(link.modulo)
    return out


def _aplicar_preco_plano(plano: SaasPlano) -> None:
    plano.preco_mensal = soma_preco_modulos(_modulos_do_plano(plano))


def _recalcular_planos_com_modulo(db: Session, modulo_id: int) -> None:
    planos = (
        db.query(SaasPlano)
        .options(joinedload(SaasPlano.modulos_links).joinedload(SaasPlanoModulo.modulo))
        .join(SaasPlanoModulo, SaasPlanoModulo.plano_id == SaasPlano.id)
        .filter(SaasPlanoModulo.modulo_id == modulo_id)
        .all()
    )
    for plano in planos:
        _aplicar_preco_plano(plano)
    db.flush()


def _set_modulos(db: Session, plano: SaasPlano, modulo_ids: list[int]) -> None:
    mods = _resolver_modulos(db, modulo_ids)
    plano.modulos_links.clear()
    db.flush()
    for m in mods:
        plano.modulos_links.append(SaasPlanoModulo(plano_id=plano.id, modulo_id=m.id))
    db.flush()
    plano.preco_mensal = soma_preco_modulos(mods)
    db.flush()


def criar_plano(db: Session, data: SaasPlanoCreate) -> SaasPlano:
    if db.query(SaasPlano).filter(SaasPlano.codigo == data.codigo).first():
        raise SaasErro("Já existe um plano com este código", 409)
    row = SaasPlano(
        codigo=data.codigo,
        nome=data.nome,
        descricao=data.descricao,
        ordem=data.ordem or 0,
        usuarios_inclusos=data.usuarios_inclusos if data.usuarios_inclusos is not None else 3,
        preco_usuario_extra=data.preco_usuario_extra if data.preco_usuario_extra is not None else 10,
        max_postos=None,
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
    # Preço do plano é sempre a soma dos módulos — não aceitar override manual.
    payload.pop("preco_mensal", None)
    payload.pop("max_postos", None)
    modulo_ids = payload.pop("modulo_ids", None)
    for k, v in payload.items():
        setattr(row, k, v)
    if modulo_ids is not None:
        _set_modulos(db, row, modulo_ids)
    else:
        _aplicar_preco_plano(row)
    db.flush()
    return obter_plano(db, row.id)


def ativar_plano(db: Session, plano_id: int) -> SaasPlano:
    row = obter_plano(db, plano_id)
    if row.ativo:
        raise SaasErro("Plano já está ativo")
    row.ativo = True
    db.flush()
    return row


def desativar_plano(db: Session, plano_id: int) -> SaasPlano:
    row = obter_plano(db, plano_id)
    if not row.ativo:
        raise SaasErro("Plano já está inativo")
    row.ativo = False
    db.flush()
    return row


def serializar_modulo(row: SaasModulo) -> dict:
    preco = row.preco_mensal
    return {
        "id": row.id,
        "codigo": row.codigo,
        "nome": row.nome,
        "descricao": row.descricao,
        "preco_mensal": float(preco) if preco is not None else None,
        "ativo": bool(row.ativo),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def serializar_plano(row: SaasPlano) -> dict:
    mods = []
    for link in row.modulos_links or []:
        m = link.modulo
        if m is None:
            continue
        mods.append(
            {
                "id": m.id,
                "codigo": m.codigo,
                "nome": m.nome,
                "ativo": bool(m.ativo),
                "preco_mensal": float(m.preco_mensal) if m.preco_mensal is not None else None,
            }
        )
    preco = row.preco_mensal
    if preco is None:
        preco = soma_preco_modulos(_modulos_do_plano(row))
    return {
        "id": row.id,
        "codigo": row.codigo,
        "nome": row.nome,
        "descricao": row.descricao,
        "ativo": bool(row.ativo),
        "ordem": int(row.ordem or 0),
        "preco_mensal": float(preco) if preco is not None else None,
        "usuarios_inclusos": int(row.usuarios_inclusos or 3),
        "preco_usuario_extra": (
            float(row.preco_usuario_extra) if row.preco_usuario_extra is not None else 10.0
        ),
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
    modulo_ids: list[int] | None = None,
) -> tuple[int | None, str | None, list[str], int | None, int | None]:
    """Valida e devolve (plano_id, nome, códigos módulos, max_postos, max_usuarios do plano)."""
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
            raise SaasErro("Plano inativo — escolha um plano ativo")
    if modulo_ids is not None:
        mods = _resolver_modulos(db, modulo_ids)
        codigos = [m.codigo for m in mods if m.codigo]
    else:
        codigos = []
        for link in plano.modulos_links or []:
            if link.modulo and link.modulo.codigo:
                codigos.append(link.modulo.codigo)
    return plano.id, plano.nome, codigos, plano.max_postos, plano.max_usuarios


def sincronizar_snapshot_licenca(db: Session, row) -> None:
    """Atualiza modulos_snapshot e limites a partir do plano_id actual (sem sobrescrever mix custom)."""
    from app.models.cliente_saas import ClienteSaaS

    if not isinstance(row, ClienteSaaS):
        return
    if not row.plano_id:
        row.modulos_snapshot = []
        row.max_postos = None
        return
    # Se já há snapshot custom, só garante limites de postos nulos; usuários contratados ficam.
    if list(getattr(row, "modulos_snapshot", None) or []):
        row.max_postos = None
        db.flush()
        return
    _pid, _nome, codigos, max_p, max_u = aplicar_plano_em_cliente(
        db,
        plano_id=row.plano_id,
        plano_actual_id=row.plano_id,
        permitir_inactivo_se_actual=True,
    )
    row.modulos_snapshot = codigos
    row.max_postos = max_p
    if getattr(row, "max_usuarios", None) is None and max_u is not None:
        row.max_usuarios = max_u
    db.flush()


def estimar_preco_mensal(
    db: Session,
    *,
    plano_id: int | None,
    modulo_ids: list[int] | None,
    usuarios_contratados: int | None,
) -> dict:
    """Calcula preço comercial (módulos + extras de usuário)."""
    mods: list[SaasModulo] = []
    inclusos = 3
    extra_unit = 10.0
    if plano_id is not None:
        plano = obter_plano(db, plano_id)
        inclusos = int(plano.usuarios_inclusos or 3)
        extra_unit = _num(plano.preco_usuario_extra) if plano.preco_usuario_extra is not None else 10.0
        if modulo_ids is None:
            mods = _modulos_do_plano(plano)
    if modulo_ids is not None:
        mods = _resolver_modulos(db, modulo_ids)
    preco_mods = soma_preco_modulos(mods)
    preco_users = preco_extra_usuarios(
        usuarios_inclusos=inclusos,
        preco_usuario_extra=extra_unit,
        usuarios_contratados=usuarios_contratados,
    )
    return {
        "preco_modulos": preco_mods,
        "preco_usuarios_extra": preco_users,
        "preco_mensal_total": round(preco_mods + preco_users, 2),
        "usuarios_inclusos": inclusos,
        "preco_usuario_extra": extra_unit,
        "usuarios_contratados": usuarios_contratados,
        "modulos": [
            {
                "id": m.id,
                "codigo": m.codigo,
                "nome": m.nome,
                "preco_mensal": float(m.preco_mensal) if m.preco_mensal is not None else None,
            }
            for m in mods
        ],
    }


_ACTION_LABELS = {
    "create": "Licença criada",
    "create_from_lead": "Criada a partir de lead",
    "update": "Dados atualizados",
    "suspender": "Suspensa",
    "reativar": "Reativada",
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
