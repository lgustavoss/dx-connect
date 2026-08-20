"""Serviço de batidas de ponto (#762 / #766 / #767 / #768)."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
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
TIPOS_VALIDOS = frozenset({"entrada", "saida", "pausa_inicio", "pausa_fim"})
TIPOS_EM_JORNADA = frozenset({"entrada", "pausa_inicio", "pausa_fim"})


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


def _q_ativas(db: Session):
    return db.query(PontoBatida).filter(PontoBatida.anulada.is_(False))


def ultima_batida(db: Session, atendente_id: int) -> PontoBatida | None:
    return (
        _q_ativas(db)
        .filter(PontoBatida.atendente_id == atendente_id)
        .order_by(PontoBatida.registrado_em.desc(), PontoBatida.id.desc())
        .first()
    )


def _entrada_da_jornada_aberta(db: Session, atendente_id: int) -> PontoBatida | None:
    """Retorna a entrada que abriu a jornada atual (se houver)."""
    batidas = (
        _q_ativas(db)
        .filter(PontoBatida.atendente_id == atendente_id)
        .order_by(PontoBatida.registrado_em.desc(), PontoBatida.id.desc())
        .limit(200)
        .all()
    )
    for b in batidas:
        if b.tipo == "saida":
            return None
        if b.tipo == "entrada":
            return b
    return None


def em_jornada_aberta(db: Session, atendente_id: int) -> bool:
    ultima = ultima_batida(db, atendente_id)
    return bool(ultima and ultima.tipo in TIPOS_EM_JORNADA)


def em_pausa_aberta(db: Session, atendente_id: int) -> bool:
    ultima = ultima_batida(db, atendente_id)
    return bool(ultima and ultima.tipo == "pausa_inicio")


def entrada_aberta(db: Session, atendente_id: int) -> PontoBatida | None:
    """Compat: entrada da jornada aberta (não necessariamente a última batida)."""
    return _entrada_da_jornada_aberta(db, atendente_id)


def estado_atual(db: Session, atendente: Atendente) -> PontoEstadoRead:
    ultima = ultima_batida(db, atendente.id)
    entrada = _entrada_da_jornada_aberta(db, atendente.id)
    hoje = datetime.now(PONTO_TZ).date()
    hoje_esp = None
    rotulo = None
    if escala_svc.escala_configurada(atendente):
        hoje_esp = escala_svc.eh_dia_de_trabalho(atendente, hoje)
        rotulo = escala_svc.rotulo_escala(atendente.escala_horas_trabalho, atendente.escala_horas_folga)
    return PontoEstadoRead(
        em_jornada=entrada is not None,
        em_pausa=bool(ultima and ultima.tipo == "pausa_inicio"),
        entrada_aberta_em=entrada.registrado_em if entrada else None,
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
    registrado_em: datetime | None = None,
    commit: bool = True,
) -> PontoBatida:
    exigir_acesso_ponto(atendente)
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo inválido de batida.")

    ultima = ultima_batida(db, atendente.id)
    em_jornada = bool(ultima and ultima.tipo in TIPOS_EM_JORNADA)
    em_pausa = bool(ultima and ultima.tipo == "pausa_inicio")

    if tipo == "entrada":
        if em_jornada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma jornada aberta. Registre a saída antes de uma nova entrada.",
            )
    elif tipo == "saida":
        if not em_jornada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não há jornada aberta para registrar saída.",
            )
        if em_pausa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encerre a pausa antes de registrar a saída.",
            )
    elif tipo == "pausa_inicio":
        if not em_jornada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível pausar com jornada aberta.",
            )
        if em_pausa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma pausa em andamento.",
            )
    elif tipo == "pausa_fim":
        if not em_pausa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não há pausa aberta para retomar.",
            )

    when = registrado_em or _agora_utc()
    batida = PontoBatida(
        tenant_id=atendente.tenant_id,
        atendente_id=atendente.id,
        tipo=tipo,
        registrado_em=_as_utc(when),
        origem=origem or "web",
        ip=ip,
        user_agent=(user_agent or "")[:512] or None,
        anulada=False,
    )
    db.add(batida)
    if commit:
        db.commit()
        db.refresh(batida)
    else:
        db.flush()
    return batida


def _segundos_pausas_no_bloco(bloco: list[PontoBatida]) -> int:
    total = 0
    pendente: PontoBatida | None = None
    for b in bloco:
        if b.tipo == "pausa_inicio":
            pendente = b
        elif b.tipo == "pausa_fim" and pendente is not None:
            total += max(0, int((_as_utc(b.registrado_em) - _as_utc(pendente.registrado_em)).total_seconds()))
            pendente = None
    return total


def _intervalos_de_batidas(batidas: list[PontoBatida]) -> list[PontoIntervaloRead]:
    """Emparelha entrada→saída; pausas reduzem o tempo trabalhado."""
    ordenadas = sorted(batidas, key=lambda b: (_as_utc(b.registrado_em), b.id))
    intervalos: list[PontoIntervaloRead] = []
    i = 0
    while i < len(ordenadas):
        b = ordenadas[i]
        if b.tipo != "entrada":
            i += 1
            continue
        entrada = b
        bloco: list[PontoBatida] = [entrada]
        saida: PontoBatida | None = None
        i += 1
        while i < len(ordenadas):
            cur = ordenadas[i]
            if cur.tipo == "entrada":
                break
            bloco.append(cur)
            i += 1
            if cur.tipo == "saida":
                saida = cur
                break
        pausas = _segundos_pausas_no_bloco(bloco)
        if saida is None:
            intervalos.append(
                PontoIntervaloRead(
                    data=_data_negocio(entrada.registrado_em),
                    entrada_em=entrada.registrado_em,
                    saida_em=None,
                    duracao_segundos=None,
                    segundos_pausa=pausas,
                    aberto=True,
                )
            )
        else:
            bruto = max(0, int((_as_utc(saida.registrado_em) - _as_utc(entrada.registrado_em)).total_seconds()))
            trabalhado = max(0, bruto - pausas)
            intervalos.append(
                PontoIntervaloRead(
                    data=_data_negocio(entrada.registrado_em),
                    entrada_em=entrada.registrado_em,
                    saida_em=saida.registrado_em,
                    duracao_segundos=trabalhado,
                    segundos_pausa=pausas,
                    aberto=False,
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
    q = _q_ativas(db).filter(PontoBatida.atendente_id == atendente.id)
    inicio, fim = _bounds_periodo(desde, ate)
    if inicio is not None:
        q = q.filter(PontoBatida.registrado_em >= inicio)
    if fim is not None:
        q = q.filter(PontoBatida.registrado_em < fim)
    batidas = q.order_by(PontoBatida.registrado_em.asc(), PontoBatida.id.asc()).all()
    intervalos = _intervalos_de_batidas(batidas)
    total_seg = sum(i.duracao_segundos or 0 for i in intervalos if not i.aberto)
    total_pausa = sum(i.segundos_pausa for i in intervalos)
    page = intervalos[offset : offset + limit]
    return PontoHistoricoRead(
        intervalos=page,
        total_segundos_fechados=total_seg,
        total_segundos_pausa=total_pausa,
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
    incluir_anuladas: bool = False,
) -> tuple[list[PontoBatidaAdminItem], int]:
    q = (
        db.query(PontoBatida, Atendente)
        .join(Atendente, Atendente.id == PontoBatida.atendente_id)
        .filter(PontoBatida.tenant_id == admin.tenant_id)
    )
    if not incluir_anuladas:
        q = q.filter(PontoBatida.anulada.is_(False))
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
            anulada=bool(b.anulada),
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
        _q_ativas(db)
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
    from app.services.presenca import PRESENCA_TTL_SEC

    hoje = datetime.now(PONTO_TZ).date()
    agora = _agora_utc()
    limite_online = agora - timedelta(seconds=PRESENCA_TTL_SEC)
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
        entrada = _entrada_da_jornada_aberta(db, a.id)
        inicio, fim = _bounds_periodo(hoje, hoje)
        bats = (
            _q_ativas(db)
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
        hb = a.presenca_heartbeat_em
        if hb is not None and hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        online = bool(hb and hb >= limite_online)
        online_sem = online and entrada is None
        itens.append(
            PontoHojeItem(
                atendente_id=a.id,
                nome=a.nome,
                esperado=esperado,
                em_jornada=entrada is not None,
                em_pausa=em_pausa_aberta(db, a.id),
                entrada_em=entrada.registrado_em if entrada else None,
                status=st,  # type: ignore[arg-type]
                online=online,
                online_sem_ponto=online_sem,
            )
        )
    return PontoHojeRead(data=hoje, itens=itens)


JORNADA_ALERTA_HORAS = 12.0


def alertas_me(db: Session, atendente: Atendente) -> "PontoAlertasMe":
    from app.schemas.ponto import PontoAlertasMe
    from app.services.presenca import PRESENCA_TTL_SEC

    exigir_acesso_ponto(atendente)
    hoje = datetime.now(PONTO_TZ).date()
    agora = _agora_utc()
    msgs: list[str] = []
    sem_entrada = False
    online_sem = False
    jornada_longa = False
    horas_aberta: float | None = None

    esperado = None
    if escala_svc.escala_configurada(atendente):
        esperado = escala_svc.eh_dia_de_trabalho(atendente, hoje)

    entrada = _entrada_da_jornada_aberta(db, atendente.id)
    inicio, fim = _bounds_periodo(hoje, hoje)
    tem_entrada_hoje = (
        _q_ativas(db)
        .filter(
            PontoBatida.atendente_id == atendente.id,
            PontoBatida.tipo == "entrada",
            PontoBatida.registrado_em >= inicio,
            PontoBatida.registrado_em < fim,
        )
        .first()
        is not None
    )

    hb = atendente.presenca_heartbeat_em
    if hb is not None and hb.tzinfo is None:
        hb = hb.replace(tzinfo=timezone.utc)
    online = bool(hb and hb >= agora - timedelta(seconds=PRESENCA_TTL_SEC))

    if esperado is True and not tem_entrada_hoje and entrada is None:
        sem_entrada = True
        msgs.append("Hoje é dia de trabalho na sua escala e ainda não há entrada registrada.")

    if online and entrada is None:
        online_sem = True
        if "ainda não há entrada" not in " ".join(msgs).lower():
            msgs.append("Você está online no painel sem jornada de ponto aberta.")

    if entrada is not None:
        horas_aberta = (_as_utc(agora) - _as_utc(entrada.registrado_em)).total_seconds() / 3600.0
        if horas_aberta >= JORNADA_ALERTA_HORAS:
            jornada_longa = True
            msgs.append(
                f"Jornada aberta há cerca de {horas_aberta:.0f} h — lembre-se de registrar a saída."
            )

    return PontoAlertasMe(
        sem_entrada_em_dia_escala=sem_entrada,
        online_sem_ponto=online_sem,
        jornada_aberta_longa=jornada_longa,
        horas_jornada_aberta=horas_aberta,
        mensagens=msgs,
    )


def _atendente_do_tenant(db: Session, tenant_id: int, atendente_id: int) -> Atendente:
    alvo = (
        db.query(Atendente)
        .filter(Atendente.id == atendente_id, Atendente.tenant_id == tenant_id)
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado")
    return alvo


def admin_criar_batida(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int,
    tipo: str,
    registrado_em: datetime,
    motivo: str,
    commit: bool = True,
) -> PontoBatida:
    alvo = _atendente_do_tenant(db, admin.tenant_id, atendente_id)
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Tipo inválido")
    batida = PontoBatida(
        tenant_id=admin.tenant_id,
        atendente_id=alvo.id,
        tipo=tipo,
        registrado_em=_as_utc(registrado_em),
        origem="admin",
        anulada=False,
    )
    db.add(batida)
    db.flush()
    registrar_audit(
        db,
        "ponto_batida",
        batida.id,
        "create_ajuste",
        admin.id,
        payload={
            "motivo": motivo,
            "atendente_id": alvo.id,
            "tipo": tipo,
            "registrado_em": _as_utc(registrado_em).isoformat(),
        },
    )
    if commit:
        db.commit()
        db.refresh(batida)
    return batida


def admin_atualizar_batida(
    db: Session,
    admin: Atendente,
    batida_id: int,
    *,
    tipo: str | None,
    registrado_em: datetime | None,
    motivo: str,
) -> PontoBatida:
    batida = (
        db.query(PontoBatida)
        .filter(PontoBatida.id == batida_id, PontoBatida.tenant_id == admin.tenant_id)
        .first()
    )
    if not batida or batida.anulada:
        raise HTTPException(status_code=404, detail="Batida não encontrada")
    antes = {"tipo": batida.tipo, "registrado_em": batida.registrado_em.isoformat()}
    if tipo is not None:
        if tipo not in TIPOS_VALIDOS:
            raise HTTPException(status_code=400, detail="Tipo inválido")
        batida.tipo = tipo
    if registrado_em is not None:
        batida.registrado_em = _as_utc(registrado_em)
    batida.origem = batida.origem or "admin"
    registrar_audit(
        db,
        "ponto_batida",
        batida.id,
        "update_ajuste",
        admin.id,
        payload={"motivo": motivo, "antes": antes, "depois": {"tipo": batida.tipo, "registrado_em": batida.registrado_em.isoformat()}},
    )
    db.commit()
    db.refresh(batida)
    return batida


def admin_anular_batida(db: Session, admin: Atendente, batida_id: int, *, motivo: str) -> PontoBatida:
    batida = (
        db.query(PontoBatida)
        .filter(PontoBatida.id == batida_id, PontoBatida.tenant_id == admin.tenant_id)
        .first()
    )
    if not batida or batida.anulada:
        raise HTTPException(status_code=404, detail="Batida não encontrada")
    batida.anulada = True
    registrar_audit(
        db,
        "ponto_batida",
        batida.id,
        "anular",
        admin.id,
        payload={
            "motivo": motivo,
            "tipo": batida.tipo,
            "registrado_em": batida.registrado_em.isoformat(),
            "atendente_id": batida.atendente_id,
        },
    )
    db.commit()
    db.refresh(batida)
    return batida


def export_csv_admin(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date | None,
    ate: date | None,
) -> str:
    """CSV UTF-8 com BOM: intervalos (entrada/saída/pausas/trabalhado)."""
    q = _q_ativas(db).filter(PontoBatida.tenant_id == admin.tenant_id)
    if atendente_id is not None:
        q = q.filter(PontoBatida.atendente_id == atendente_id)
    inicio, fim = _bounds_periodo(desde, ate)
    if inicio is not None:
        q = q.filter(PontoBatida.registrado_em >= inicio)
    if fim is not None:
        q = q.filter(PontoBatida.registrado_em < fim)
    batidas = q.order_by(PontoBatida.atendente_id.asc(), PontoBatida.registrado_em.asc(), PontoBatida.id.asc()).all()

    nomes = {
        a.id: a.nome
        for a in db.query(Atendente).filter(Atendente.tenant_id == admin.tenant_id).all()
    }

    por_atendente: dict[int, list[PontoBatida]] = {}
    for b in batidas:
        por_atendente.setdefault(b.atendente_id, []).append(b)

    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["atendente", "data", "entrada", "saida", "pausas_min", "trabalhado_min", "aberto"])
    for aid, bats in por_atendente.items():
        for it in _intervalos_de_batidas(bats):
            writer.writerow(
                [
                    nomes.get(aid, str(aid)),
                    it.data.isoformat(),
                    _as_utc(it.entrada_em).astimezone(PONTO_TZ).strftime("%Y-%m-%d %H:%M"),
                    _as_utc(it.saida_em).astimezone(PONTO_TZ).strftime("%Y-%m-%d %H:%M") if it.saida_em else "",
                    round((it.segundos_pausa or 0) / 60, 2),
                    round((it.duracao_segundos or 0) / 60, 2) if it.duracao_segundos is not None else "",
                    "sim" if it.aberto else "nao",
                ]
            )
    return buf.getvalue()
