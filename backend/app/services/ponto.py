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
    PontoBancoHorasRead,
    PontoCalendarioDia,
    PontoCalendarioRead,
    PontoDigestRead,
    PontoEstadoRead,
    PontoHistoricoRead,
    PontoHojeItem,
    PontoHojeRead,
    PontoIntervaloRead,
)
from app.services import escala as escala_svc
from app.services import ponto_settings as ponto_settings_svc

PONTO_TZ = ZoneInfo("America/Sao_Paulo")
TIPOS_VALIDOS = frozenset({"entrada", "saida", "pausa_inicio", "pausa_fim"})
TIPOS_EM_JORNADA = frozenset({"entrada", "pausa_inicio", "pausa_fim"})
ORIGENS_VALIDAS = frozenset({"web", "mobile", "admin", "sistema"})


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
        rotulo = escala_svc.rotulo_jornada(atendente)
    return PontoEstadoRead(
        em_jornada=entrada is not None,
        em_pausa=bool(ultima and ultima.tipo == "pausa_inicio"),
        entrada_aberta_em=entrada.registrado_em if entrada else None,
        ultima_batida=PontoBatidaRead.model_validate(ultima) if ultima else None,
        usa_escala=escala_svc.escala_configurada(atendente),
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
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_metros: float | None = None,
    commit: bool = True,
) -> PontoBatida:
    exigir_acesso_ponto(atendente)
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo inválido de batida.")

    has_lat = latitude is not None
    has_lon = longitude is not None
    if has_lat != has_lon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe latitude e longitude juntos, ou omita ambas.",
        )
    if has_lat and (latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordenadas inválidas.")

    from app.services import ponto_geofence as geo_svc

    geo_res = geo_svc.validar_batida_geolocalizacao(
        db,
        atendente,
        latitude=float(latitude) if has_lat else None,
        longitude=float(longitude) if has_lon else None,
    )

    ultima = ultima_batida(db, atendente.id)
    em_jornada = bool(ultima and ultima.tipo in TIPOS_EM_JORNADA)
    em_pausa = bool(ultima and ultima.tipo == "pausa_inicio")

    if tipo == "entrada":
        if em_jornada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma jornada aberta. Registre a saída antes de uma nova entrada.",
            )
        origem_chk = (origem or "web").strip().lower()
        if origem_chk not in ("admin", "sistema"):
            when_chk = registrado_em or _agora_utc()
            escala_svc.validar_janela_entrada(atendente, when_chk)
    elif tipo == "saida":
        if not em_jornada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não há jornada aberta para registrar saída.",
            )
        if em_pausa:
            # #841: fecha a pausa automaticamente no mesmo instante (origem sistema).
            when_auto = registrado_em or _agora_utc()
            bater(
                db,
                atendente,
                "pausa_fim",
                origem="sistema",
                ip=ip,
                user_agent=user_agent,
                registrado_em=when_auto,
                commit=False,
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
    origem_norm = (origem or "web").strip().lower()
    if origem_norm not in ORIGENS_VALIDAS:
        origem_norm = "web"
    batida = PontoBatida(
        tenant_id=atendente.tenant_id,
        atendente_id=atendente.id,
        tipo=tipo,
        registrado_em=_as_utc(when),
        origem=origem_norm,
        ip=ip,
        user_agent=(user_agent or "")[:512] or None,
        latitude=float(latitude) if has_lat else None,
        longitude=float(longitude) if has_lon else None,
        accuracy_metros=float(accuracy_metros) if accuracy_metros is not None and has_lat else None,
        fora_area=bool(geo_res.fora_area),
        distancia_metros=geo_res.distancia_metros,
        local_id=geo_res.local_id,
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
                    entrada_latitude=entrada.latitude,
                    entrada_longitude=entrada.longitude,
                    entrada_fora_area=bool(getattr(entrada, "fora_area", False)),
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
                    entrada_latitude=entrada.latitude,
                    entrada_longitude=entrada.longitude,
                    entrada_fora_area=bool(getattr(entrada, "fora_area", False)),
                    saida_latitude=saida.latitude,
                    saida_longitude=saida.longitude,
                    saida_fora_area=bool(getattr(saida, "fora_area", False)),
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
            latitude=getattr(b, "latitude", None),
            longitude=getattr(b, "longitude", None),
            accuracy_metros=getattr(b, "accuracy_metros", None),
            fora_area=bool(getattr(b, "fora_area", False)),
            distancia_metros=getattr(b, "distancia_metros", None),
            local_id=getattr(b, "local_id", None),
            anulada=bool(b.anulada),
        )
        for b, a in rows
    ]
    return itens, total


