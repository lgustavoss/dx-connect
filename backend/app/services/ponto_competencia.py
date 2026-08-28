"""Setup checklist (#981), competência (#978) e ciência do espelho (#979)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.core.auth import ROLES_ATENDENTE
from app.models.atendente import Atendente
from app.models.ponto_competencia import PontoCompetencia, PontoEspelhoCiencia
from app.models.ponto_settings import PontoLocal
from app.schemas.ponto import (
    PontoCienciaItem,
    PontoCienciaMe,
    PontoCompetenciaRead,
    PontoSetupItem,
    PontoSetupStatus,
)
from app.services import ponto as ponto_svc
from app.services import ponto_settings as ponto_settings_svc
from app.services.escala import escala_configurada


def _validar_ano_mes(ano: int, mes: int) -> None:
    if ano < 2000 or ano > 2100 or mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Competência inválida (ano/mês).")


def competencia_fechada(db: Session, tenant_id: int, *, ano: int, mes: int) -> bool:
    row = (
        db.query(PontoCompetencia)
        .filter(
            PontoCompetencia.tenant_id == tenant_id,
            PontoCompetencia.ano == ano,
            PontoCompetencia.mes == mes,
            PontoCompetencia.fechada.is_(True),
        )
        .first()
    )
    return row is not None


def competencia_fechada_para_data(db: Session, tenant_id: int, dia: date) -> bool:
    return competencia_fechada(db, tenant_id, ano=dia.year, mes=dia.month)


def setup_status(db: Session, admin: Atendente) -> PontoSetupStatus:
    st = ponto_settings_svc.get_or_create_settings(db, admin.tenant_id)
    ativos = (
        db.query(Atendente)
        .filter(
            Atendente.tenant_id == admin.tenant_id,
            Atendente.ativo.is_(True),
            Atendente.role.in_(tuple(ROLES_ATENDENTE)),
        )
        .all()
    )
    sem_jornada = sum(1 for a in ativos if not escala_configurada(a))
    locais_ativos = (
        db.query(PontoLocal)
        .filter(
            PontoLocal.tenant_id == admin.tenant_id,
            PontoLocal.ativo.is_(True),
            PontoLocal.atendente_id.isnot(None),
        )
        .count()
    )
    itens: list[PontoSetupItem] = []
    if sem_jornada > 0:
        itens.append(
            PontoSetupItem(
                codigo="jornada_colaboradores",
                titulo="Configure a jornada dos colaboradores",
                detalhe=f"{sem_jornada} colaborador(es) ainda sem jornada (modo nenhum).",
                destino="cadastro_atendentes",
                ok=False,
            )
        )
    else:
        itens.append(
            PontoSetupItem(
                codigo="jornada_colaboradores",
                titulo="Jornada dos colaboradores",
                detalhe="Todos os ativos têm jornada configurada.",
                destino="cadastro_atendentes",
                ok=True,
            )
        )

    itens.append(
        PontoSetupItem(
            codigo="fecho_automatico",
            titulo="Revise o fecho automático",
            detalhe=(
                "Fecho automático ativo."
                if st.fecho_automatico_ativo
                else "Fecho por esquecimento está desligado (padrão até o admin ativar)."
            ),
            destino="ponto_settings",
            ok=True,  # informativo; não bloqueia
            informativo=True,
        )
    )
    itens.append(
        PontoSetupItem(
            codigo="feriados",
            titulo="Feriados",
            detalhe=(
                "Feriados nacionais ligados."
                if st.usar_feriados_nacionais
                else "Feriados nacionais desligados — confira feriados custom."
            ),
            destino="ponto_feriados",
            ok=True,
            informativo=True,
        )
    )
    if st.politica_geolocalizacao != "opcional" and locais_ativos == 0:
        itens.append(
            PontoSetupItem(
                codigo="locais_geo",
                titulo="Locais de geolocalização",
                detalhe="Política de geo exige locais, mas nenhum local ativo está vinculado a colaboradores.",
                destino="cadastro_atendentes",
                ok=False,
            )
        )
    else:
        itens.append(
            PontoSetupItem(
                codigo="locais_geo",
                titulo="Locais de geolocalização",
                detalhe=(
                    f"Política: {st.politica_geolocalizacao}; {locais_ativos} local(is) ativo(s)."
                ),
                destino="cadastro_atendentes",
                ok=True,
                informativo=st.politica_geolocalizacao == "opcional",
            )
        )

    pendentes = sum(1 for i in itens if not i.ok)
    return PontoSetupStatus(
        defaults_fecho_off=not st.fecho_automatico_ativo,
        tolerancia_sugerida_minutos=15,
        pendentes=pendentes,
        itens=itens,
    )


def _to_comp_read(row: PontoCompetencia) -> PontoCompetenciaRead:
    return PontoCompetenciaRead(
        id=row.id,
        ano=row.ano,
        mes=row.mes,
        fechada=row.fechada,
        fechado_em=row.fechado_em,
        fechado_por_id=row.fechado_por_id,
        fechado_por_nome=row.fechado_por.nome if row.fechado_por else None,
        reaberto_em=row.reaberto_em,
        reaberto_por_id=row.reaberto_por_id,
        reabrir_motivo=row.reabrir_motivo,
    )


def _get_or_create_comp(db: Session, tenant_id: int, ano: int, mes: int) -> PontoCompetencia:
    row = (
        db.query(PontoCompetencia)
        .filter(
            PontoCompetencia.tenant_id == tenant_id,
            PontoCompetencia.ano == ano,
            PontoCompetencia.mes == mes,
        )
        .first()
    )
    if row:
        return row
    row = PontoCompetencia(tenant_id=tenant_id, ano=ano, mes=mes, fechada=False)
    db.add(row)
    db.flush()
    return row


def obter_competencia(db: Session, admin: Atendente, *, ano: int, mes: int) -> PontoCompetenciaRead:
    _validar_ano_mes(ano, mes)
    row = (
        db.query(PontoCompetencia)
        .options(joinedload(PontoCompetencia.fechado_por))
        .filter(
            PontoCompetencia.tenant_id == admin.tenant_id,
            PontoCompetencia.ano == ano,
            PontoCompetencia.mes == mes,
        )
        .first()
    )
    if not row:
        return PontoCompetenciaRead(id=0, ano=ano, mes=mes, fechada=False)
    return _to_comp_read(row)


def fechar_competencia(db: Session, admin: Atendente, *, ano: int, mes: int) -> PontoCompetenciaRead:
    _validar_ano_mes(ano, mes)
    row = _get_or_create_comp(db, admin.tenant_id, ano, mes)
    if row.fechada:
        raise HTTPException(status_code=400, detail="Esta competência já está fechada.")
    agora = datetime.now(timezone.utc)
    row.fechada = True
    row.fechado_em = agora
    row.fechado_por_id = admin.id
    row.reaberto_em = None
    row.reaberto_por_id = None
    row.reabrir_motivo = None
    registrar_audit(
        db,
        "ponto_competencia",
        row.id,
        "fechar",
        admin.id,
        payload={"ano": ano, "mes": mes},
    )
    db.commit()
    return obter_competencia(db, admin, ano=ano, mes=mes)


def reabrir_competencia(
    db: Session,
    admin: Atendente,
    *,
    ano: int,
    mes: int,
    motivo: str,
) -> PontoCompetenciaRead:
    _validar_ano_mes(ano, mes)
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 3:
        raise HTTPException(status_code=400, detail="Informe o motivo da reabertura (mín. 3 caracteres).")
    row = (
        db.query(PontoCompetencia)
        .filter(
            PontoCompetencia.tenant_id == admin.tenant_id,
            PontoCompetencia.ano == ano,
            PontoCompetencia.mes == mes,
        )
        .first()
    )
    if not row or not row.fechada:
        raise HTTPException(status_code=400, detail="Competência não está fechada.")
    row.fechada = False
    row.reaberto_em = datetime.now(timezone.utc)
    row.reaberto_por_id = admin.id
    row.reabrir_motivo = motivo_limpo[:1000]
    registrar_audit(
        db,
        "ponto_competencia",
        row.id,
        "reabrir",
        admin.id,
        payload={"ano": ano, "mes": mes, "motivo": motivo_limpo},
    )
    db.commit()
    return obter_competencia(db, admin, ano=ano, mes=mes)


def listar_competencias(db: Session, admin: Atendente, *, ano: int | None = None) -> list[PontoCompetenciaRead]:
    q = (
        db.query(PontoCompetencia)
        .options(joinedload(PontoCompetencia.fechado_por))
        .filter(PontoCompetencia.tenant_id == admin.tenant_id)
    )
    if ano is not None:
        q = q.filter(PontoCompetencia.ano == ano)
    rows = q.order_by(PontoCompetencia.ano.desc(), PontoCompetencia.mes.desc()).limit(36).all()
    return [_to_comp_read(r) for r in rows]


def invalidar_ciencias_mes(
    db: Session,
    *,
    tenant_id: int,
    atendente_id: int,
    ano: int,
    mes: int,
    motivo: str,
) -> None:
    row = (
        db.query(PontoEspelhoCiencia)
        .filter(
            PontoEspelhoCiencia.tenant_id == tenant_id,
            PontoEspelhoCiencia.atendente_id == atendente_id,
            PontoEspelhoCiencia.ano == ano,
            PontoEspelhoCiencia.mes == mes,
            PontoEspelhoCiencia.ativa.is_(True),
        )
        .first()
    )
    if not row:
        return
    row.ativa = False
    row.invalidada_em = datetime.now(timezone.utc)
    row.invalidada_motivo = motivo[:500]


def confirmar_ciencia(db: Session, atendente: Atendente, *, ano: int, mes: int) -> PontoCienciaMe:
    ponto_svc.exigir_acesso_ponto(atendente)
    _validar_ano_mes(ano, mes)
    if not competencia_fechada(db, atendente.tenant_id, ano=ano, mes=mes):
        raise HTTPException(
            status_code=400,
            detail="Só é possível confirmar ciência após o admin fechar a competência do mês.",
        )
    existente = (
        db.query(PontoEspelhoCiencia)
        .filter(
            PontoEspelhoCiencia.tenant_id == atendente.tenant_id,
            PontoEspelhoCiencia.atendente_id == atendente.id,
            PontoEspelhoCiencia.ano == ano,
            PontoEspelhoCiencia.mes == mes,
        )
        .first()
    )
    agora = datetime.now(timezone.utc)
    if existente and existente.ativa:
        raise HTTPException(status_code=400, detail="Ciência deste mês já confirmada.")
    if existente:
        existente.ativa = True
        existente.confirmado_em = agora
        existente.invalidada_em = None
        existente.invalidada_motivo = None
        row = existente
    else:
        row = PontoEspelhoCiencia(
            tenant_id=atendente.tenant_id,
            atendente_id=atendente.id,
            ano=ano,
            mes=mes,
            confirmado_em=agora,
            ativa=True,
        )
        db.add(row)
        db.flush()
    registrar_audit(
        db,
        "ponto_espelho_ciencia",
        row.id,
        "confirmar",
        atendente.id,
        payload={"ano": ano, "mes": mes, "confirmado_em": agora.isoformat()},
    )
    db.commit()
    return ciencia_me(db, atendente, ano=ano, mes=mes)


def ciencia_me(db: Session, atendente: Atendente, *, ano: int, mes: int) -> PontoCienciaMe:
    ponto_svc.exigir_acesso_ponto(atendente)
    _validar_ano_mes(ano, mes)
    fechada = competencia_fechada(db, atendente.tenant_id, ano=ano, mes=mes)
    row = (
        db.query(PontoEspelhoCiencia)
        .filter(
            PontoEspelhoCiencia.tenant_id == atendente.tenant_id,
            PontoEspelhoCiencia.atendente_id == atendente.id,
            PontoEspelhoCiencia.ano == ano,
            PontoEspelhoCiencia.mes == mes,
        )
        .first()
    )
    return PontoCienciaMe(
        ano=ano,
        mes=mes,
        competencia_fechada=fechada,
        confirmada=bool(row and row.ativa),
        confirmado_em=row.confirmado_em if row and row.ativa else None,
        pode_confirmar=fechada and not (row and row.ativa),
    )


def listar_ciencias_admin(
    db: Session,
    admin: Atendente,
    *,
    ano: int,
    mes: int,
) -> list[PontoCienciaItem]:
    _validar_ano_mes(ano, mes)
    ativos = (
        db.query(Atendente)
        .filter(
            Atendente.tenant_id == admin.tenant_id,
            Atendente.ativo.is_(True),
            Atendente.role.in_(tuple(ROLES_ATENDENTE)),
        )
        .order_by(Atendente.nome.asc())
        .all()
    )
    rows = (
        db.query(PontoEspelhoCiencia)
        .filter(
            PontoEspelhoCiencia.tenant_id == admin.tenant_id,
            PontoEspelhoCiencia.ano == ano,
            PontoEspelhoCiencia.mes == mes,
            PontoEspelhoCiencia.ativa.is_(True),
        )
        .all()
    )
    por_id = {r.atendente_id: r for r in rows}
    out: list[PontoCienciaItem] = []
    for a in ativos:
        c = por_id.get(a.id)
        out.append(
            PontoCienciaItem(
                atendente_id=a.id,
                atendente_nome=a.nome,
                confirmada=c is not None,
                confirmado_em=c.confirmado_em if c else None,
            )
        )
    return out


def periodo_competencia(ano: int, mes: int) -> tuple[date, date]:
    _validar_ano_mes(ano, mes)
    ultimo = monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo)
