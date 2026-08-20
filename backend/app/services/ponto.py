"""Serviço de batidas de ponto (#762)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import ROLES_ATENDENTE
from app.models.atendente import Atendente
from app.models.ponto_batida import PontoBatida
from app.schemas.ponto import (
    PontoBatidaAdminItem,
    PontoBatidaRead,
    PontoCalendarioDia,
    PontoCalendarioRead,
    PontoEstadoRead,
    PontoHistoricoRead,
    PontoHojeItem,
    PontoHojeRead,
    PontoIntervaloRead,
)
from app.services import escala as escala_svc

PONTO_TZ = ZoneInfo("America/Sao_Paulo")


def exigir_acesso_ponto(atendente: Atendente) -> Atendente:
    if atendente.role not in ROLES_ATENDENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Controle de ponto indisponível para este perfil",
        )
    return atendente


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _data_negocio(dt: datetime) -> date:
    return _as_utc(dt).astimezone(PONTO_TZ).date()


def _bounds_periodo(desde: date | None, ate: date | None) -> tuple[datetime | None, datetime | None]:
    inicio = None
    fim = None
    if desde is not None:
        inicio = datetime.combine(desde, time.min, tzinfo=PONTO_TZ).astimezone(timezone.utc)
    if ate is not None:
        fim = datetime.combine(ate + timedelta(days=1), time.min, tzinfo=PONTO_TZ).astimezone(timezone.utc)
    return inicio, fim


def ultima_batida(db: Session, atendente_id: int) -> PontoBatida | None:
    return (
        db.query(PontoBatida)
        .filter(PontoBatida.atendente_id == atendente_id)
        .order_by(PontoBatida.registrado_em.desc(), PontoBatida.id.desc())
        .first()
    )


def entrada_aberta(db: Session, atendente_id: int) -> PontoBatida | None:
    ultima = ultima_batida(db, atendente_id)
    if ultima and ultima.tipo == "entrada":
        return ultima
    return None


def estado_atual(db: Session, atendente: Atendente) -> PontoEstadoRead:
    ultima = ultima_batida(db, atendente.id)
    aberta = entrada_aberta(db, atendente.id)
    hoje = datetime.now(PONTO_TZ).date()
    hoje_esp = None
    rotulo = None
    if escala_svc.escala_configurada(atendente):
        hoje_esp = escala_svc.eh_dia_de_trabalho(atendente, hoje)
        rotulo = escala_svc.rotulo_escala(atendente.escala_horas_trabalho, atendente.escala_horas_folga)
    return PontoEstadoRead(
        em_jornada=aberta is not None,
        entrada_aberta_em=aberta.registrado_em if aberta else None,
        ultima_batida=PontoBatidaRead.model_validate(ultima) if ultima else None,
        usa_escala=bool(getattr(atendente, "usa_escala", False)),
        hoje_esperado=hoje_esp,
        escala_rotulo=rotulo,
    )


def bater(
    db: Session,
    atendente: Atendente,
    tipo: str,
    *,
    origem: str | None = "web",
    ip: str | None = None,
    user_agent: str | None = None,
) -> PontoBatida:
    exigir_acesso_ponto(atendente)
    aberta = entrada_aberta(db, atendente.id)
    if tipo == "entrada":
        if aberta is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma entrada aberta. Registre a saída antes de uma nova entrada.",
            )
    elif tipo == "saida":
        if aberta is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não há entrada aberta para registrar saída.",
            )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo inválido: use entrada ou saida")

    batida = PontoBatida(
        tenant_id=atendente.tenant_id,
        atendente_id=atendente.id,
        tipo=tipo,
        registrado_em=_agora_utc(),
        origem=origem or "web",
        ip=ip,
        user_agent=(user_agent or "")[:512] or None,
    )
    db.add(batida)
    db.commit()
    db.refresh(batida)
    return batida


def _intervalos_de_batidas(batidas: list[PontoBatida]) -> list[PontoIntervaloRead]:
    """Emparelha entrada→saída em ordem cronológica (ideia dx-ponto / Periods)."""
    ordenadas = sorted(batidas, key=lambda b: (_as_utc(b.registrado_em), b.id))
    intervalos: list[PontoIntervaloRead] = []
    pendente: PontoBatida | None = None
    for b in ordenadas:
        if b.tipo == "entrada":
            if pendente is not None:
                # Entrada órfã anterior — fecha como aberto sem saída
                intervalos.append(
                    PontoIntervaloRead(
                        data=_data_negocio(pendente.registrado_em),
                        entrada_em=pendente.registrado_em,
                        saida_em=None,
                        duracao_segundos=None,
                        aberto=True,
                    )
                )
            pendente = b
        elif b.tipo == "saida":
            if pendente is None:
                continue
            entrada = pendente
            saida = b
            dur = int((_as_utc(saida.registrado_em) - _as_utc(entrada.registrado_em)).total_seconds())
            intervalos.append(
                PontoIntervaloRead(
                    data=_data_negocio(entrada.registrado_em),
                    entrada_em=entrada.registrado_em,
                    saida_em=saida.registrado_em,
                    duracao_segundos=max(0, dur),
                    aberto=False,
                )
            )
            pendente = None
    if pendente is not None:
        intervalos.append(
            PontoIntervaloRead(
                data=_data_negocio(pendente.registrado_em),
                entrada_em=pendente.registrado_em,
                saida_em=None,
                duracao_segundos=None,
                aberto=True,
            )
        )
    return intervalos


def historico(
    db: Session,
    atendente: Atendente,
    *,
    desde: date | None,
    ate: date | None,
    offset: int = 0,
    limit: int = 50,
) -> PontoHistoricoRead:
    q = db.query(PontoBatida).filter(PontoBatida.atendente_id == atendente.id)
    inicio, fim = _bounds_periodo(desde, ate)
    if inicio is not None:
        q = q.filter(PontoBatida.registrado_em >= inicio)
    if fim is not None:
        q = q.filter(PontoBatida.registrado_em < fim)
    batidas = q.order_by(PontoBatida.registrado_em.asc(), PontoBatida.id.asc()).all()
    intervalos = _intervalos_de_batidas(batidas)
    total_seg = sum(i.duracao_segundos or 0 for i in intervalos if not i.aberto)
    page = intervalos[offset : offset + limit]
    return PontoHistoricoRead(
        intervalos=page,
        total_segundos_fechados=total_seg,
        total=len(intervalos),
    )


def listar_batidas_admin(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date | None,
    ate: date | None,
    offset: int,
    limit: int,
) -> tuple[list[PontoBatidaAdminItem], int]:
    q = (
        db.query(PontoBatida, Atendente)
        .join(Atendente, Atendente.id == PontoBatida.atendente_id)
        .filter(PontoBatida.tenant_id == admin.tenant_id)
    )
    if atendente_id is not None:
        q = q.filter(PontoBatida.atendente_id == atendente_id)
    inicio, fim = _bounds_periodo(desde, ate)
    if inicio is not None:
        q = q.filter(PontoBatida.registrado_em >= inicio)
    if fim is not None:
        q = q.filter(PontoBatida.registrado_em < fim)
    total = q.count()
    rows = (
        q.order_by(PontoBatida.registrado_em.desc(), PontoBatida.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    itens = [
        PontoBatidaAdminItem(
            id=b.id,
            atendente_id=b.atendente_id,
            atendente_nome=a.nome,
            tipo=b.tipo,
            registrado_em=b.registrado_em,
            origem=b.origem,
        )
        for b, a in rows
    ]
    return itens, total


def _status_dia(
    *,
    usa_escala: bool,
    esperado: bool,
    tem_entrada: bool,
    tem_saida: bool,
) -> str:
    if not usa_escala:
        if tem_entrada and tem_saida:
            return "ok"
        if tem_entrada:
            return "parcial"
        return "livre"
    if esperado:
        if tem_entrada and tem_saida:
            return "ok"
        if tem_entrada:
            return "parcial"
        return "falta"
    if tem_entrada or tem_saida:
        return "folga_com_ponto"
    return "folga"


def calendario(
    db: Session,
    atendente: Atendente,
    ano: int,
    mes: int,
) -> PontoCalendarioRead:
    dias_mes = escala_svc.dias_do_mes(ano, mes)
    if not dias_mes:
        return PontoCalendarioRead(atendente_id=atendente.id, ano=ano, mes=mes, usa_escala=False, dias=[])
    desde, ate = dias_mes[0], dias_mes[-1]
    inicio, fim = _bounds_periodo(desde, ate)
    batidas = (
        db.query(PontoBatida)
        .filter(
            PontoBatida.atendente_id == atendente.id,
            PontoBatida.registrado_em >= inicio,
            PontoBatida.registrado_em < fim,
        )
        .all()
    )
    por_dia: dict[date, dict[str, bool]] = {}
    for b in batidas:
        d = _data_negocio(b.registrado_em)
        slot = por_dia.setdefault(d, {"entrada": False, "saida": False})
        if b.tipo == "entrada":
            slot["entrada"] = True
        elif b.tipo == "saida":
            slot["saida"] = True

    usa = escala_svc.escala_configurada(atendente)
    dias_out: list[PontoCalendarioDia] = []
    for d in dias_mes:
        esp = escala_svc.eh_dia_de_trabalho(atendente, d) if usa else False
        slot = por_dia.get(d, {"entrada": False, "saida": False})
        te, ts = slot["entrada"], slot["saida"]
        dias_out.append(
            PontoCalendarioDia(
                data=d,
                esperado=esp,
                tem_entrada=te,
                tem_saida=ts,
                status=_status_dia(usa_escala=usa, esperado=esp, tem_entrada=te, tem_saida=ts),  # type: ignore[arg-type]
            )
        )
    return PontoCalendarioRead(
        atendente_id=atendente.id,
        ano=ano,
        mes=mes,
        usa_escala=bool(getattr(atendente, "usa_escala", False)),
        escala_rotulo=escala_svc.rotulo_escala(
            atendente.escala_horas_trabalho,
            atendente.escala_horas_folga,
        )
        if getattr(atendente, "usa_escala", False)
        else None,
        dias=dias_out,
    )


def visao_hoje(db: Session, admin: Atendente) -> PontoHojeRead:
    hoje = datetime.now(PONTO_TZ).date()
    atendentes = (
        db.query(Atendente)
        .filter(
            Atendente.tenant_id == admin.tenant_id,
            Atendente.ativo.is_(True),
            Atendente.role.in_(tuple(ROLES_ATENDENTE)),
        )
        .order_by(Atendente.nome.asc())
        .all()
    )
    itens: list[PontoHojeItem] = []
    for a in atendentes:
        usa = escala_svc.escala_configurada(a)
        esperado = escala_svc.eh_dia_de_trabalho(a, hoje) if usa else False
        aberta = entrada_aberta(db, a.id)
        inicio, fim = _bounds_periodo(hoje, hoje)
        bats = (
            db.query(PontoBatida)
            .filter(
                PontoBatida.atendente_id == a.id,
                PontoBatida.registrado_em >= inicio,
                PontoBatida.registrado_em < fim,
            )
            .all()
        )
        te = any(b.tipo == "entrada" for b in bats)
        ts = any(b.tipo == "saida" for b in bats)
        st = _status_dia(usa_escala=usa, esperado=esperado, tem_entrada=te, tem_saida=ts)
        itens.append(
            PontoHojeItem(
                atendente_id=a.id,
                nome=a.nome,
                esperado=esperado,
                em_jornada=aberta is not None,
                entrada_em=aberta.registrado_em if aberta else None,
                status=st,  # type: ignore[arg-type]
            )
        )
    return PontoHojeRead(data=hoje, itens=itens)