def _primeira_entrada_do_dia(batidas_dia: list[PontoBatida]) -> PontoBatida | None:
    entradas = [b for b in batidas_dia if b.tipo == "entrada"]
    if not entradas:
        return None
    return min(entradas, key=lambda b: (_as_utc(b.registrado_em), b.id))


def _atrasado_entrada(atendente: Atendente, entrada: PontoBatida | None) -> bool:
    """True se a 1ª entrada passou inicio + tolerância (dentro da tol = não atraso)."""
    if entrada is None:
        return False
    if not escala_svc.escala_configurada(atendente):
        return False
    local = _as_utc(entrada.registrado_em).astimezone(PONTO_TZ)
    limite = escala_svc.limite_atraso_em(atendente, local.date())
    if limite is None:
        return False
    return local > limite


def _status_dia(
    *,
    usa_escala: bool,
    esperado: bool,
    tem_entrada: bool,
    tem_saida: bool,
    feriado: bool = False,
    atrasado: bool = False,
) -> str:
    if feriado:
        if tem_entrada and tem_saida:
            return "ok"
        if tem_entrada:
            return "parcial"
        return "feriado"
    if not usa_escala:
        if tem_entrada and tem_saida:
            return "atraso" if atrasado else "ok"
        if tem_entrada:
            return "parcial"
        return "livre"
    if esperado:
        if tem_entrada and tem_saida:
            return "atraso" if atrasado else "ok"
        if tem_entrada:
            return "parcial"
        return "falta"
    if tem_entrada or tem_saida:
        return "folga_com_ponto"
    return "folga"


def _classe_visual_dia(
    *,
    feriado: bool,
    esperado: bool,
    segundos_trabalhados: int,
    segundos_esperados: int,
) -> str:
    """Paleta #842: vermelho abaixo / verde ok / azul HE / laranja feriado."""
    if feriado:
        return "feriado"
    meta = segundos_esperados if segundos_esperados > 0 else 0
    if segundos_trabalhados <= 0:
        return "abaixo" if esperado else "neutro"
    if meta <= 0:
        return "ok"
    if segundos_trabalhados < meta:
        return "abaixo"
    if segundos_trabalhados > meta:
        return "he"
    return "ok"


