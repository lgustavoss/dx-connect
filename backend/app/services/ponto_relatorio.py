"""Relatório mensal de ponto — PDF e Excel (#844 / #971).

Espelho alinhado ao uso contábil / Portaria MTP 671 (espelho eletrônico):
identificação, período, marcações e duração das jornadas. Feriados e folgas
(DSR / fim de semana) aparecem no calendário do período; ajustes admin ficam
fora deste relatório de fechamento.
"""

from __future__ import annotations

import io
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import escape

from sqlalchemy.orm import Session, joinedload

from app.core.business_calendar import easter_date_gregorian, is_feriado_nacional_br
from app.models.atendente import Atendente
from app.models.audit_log import AuditLog
from app.models.ponto_batida import PontoBatida
from app.schemas.ponto import PontoIntervaloRead
from app.services import escala as escala_svc
from app.services import ponto_ausencia as ausencia_svc
from app.services import ponto_settings as ponto_settings_svc
from app.services.comercial_proposta import _logo_html, html_para_pdf
from app.services import ponto as ponto_svc
from app.services.ponto import PONTO_TZ, _as_utc, _bounds_periodo, _intervalos_de_batidas, _q_ativas

MESES_PT = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

DIAS_SEMANA_PT = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


def _rotulo_acao_ajuste(action: str) -> str:
    return {
        "create_ajuste": "Criação",
        "update_ajuste": "Alteração",
        "anular": "Anulação",
    }.get(action, action)


def _coletar_ajustes_audit(
    db: Session,
    admin: Atendente,
    *,
    desde: date | None,
    ate: date | None,
) -> list[AuditLog]:
    """Usado pela exportação de folha RH (não entra no espelho PDF/Excel de fechamento)."""
    q = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.atendente))
        .filter(
            AuditLog.entity_type == "ponto_batida",
            AuditLog.action.in_(("create_ajuste", "update_ajuste", "anular")),
        )
    )
    ids = [
        row[0]
        for row in db.query(Atendente.id).filter(Atendente.tenant_id == admin.tenant_id).all()
    ]
    if ids:
        q = q.filter(AuditLog.atendente_id.in_(ids))
    inicio, fim = _bounds_periodo(desde, ate)
    if inicio is not None:
        q = q.filter(AuditLog.created_at >= inicio)
    if fim is not None:
        q = q.filter(AuditLog.created_at < fim)
    return q.order_by(AuditLog.created_at.asc(), AuditLog.id.asc()).limit(2000).all()


@dataclass(frozen=True)
class DiaRelatorio:
    nome: str
    data: date
    entrada_em: datetime | None
    saida_em: datetime | None
    segundos_trabalhados: int
    segundos_pausa: int
    aberto: bool
    ocorrencia: str
    destaque: str  # normal | folga | feriado | falta | ausencia | trabalho_especial