def calendario(
    db: Session,
    atendente: Atendente,
    ano: int,
    mes: int,
) -> PontoCalendarioRead:
    dias_mes = escala_svc.dias_do_mes(ano, mes)
    settings = ponto_settings_svc.get_or_create_settings(db, atendente.tenant_id)
    jornada_min = int(getattr(settings, "jornada_diaria_minutos", None) or 480)
    meta_default = jornada_min * 60
    if not dias_mes:
        return PontoCalendarioRead(
            atendente_id=atendente.id,
            ano=ano,
            mes=mes,
            usa_escala=False,
            jornada_diaria_minutos=jornada_min,
            dias=[],
        )
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
    por_dia: dict[date, list[PontoBatida]] = {}
    for b in batidas:
        d = _data_negocio(b.registrado_em)
        por_dia.setdefault(d, []).append(b)

    usa = escala_svc.escala_configurada(atendente)
    dias_out: list[PontoCalendarioDia] = []
    for d in dias_mes:
        feriado = ponto_settings_svc.eh_feriado(db, atendente.tenant_id, d)
        esp = escala_svc.eh_dia_de_trabalho(atendente, d) if usa else False
        bats = por_dia.get(d, [])
        te = any(b.tipo == "entrada" for b in bats)
        ts = any(b.tipo == "saida" for b in bats)
        atrasado = _atrasado_entrada(atendente, _primeira_entrada_do_dia(bats))
        intervalos = _intervalos_de_batidas(bats)
        trabalhados = sum(i.duracao_segundos or 0 for i in intervalos if not i.aberto)
        esperado_visual = bool(esp and not feriado)
        if usa and esperado_visual:
            esperados = escala_svc.segundos_esperados_dia(atendente, d) or meta_default
        elif te or ts:
            esperados = meta_default
        elif esperado_visual:
            esperados = meta_default
        else:
            esperados = 0
        # Sem jornada esperada: dia com batidas compara à meta; dia vazio fica neutro
        esperado_para_cor = esperado_visual if usa else bool(te or ts)
        dias_out.append(
            PontoCalendarioDia(
                data=d,
                esperado=esperado_visual,
                tem_entrada=te,
                tem_saida=ts,
                status=_status_dia(  # type: ignore[arg-type]
                    usa_escala=usa,
                    esperado=esp,
                    tem_entrada=te,
                    tem_saida=ts,
                    feriado=feriado,
                    atrasado=atrasado,
                ),
                atrasado=atrasado,
                feriado=feriado,
                segundos_trabalhados=trabalhados,
                segundos_esperados=esperados,
                classe_visual=_classe_visual_dia(  # type: ignore[arg-type]
                    feriado=feriado,
                    esperado=esperado_para_cor,
                    segundos_trabalhados=trabalhados,
                    segundos_esperados=esperados,
                ),
            )
        )

    return PontoCalendarioRead(
        atendente_id=atendente.id,
        ano=ano,
        mes=mes,
        usa_escala=usa,
        escala_rotulo=escala_svc.rotulo_jornada(atendente) if usa else None,
        jornada_diaria_minutos=jornada_min,
        dias=dias_out,
    )


def visao_hoje(db: Session, admin: Atendente) -> PontoHojeRead:
    from app.services.presenca import PRESENCA_TTL_SEC

    hoje = datetime.now(PONTO_TZ).date()
    agora = _agora_utc()
    limite_online = agora - timedelta(seconds=PRESENCA_TTL_SEC)
    feriado_hoje = ponto_settings_svc.eh_feriado(db, admin.tenant_id, hoje)
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
        atrasado = _atrasado_entrada(a, _primeira_entrada_do_dia(bats))
        st = _status_dia(
            usa_escala=usa,
            esperado=esperado,
            tem_entrada=te,
            tem_saida=ts,
            feriado=feriado_hoje,
            atrasado=atrasado,
        )
        hb = a.presenca_heartbeat_em
        if hb is not None and hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        online = bool(hb and hb >= limite_online)
        online_sem = online and entrada is None
        itens.append(
            PontoHojeItem(
                atendente_id=a.id,
                nome=a.nome,
                esperado=esperado and not feriado_hoje,
                em_jornada=entrada is not None,
                em_pausa=em_pausa_aberta(db, a.id),
                entrada_em=entrada.registrado_em if entrada else None,
                status=st,  # type: ignore[arg-type]
                online=online,
                online_sem_ponto=online_sem,
                atrasado=atrasado,
                feriado=feriado_hoje,
            )
        )
    return PontoHojeRead(data=hoje, itens=itens)


def digest_hoje(db: Session, admin: Atendente) -> PontoDigestRead:
    from app.models.ponto_justificativa import PontoJustificativa
    from app.services import ponto_hora_extra as he_svc

    hoje = visao_hoje(db, admin)
    pendentes = (
        db.query(PontoJustificativa)
        .filter(
            PontoJustificativa.tenant_id == admin.tenant_id,
            PontoJustificativa.estado == "pendente",
        )
        .count()
    )
    faltas = sum(1 for i in hoje.itens if i.status == "falta")
    atrasos = sum(1 for i in hoje.itens if i.atrasado or i.status == "atraso")
    abertas = sum(1 for i in hoje.itens if i.em_jornada)
    online_sem = sum(1 for i in hoje.itens if i.online_sem_ponto)
    destaque = [
        i
        for i in hoje.itens
        if i.status in ("falta", "atraso", "parcial") or i.online_sem_ponto or i.em_jornada
    ]
    return PontoDigestRead(
        data=hoje.data,
        faltas=faltas,
        atrasos=atrasos,
        jornadas_abertas=abertas,
        online_sem_ponto=online_sem,
        justificativas_pendentes=pendentes,
        he_acima_teto_mensal=he_svc.contar_acima_teto_mensal(db, admin.tenant_id),
        itens=destaque[:40],
    )


def banco_horas(
    db: Session,
    atendente: Atendente,
    *,
    desde: date,
    ate: date,
) -> PontoBancoHorasRead:
    if ate < desde:
        raise HTTPException(status_code=400, detail="Período inválido (até < desde).")
    usa = escala_svc.escala_configurada(atendente)
    dias_escala = 0
    dias_feriado = 0
    esperado = 0
    d = desde
    while d <= ate:
        feriado = ponto_settings_svc.eh_feriado(db, atendente.tenant_id, d)
        if feriado:
            dias_feriado += 1
        elif usa and escala_svc.eh_dia_de_trabalho(atendente, d):
            dias_escala += 1
            esperado += escala_svc.segundos_esperados_dia(atendente, d)
        d += timedelta(days=1)

    hist = historico(db, atendente, desde=desde, ate=ate, offset=0, limit=10_000)
    realizado = hist.total_segundos_fechados
    # Sem escala: não gera débito — saldo = realizado (crédito puro)
    if not usa:
        esperado = 0
    return PontoBancoHorasRead(
        atendente_id=atendente.id,
        atendente_nome=atendente.nome,
        desde=desde,
        ate=ate,
        segundos_esperados=esperado,
        segundos_realizados=realizado,
        saldo_segundos=realizado - esperado,
        dias_escala=dias_escala,
        dias_feriado=dias_feriado,
    )


JORNADA_ALERTA_HORAS = 12.0