def _fmt_hora(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return _as_utc(dt).astimezone(PONTO_TZ).strftime("%H:%M")


def _fmt_duracao(segundos: int | None, *, vazio: bool = False) -> str:
    if vazio or segundos is None:
        return "—"
    s = max(0, int(segundos))
    if s == 0:
        return "—"
    h, rem = divmod(s, 3600)
    m = rem // 60
    if h <= 0:
        return f"{m} min"
    return f"{h}h{m:02d}"


def nome_feriado_br(dia: date) -> str | None:
    """Nome amigável de feriado nacional (fixos + móveis)."""
    fixos = {
        (1, 1): "Confraternização Universal",
        (4, 21): "Tiradentes",
        (5, 1): "Dia do Trabalho",
        (9, 7): "Independência do Brasil",
        (10, 12): "Nossa Senhora Aparecida",
        (11, 2): "Finados",
        (11, 15): "Proclamação da República",
        (11, 20): "Consciência Negra",
        (12, 25): "Natal",
    }
    if (dia.month, dia.day) in fixos:
        return fixos[(dia.month, dia.day)]
    easter = easter_date_gregorian(dia.year)
    moveis = {
        easter - timedelta(days=48): "Carnaval",
        easter - timedelta(days=47): "Carnaval",
        easter - timedelta(days=2): "Sexta-feira Santa",
        easter + timedelta(days=60): "Corpus Christi",
    }
    return moveis.get(dia)


def nome_feriado(db: Session, tenant_id: int, dia: date) -> str | None:
    custom = ponto_settings_svc.feriado_custom_no_dia(db, tenant_id, dia)
    if custom:
        return custom.nome
    settings = ponto_settings_svc.get_or_create_settings(db, tenant_id)
    if settings.usar_feriados_nacionais and is_feriado_nacional_br(dia):
        return nome_feriado_br(dia) or "Feriado nacional"
    return None


def _iter_dias(desde: date, ate: date):
    cur = desde
    while cur <= ate:
        yield cur
        cur += timedelta(days=1)


def _esperado_trabalho(atendente: Atendente, dia: date) -> bool:
    if escala_svc.escala_configurada(atendente):
        return escala_svc.eh_dia_de_trabalho(atendente, dia)
    # Sem escala: espelho contábil considera segunda a sexta
    return dia.weekday() < 5


def _rotulo_folga(dia: date, *, com_ponto: bool) -> str:
    wd = dia.weekday()
    if wd == 5:
        base = "Folga (sábado)"
    elif wd == 6:
        base = "Folga (domingo)"
    else:
        base = "Folga"
    return f"{base} — com ponto" if com_ponto else base


def _rotulo_ausencia(tipo: str | None) -> str:
    if tipo == "ferias":
        return "Férias"
    if tipo == "folga_programada":
        return "Folga programada"
    if tipo == "abono":
        return "Folga (banco)"
    return "Ausência"


def agregar_dias(linhas: list[tuple[str, PontoIntervaloRead]]) -> list[DiaRelatorio]:
    """Agrega intervalos do mesmo dia (pausas explícitas + intervalo entre turnos)."""
    grupos: OrderedDict[tuple[str, date], list[PontoIntervaloRead]] = OrderedDict()
    for nome, it in linhas:
        grupos.setdefault((nome, it.data), []).append(it)

    dias: list[DiaRelatorio] = []
    for (nome, data), its in grupos.items():
        its_sorted = sorted(its, key=lambda x: (_as_utc(x.entrada_em), x.entrada_batida_id or 0))
        entrada = its_sorted[0].entrada_em
        aberto = any(i.aberto for i in its_sorted)
        saidas_fechadas = [i.saida_em for i in its_sorted if i.saida_em is not None and not i.aberto]
        if aberto:
            saida = saidas_fechadas[-1] if saidas_fechadas else None
        else:
            saida = its_sorted[-1].saida_em

        trab = sum(i.duracao_segundos or 0 for i in its_sorted if not i.aberto)
        pausa = sum(i.segundos_pausa or 0 for i in its_sorted)
        for ant, prox in zip(its_sorted, its_sorted[1:]):
            if ant.saida_em is None:
                continue
            gap = int((_as_utc(prox.entrada_em) - _as_utc(ant.saida_em)).total_seconds())
            if gap > 0:
                pausa += gap

        dias.append(
            DiaRelatorio(
                nome=nome,
                data=data,
                entrada_em=entrada,
                saida_em=saida,
                segundos_trabalhados=trab,
                segundos_pausa=pausa,
                aberto=aberto,
                ocorrencia="Normal",
                destaque="normal",
            )
        )
    return dias


def _coletar_intervalos_atendente(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int,
    desde: date | None,
    ate: date | None,
) -> list[PontoIntervaloRead]:
    q = _q_ativas(db).filter(
        PontoBatida.tenant_id == admin.tenant_id,
        PontoBatida.atendente_id == atendente_id,
    )
    inicio, fim = _bounds_periodo(desde, ate)
    if inicio is not None:
        q = q.filter(PontoBatida.registrado_em >= inicio)
    if fim is not None:
        q = q.filter(PontoBatida.registrado_em < fim)
    batidas = q.order_by(PontoBatida.registrado_em.asc()).all()
    return _intervalos_de_batidas(batidas)


def montar_espelho_colaborador(
    db: Session,
    admin: Atendente,
    atendente: Atendente,
    *,
    desde: date,
    ate: date,
) -> list[DiaRelatorio]:
    """Calendário completo do período: marcações + feriado/folga/falta (espelho contábil)."""
    intervalos = _coletar_intervalos_atendente(
        db, admin, atendente_id=atendente.id, desde=desde, ate=ate
    )
    agregados = {
        d.data: d
        for d in agregar_dias([(atendente.nome, it) for it in intervalos])
    }
    ausencias = ausencia_svc.mapa_ausencias_aprovadas(db, atendente.id, desde=desde, ate=ate)
    hoje = datetime.now(timezone.utc).astimezone(PONTO_TZ).date()

    out: list[DiaRelatorio] = []
    for dia in _iter_dias(desde, ate):
        base = agregados.get(dia)
        tem_ponto = base is not None and (
            base.segundos_trabalhados > 0 or base.entrada_em is not None
        )
        fer_nome = nome_feriado(db, admin.tenant_id, dia)
        eh_fer = fer_nome is not None
        aus_tipo = ausencias.get(dia)
        esperado = _esperado_trabalho(atendente, dia) and not eh_fer and not aus_tipo

        if eh_fer:
            ocorrencia = f"Feriado — {fer_nome}"
            if tem_ponto:
                ocorrencia += " (com ponto)"
            destaque = "trabalho_especial" if tem_ponto else "feriado"
        elif aus_tipo:
            ocorrencia = _rotulo_ausencia(aus_tipo)
            if tem_ponto:
                ocorrencia += " (com ponto)"
            destaque = "ausencia"
        elif not esperado:
            ocorrencia = _rotulo_folga(dia, com_ponto=bool(tem_ponto))
            destaque = "trabalho_especial" if tem_ponto else "folga"
        elif tem_ponto:
            ocorrencia = "Normal"
            destaque = "normal"
        elif dia > hoje:
            ocorrencia = "—"
            destaque = "normal"
        else:
            ocorrencia = "Falta"
            destaque = "falta"

        if base:
            out.append(
                DiaRelatorio(
                    nome=atendente.nome,
                    data=dia,
                    entrada_em=base.entrada_em,
                    saida_em=base.saida_em,
                    segundos_trabalhados=base.segundos_trabalhados,
                    segundos_pausa=base.segundos_pausa,
                    aberto=base.aberto,
                    ocorrencia=ocorrencia,
                    destaque=destaque,
                )
            )
        else:
            out.append(
                DiaRelatorio(
                    nome=atendente.nome,
                    data=dia,
                    entrada_em=None,
                    saida_em=None,
                    segundos_trabalhados=0,
                    segundos_pausa=0,
                    aberto=False,
                    ocorrencia=ocorrencia,
                    destaque=destaque,
                )
            )
    return out


def _listar_alvos(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
) -> list[Atendente]:
    q = db.query(Atendente).filter(
        Atendente.tenant_id == admin.tenant_id,
        Atendente.ativo.is_(True),
    )
    if atendente_id is not None:
        q = q.filter(Atendente.id == atendente_id)
    return q.order_by(Atendente.nome.asc()).all()


def _titulo_periodo(desde: date | None, ate: date | None) -> str:
    if desde and ate and desde.year == ate.year and desde.month == ate.month and desde.day == 1:
        ultimo = (
            date(desde.year, desde.month % 12 + 1, 1)
            if desde.month < 12
            else date(desde.year + 1, 1, 1)
        )
        fim_mes = ultimo - timedelta(days=1)
        if ate >= fim_mes:
            return f"{MESES_PT[desde.month]} / {desde.year}"
    d1 = desde.isoformat() if desde else "—"
    d2 = ate.isoformat() if ate else "—"
    return f"{d1} a {d2}"


def _periodo_obrigatorio(desde: date | None, ate: date | None) -> tuple[date, date]:
    if desde is None or ate is None:
        hoje = datetime.now(timezone.utc).astimezone(PONTO_TZ).date()
        inicio = date(hoje.year, hoje.month, 1)
        if hoje.month == 12:
            fim = date(hoje.year, 12, 31)
        else:
            fim = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
        return (desde or inicio, ate or fim)
    return desde, ate


def _montar_todos(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date | None,
    ate: date | None,
) -> list[DiaRelatorio]:
    d0, d1 = _periodo_obrigatorio(desde, ate)
    dias: list[DiaRelatorio] = []
    for alvo in _listar_alvos(db, admin, atendente_id=atendente_id):
        dias.extend(montar_espelho_colaborador(db, admin, alvo, desde=d0, ate=d1))
    return dias


def _css_destaque(destaque: str) -> str:
    return {
        "feriado": "row-feriado",
        "folga": "row-folga",
        "falta": "row-falta",
        "ausencia": "row-ausencia",
        "trabalho_especial": "row-especial",
    }.get(destaque, "")


def _resumo_banco_html(
    db: Session,
    atendente: Atendente,
    *,
    desde: date,
    ate: date,
    dias: list[DiaRelatorio],
) -> str:
    """Bloco de fechamento: saldo inicial, créditos, débitos e faltas (p/ folha)."""
    bh = ponto_svc.banco_horas(db, atendente, desde=desde, ate=ate)
    ate_prev = desde - timedelta(days=1)
    saldo_inicial = ponto_svc.saldo_banco_ate(db, atendente, ate=ate_prev)
    credito = int(getattr(bh, "segundos_credito_banco", 0) or 0)
    debito = int(getattr(bh, "segundos_debito_banco", 0) or 0)
    saldo_final = saldo_inicial + bh.saldo_segundos
    faltas = sum(1 for d in dias if d.destaque == "falta")
    he_pagos = int(getattr(bh, "segundos_he_pagos", 0) or 0)

    def _s(seg: int, *, sinal: bool = False) -> str:
        if sinal and seg != 0:
            pref = "+" if seg > 0 else "−"
            return f"{pref}{_fmt_duracao(abs(seg))}"
        return _fmt_duracao(seg) if seg else "0"

    he_linha = (
        f"<tr><th>HE a pagar (config.)</th><td>{_fmt_duracao(he_pagos)}</td></tr>"
        if he_pagos > 0
        else ""
    )
    return f"""<table class="resumo-banco">
  <caption>Banco de horas e faltas (fechamento)</caption>
  <tbody>
    <tr><th>Saldo inicial</th><td>{_s(saldo_inicial, sinal=True)}</td></tr>
    <tr><th>Crédito no mês</th><td>{('+' + _fmt_duracao(credito)) if credito else '0'}</td></tr>
    <tr><th>Débito no mês</th><td>{('−' + _fmt_duracao(debito)) if debito else '0'}</td></tr>
    <tr><th>Saldo do mês (líquido)</th><td>{_s(bh.saldo_segundos, sinal=True)}</td></tr>
    <tr><th>Saldo final</th><td>{_s(saldo_final, sinal=True)}</td></tr>
    <tr><th>Faltas (p/ desconto em folha)</th><td>{faltas} dia(s)</td></tr>
    {he_linha}
  </tbody>
</table>
<p class="nota">Faltas não abonadas não debitam o banco — ficam para tratamento salarial.
Déficit parcial e folga (banco) já entram no débito acima. Saldo negativo entre meses
só gera desconto em folha se houver previsão em acordo ou convenção coletiva.</p>"""


def _linha_html(d: DiaRelatorio, *, com_nome: bool) -> str:
    sem_marcacao = d.entrada_em is None and not d.aberto
    cells = ""
    if com_nome:
        cells += f"<td>{escape(d.nome)}</td>"
    cells += (
        f"<td>{d.data.strftime('%d/%m/%Y')}</td>"
        f"<td>{DIAS_SEMANA_PT[d.data.weekday()]}</td>"
        f"<td>{escape(d.ocorrencia)}</td>"
        f"<td>{_fmt_hora(d.entrada_em)}</td>"
        f"<td>{_fmt_hora(d.saida_em)}</td>"
        f"<td>{_fmt_duracao(d.segundos_pausa, vazio=sem_marcacao and d.segundos_pausa == 0)}</td>"
        f"<td>{_fmt_duracao(d.segundos_trabalhados, vazio=sem_marcacao and not d.aberto)}</td>"
    )
    cls = _css_destaque(d.destaque)
    return f'<tr class="{cls}">{cells}</tr>'


def export_pdf_mensal(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date | None,
    ate: date | None,
) -> bytes:
    dias = _montar_todos(db, admin, atendente_id=atendente_id, desde=desde, ate=ate)
    titulo = _titulo_periodo(desde, ate)
    gerado = datetime.now(timezone.utc).astimezone(PONTO_TZ).strftime("%d/%m/%Y %H:%M")
    from app.services import ponto_competencia as comp_svc

    selo_comp = ""
    if desde and desde.year and desde.month:
        if comp_svc.competencia_fechada(db, admin.tenant_id, ano=desde.year, mes=desde.month):
            selo_comp = " · Competência FECHADA"

    colaborador: str | None = None
    if atendente_id is not None:
        alvo = db.query(Atendente).filter(Atendente.id == atendente_id).first()
        colaborador = alvo.nome if alvo else f"#{atendente_id}"
    else:
        nomes = {d.nome for d in dias}
        if len(nomes) == 1:
            colaborador = next(iter(nomes))

    total_seg = sum(d.segundos_trabalhados for d in dias if not d.aberto)
    total_pausa = sum(d.segundos_pausa for d in dias if d.entrada_em is not None)

    d0, d1 = _periodo_obrigatorio(desde, ate)
    alvos = _listar_alvos(db, admin, atendente_id=atendente_id)
    alvos_por_nome = {a.nome: a for a in alvos}
    alvos_por_id = {a.id: a for a in alvos}

    if colaborador:
        sections: list[tuple[str | None, list[DiaRelatorio]]] = [(None, dias)]
        com_nome = False
    else:
        por_nome: OrderedDict[str, list[DiaRelatorio]] = OrderedDict()
        for d in dias:
            por_nome.setdefault(d.nome, []).append(d)
        sections = [(nome, rows) for nome, rows in por_nome.items()]
        com_nome = False

    body_parts: list[str] = []
    for secao_nome, rows in sections:
        if secao_nome:
            body_parts.append(f"<h2>{escape(secao_nome)}</h2>")
        rows_html = "".join(_linha_html(d, com_nome=com_nome) for d in rows)
        body_parts.append(
            f"""<table class="espelho">
    <thead><tr>
      <th>Data</th><th>Dia</th><th>Ocorrência</th><th>Entrada</th><th>Saída</th>
      <th>Pausa</th><th>Trabalhado</th>
    </tr></thead>
    <tbody>{rows_html or '<tr><td colspan="7">Sem registros no período.</td></tr>'}</tbody>
  </table>"""
        )
        alvo_resumo: Atendente | None = None
        if secao_nome and secao_nome in alvos_por_nome:
            alvo_resumo = alvos_por_nome[secao_nome]
        elif atendente_id is not None:
            alvo_resumo = alvos_por_id.get(atendente_id)
        elif colaborador and colaborador in alvos_por_nome:
            alvo_resumo = alvos_por_nome[colaborador]
        if alvo_resumo is not None:
            body_parts.append(
                _resumo_banco_html(db, alvo_resumo, desde=d0, ate=d1, dias=rows)
            )

    linha_colab = (
        f'<p class="colaborador">Colaborador: {escape(colaborador)}</p>'
        if colaborador
        else ""
    )
    logo_html = _logo_html(db)
    logo_cell = logo_html if logo_html else "&nbsp;"
    selo_html = (
        f'<p class="selo">{escape(selo_comp.lstrip(" · "))}</p>' if selo_comp else ""
    )
    rodape = f"Gerado em {gerado} · DeskRudder"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Espelho de ponto</title>
<style>
  @page {{
    size: A4;
    margin: 14mm 12mm 16mm 12mm;
    @bottom-center {{
      content: "{rodape}";
      font-size: 8pt;
      color: #64748b;
    }}
  }}
  body {{ font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 10px; color: #0f172a; }}
  table.cabecalho {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1.5px solid #e2e8f0;
  }}
  table.cabecalho td {{
    border: none;
    vertical-align: middle;
    padding: 0;
  }}
  table.cabecalho td.logo {{
    width: 210px;
    padding-right: 18px;
    text-align: left;
  }}
  table.cabecalho td.logo img {{
    max-height: 110px;
    max-width: 220px;
    height: auto;
    width: auto;
  }}
  table.cabecalho td.titulos {{
    text-align: left;
  }}
  table.cabecalho h1 {{
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #0f172a;
    margin: 0 0 4px;
    line-height: 1.15;
  }}
  table.cabecalho .competencia {{
    font-size: 15px;
    font-weight: 600;
    color: #334155;
    margin: 0;
    line-height: 1.3;
  }}
  table.cabecalho .colaborador {{
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
    margin: 8px 0 0;
  }}
  table.cabecalho .selo {{
    font-size: 10px;
    font-weight: 600;
    color: #b45309;
    margin: 4px 0 0;
  }}
  h2 {{ font-size: 12px; margin: 14px 0 6px; }}
  table.espelho {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  table.espelho th, table.espelho td {{ border: 1px solid #ccc; padding: 3px 5px; text-align: left; }}
  table.espelho th {{ background: #f0f0f0; }}
  .row-feriado {{ background: #fff7ed; }}
  .row-folga {{ background: #f8fafc; color: #475569; }}
  .row-falta {{ background: #fef2f2; }}
  .row-ausencia {{ background: #f5f3ff; }}
  .row-especial {{ background: #ecfeff; }}
  .total {{ margin-top: 10px; font-weight: bold; }}
  .nota {{ color: #64748b; font-size: 9px; margin-top: 8px; }}
  table.resumo-banco {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 4px;
    font-size: 10px;
  }}
  table.resumo-banco caption {{
    text-align: left;
    font-weight: 700;
    font-size: 11px;
    margin-bottom: 4px;
    color: #0f172a;
  }}
  table.resumo-banco th, table.resumo-banco td {{
    border: 1px solid #cbd5e1;
    padding: 4px 6px;
    text-align: left;
  }}
  table.resumo-banco th {{ width: 55%; background: #f8fafc; font-weight: 600; }}
</style>
</head>
<body>
  <table class="cabecalho">
    <tr>
      <td class="logo">{logo_cell}</td>
      <td class="titulos">
        <h1>Espelho de ponto</h1>
        <p class="competencia">{escape(titulo)}</p>
        {linha_colab}
        {selo_html}
      </td>
    </tr>
  </table>
  {"".join(body_parts) if body_parts else "<p>Sem registros no período.</p>"}
  <p class="total">Total trabalhado: {_fmt_duracao(total_seg)} · Total em pausa: {_fmt_duracao(total_pausa)}</p>
  <p class="nota">Folgas de sábado/domingo e feriados constam para conferência da jornada e do DSR.
  Trabalho nesses dias aparece como «com ponto». Relatório destinado ao fechamento / contabilidade
  (espelho eletrônico — Portaria MTP 671). O bloco de banco/faltas é informativo para RH;
  não substitui acordo coletivo nem holerite.</p>
</body>
</html>"""
    return html_para_pdf(html)


def export_xlsx_mensal(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date | None,
    ate: date | None,
) -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Exportação Excel indisponível (openpyxl não instalado).",
        ) from exc

    dias = _montar_todos(db, admin, atendente_id=atendente_id, desde=desde, ate=ate)
    from app.services import ponto_competencia as comp_svc

    d0, d1 = _periodo_obrigatorio(desde, ate)
    alvos = _listar_alvos(db, admin, atendente_id=atendente_id)
    alvos_por_nome = {a.nome: a for a in alvos}

    colaborador: str | None = None
    if atendente_id is not None:
        alvo = db.query(Atendente).filter(Atendente.id == atendente_id).first()
        colaborador = alvo.nome if alvo else f"#{atendente_id}"
    else:
        nomes = {d.nome for d in dias}
        if len(nomes) == 1:
            colaborador = next(iter(nomes))

    wb = Workbook()
    ws = wb.active
    ws.title = "Espelho"
    if desde and comp_svc.competencia_fechada(db, admin.tenant_id, ano=desde.year, mes=desde.month):
        ws.append([f"Competência FECHADA — {_titulo_periodo(desde, ate)}"])
    if colaborador:
        ws.append([f"Colaborador: {colaborador}"])
    if ws.max_row >= 1 and ws.cell(1, 1).value:
        ws.append([])

    inclui_nome = colaborador is None
    cabecalho = ["Data", "Dia", "Ocorrência", "Entrada", "Saída", "Pausa", "Trabalhado"]
    if inclui_nome:
        cabecalho = ["Atendente", *cabecalho]
    ws.append(cabecalho)

    total_seg = 0
    total_pausa = 0
    por_nome: OrderedDict[str, list[DiaRelatorio]] = OrderedDict()
    for d in dias:
        if not d.aberto:
            total_seg += d.segundos_trabalhados
        if d.entrada_em is not None:
            total_pausa += d.segundos_pausa
        sem_marcacao = d.entrada_em is None and not d.aberto
        row = [
            d.data.isoformat(),
            DIAS_SEMANA_PT[d.data.weekday()],
            d.ocorrencia,
            _fmt_hora(d.entrada_em),
            _fmt_hora(d.saida_em),
            _fmt_duracao(d.segundos_pausa, vazio=sem_marcacao and d.segundos_pausa == 0),
            _fmt_duracao(d.segundos_trabalhados, vazio=sem_marcacao and not d.aberto),
        ]
        if inclui_nome:
            row = [d.nome, *row]
        ws.append(row)
        por_nome.setdefault(d.nome, []).append(d)

    ws.append([])
    ws.append(["Total trabalhado", _fmt_duracao(total_seg)])
    ws.append(["Total em pausa", _fmt_duracao(total_pausa)])

    def _append_resumo(nome: str, rows: list[DiaRelatorio]) -> None:
        alvo = alvos_por_nome.get(nome)
        if alvo is None and atendente_id is not None and len(alvos) == 1:
            alvo = alvos[0]
        if alvo is None:
            return
        bh = ponto_svc.banco_horas(db, alvo, desde=d0, ate=d1)
        saldo_inicial = ponto_svc.saldo_banco_ate(db, alvo, ate=d0 - timedelta(days=1))
        credito = int(getattr(bh, "segundos_credito_banco", 0) or 0)
        debito = int(getattr(bh, "segundos_debito_banco", 0) or 0)
        faltas = sum(1 for x in rows if x.destaque == "falta")
        ws.append([])
        if inclui_nome:
            ws.append([f"Banco / faltas — {nome}"])
        else:
            ws.append(["Banco de horas e faltas (fechamento)"])
        ws.append(["Saldo inicial", _fmt_duracao(abs(saldo_inicial)) if saldo_inicial else "0",
                   "+" if saldo_inicial > 0 else ("−" if saldo_inicial < 0 else "")])
        ws.append(["Crédito no mês", _fmt_duracao(credito) if credito else "0"])
        ws.append(["Débito no mês", _fmt_duracao(debito) if debito else "0"])
        ws.append(["Saldo do mês (líquido)", _fmt_duracao(abs(bh.saldo_segundos)) if bh.saldo_segundos else "0",
                   "+" if bh.saldo_segundos > 0 else ("−" if bh.saldo_segundos < 0 else "")])
        saldo_final = saldo_inicial + bh.saldo_segundos
        ws.append(["Saldo final", _fmt_duracao(abs(saldo_final)) if saldo_final else "0",
                   "+" if saldo_final > 0 else ("−" if saldo_final < 0 else "")])
        ws.append(["Faltas (p/ desconto em folha)", faltas])

    if colaborador and len(por_nome) == 1:
        nome0, rows0 = next(iter(por_nome.items()))
        _append_resumo(nome0, rows0)
    else:
        for nome, rows in por_nome.items():
            _append_resumo(nome, rows)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