def alertas_me(db: Session, atendente: Atendente) -> "PontoAlertasMe":
    from app.schemas.ponto import PontoAlertasMe
    from app.services.presenca import PRESENCA_TTL_SEC

    exigir_acesso_ponto(atendente)
    hoje = datetime.now(PONTO_TZ).date()
    agora = _agora_utc()
    agora_local = agora.astimezone(PONTO_TZ)
    msgs: list[str] = []
    sem_entrada = False
    online_sem = False
    jornada_longa = False
    horas_aberta: float | None = None
    lembrete_entrada = False
    lembrete_saida = False

    feriado = ponto_settings_svc.eh_feriado(db, atendente.tenant_id, hoje)
    jornada_ativa = escala_svc.escala_configurada(atendente)
    esperado = None
    if jornada_ativa and not feriado:
        esperado = escala_svc.eh_dia_de_trabalho(atendente, hoje)

    entrada = _entrada_da_jornada_aberta(db, atendente.id)
    inicio, fim = _bounds_periodo(hoje, hoje)
    bats_hoje = (
        _q_ativas(db)
        .filter(
            PontoBatida.atendente_id == atendente.id,
            PontoBatida.registrado_em >= inicio,
            PontoBatida.registrado_em < fim,
        )
        .all()
    )
    tem_entrada_hoje = any(b.tipo == "entrada" for b in bats_hoje)
    primeira = _primeira_entrada_do_dia(bats_hoje)

    hb = atendente.presenca_heartbeat_em
    if hb is not None and hb.tzinfo is None:
        hb = hb.replace(tzinfo=timezone.utc)
    online = bool(hb and hb >= agora - timedelta(seconds=PRESENCA_TTL_SEC))

    # Modo nenhum: sem avisos de falta/atraso/lembretes de tolerância (#959 / #968)
    if jornada_ativa:
        if esperado is True and not tem_entrada_hoje and entrada is None:
            liberacao = escala_svc.liberacao_entrada_em(atendente, hoje)
            if liberacao is not None and agora_local >= liberacao:
                sem_entrada = True
                lembrete_entrada = True
                limite = escala_svc.limite_atraso_em(atendente, hoje)
                if limite is not None and agora_local <= limite:
                    msgs.append("Janela de entrada — registre o ponto agora.")
                else:
                    msgs.append(
                        "Hoje é dia de trabalho na sua jornada e ainda não há entrada registrada."
                    )

        if _atrasado_entrada(atendente, primeira):
            msgs.append("Entrada registrada após o horário previsto (fora da tolerância).")

    if online and entrada is None:
        online_sem = True
        if "ainda não há entrada" not in " ".join(msgs).lower() and "Janela de entrada" not in " ".join(
            msgs
        ):
            msgs.append("Você está online no painel sem jornada de ponto aberta.")

    if entrada is not None:
        horas_aberta = (_as_utc(agora) - _as_utc(entrada.registrado_em)).total_seconds() / 3600.0
        if horas_aberta >= JORNADA_ALERTA_HORAS:
            jornada_longa = True
            msgs.append(
                f"Jornada aberta há cerca de {horas_aberta:.0f} h — lembre-se de registrar a saída."
            )
        elif jornada_ativa:
            inicio_saida = escala_svc.liberacao_saida_lembrete_em(atendente, hoje)
            saida_prev = escala_svc.saida_prevista_em(atendente, hoje)
            if inicio_saida is not None and agora_local >= inicio_saida:
                lembrete_saida = True
                if saida_prev is not None and agora_local >= saida_prev:
                    msgs.append("Horário de saída previsto já passou — registre a saída.")
                else:
                    msgs.append("Janela de saída — registre o ponto ao encerrar.")

    return PontoAlertasMe(
        sem_entrada_em_dia_escala=sem_entrada,
        online_sem_ponto=online_sem,
        jornada_aberta_longa=jornada_longa,
        horas_jornada_aberta=horas_aberta,
        lembrete_entrada_tolerancia=lembrete_entrada,
        lembrete_saida_tolerancia=lembrete_saida,
        mensagens=msgs,
    )


def _semana_bounds(ref: date) -> tuple[date, date]:
    """Segunda a domingo da semana que contém `ref` (pt-BR / ISO weekday)."""
    desde = ref - timedelta(days=ref.weekday())
    return desde, desde + timedelta(days=6)


def _contar_atrasos_periodo(
    db: Session,
    atendente: Atendente,
    *,
    desde: date,
    ate: date,
) -> int:
    if not escala_svc.escala_configurada(atendente):
        return 0
    n = 0
    d = desde
    while d <= ate:
        if ponto_settings_svc.eh_feriado(db, atendente.tenant_id, d):
            d += timedelta(days=1)
            continue
        if not escala_svc.eh_dia_de_trabalho(atendente, d):
            d += timedelta(days=1)
            continue
        ini, fim = _bounds_periodo(d, d)
        bats = (
            _q_ativas(db)
            .filter(
                PontoBatida.atendente_id == atendente.id,
                PontoBatida.registrado_em >= ini,
                PontoBatida.registrado_em < fim,
            )
            .all()
        )
        if _atrasado_entrada(atendente, _primeira_entrada_do_dia(bats)):
            n += 1
        d += timedelta(days=1)
    return n


def _he_minutos_periodo(db: Session, atendente: Atendente, *, desde: date, ate: date) -> int:
    from app.models.ponto_hora_extra import PontoHoraExtra

    ini, fim = _bounds_periodo(desde, ate)
    rows = (
        db.query(PontoHoraExtra)
        .filter(
            PontoHoraExtra.atendente_id == atendente.id,
            PontoHoraExtra.estado.in_(("aprovada", "expirada")),
            PontoHoraExtra.ate_em.isnot(None),
            PontoHoraExtra.decidido_em.isnot(None),
            PontoHoraExtra.decidido_em >= ini,
            PontoHoraExtra.decidido_em < fim,
        )
        .all()
    )
    total = 0
    for r in rows:
        dec = r.decidido_em
        ate_em = r.ate_em
        if dec is None or ate_em is None:
            continue
        if dec.tzinfo is None:
            dec = dec.replace(tzinfo=timezone.utc)
        if ate_em.tzinfo is None:
            ate_em = ate_em.replace(tzinfo=timezone.utc)
        total += max(0, int((ate_em - dec).total_seconds() // 60))
    return total


def resumo_semana(
    db: Session,
    atendente: Atendente,
    *,
    ref: date | None = None,
) -> "PontoResumoSemanaRead":
    from app.schemas.ponto import PontoResumoSemanaRead

    exigir_acesso_ponto(atendente)
    dia_ref = ref or datetime.now(PONTO_TZ).date()
    desde, ate = _semana_bounds(dia_ref)
    bh = banco_horas(db, atendente, desde=desde, ate=ate)
    return PontoResumoSemanaRead(
        desde=desde,
        ate=ate,
        segundos_esperados=bh.segundos_esperados,
        segundos_realizados=bh.segundos_realizados,
        saldo_segundos=bh.saldo_segundos,
        atrasos=_contar_atrasos_periodo(db, atendente, desde=desde, ate=ate),
        he_minutos=_he_minutos_periodo(db, atendente, desde=desde, ate=ate),
        dias_escala=bh.dias_escala,
        dias_feriado=bh.dias_feriado,
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
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 3:
        raise HTTPException(
            status_code=400,
            detail="Informe o motivo do ajuste (mínimo 3 caracteres).",
        )
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
            "motivo": motivo_limpo,
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
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 3:
        raise HTTPException(
            status_code=400,
            detail="Informe o motivo do ajuste (mínimo 3 caracteres).",
        )
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
        payload={
            "motivo": motivo_limpo,
            "antes": antes,
            "depois": {"tipo": batida.tipo, "registrado_em": batida.registrado_em.isoformat()},
        },
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
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 3:
        raise HTTPException(
            status_code=400,
            detail="Informe o motivo da anulação (mínimo 3 caracteres).",
        )
    batida.anulada = True
    registrar_audit(
        db,
        "ponto_batida",
        batida.id,
        "anular",
        admin.id,
        payload={
            "motivo": motivo_limpo,
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
    writer.writerow(
        [
            "atendente",
            "tipo",
            "registrado_em",
            "origem",
            "latitude",
            "longitude",
            "accuracy_metros",
            "fora_area",
            "distancia_metros",
        ]
    )
    for aid, bats in por_atendente.items():
        for b in bats:
            writer.writerow(
                [
                    nomes.get(aid, str(aid)),
                    b.tipo,
                    _as_utc(b.registrado_em).astimezone(PONTO_TZ).strftime("%Y-%m-%d %H:%M"),
                    b.origem or "",
                    b.latitude if b.latitude is not None else "",
                    b.longitude if b.longitude is not None else "",
                    b.accuracy_metros if b.accuracy_metros is not None else "",
                    "sim" if getattr(b, "fora_area", False) else "nao",
                    getattr(b, "distancia_metros", None) if getattr(b, "distancia_metros", None) is not None else "",
                ]
            )
    return buf.getvalue()
