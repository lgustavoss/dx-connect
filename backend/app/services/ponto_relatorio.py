"""Relatório mensal de ponto — PDF e Excel (#844)."""

from __future__ import annotations

import io
from datetime import date, datetime, timezone
from html import escape

from sqlalchemy.orm import Session

from app.models.atendente import Atendente
from app.models.ponto_batida import PontoBatida
from app.services.comercial_proposta import html_para_pdf
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


def _coletar_intervalos(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date | None,
    ate: date | None,
) -> list[tuple[str, object]]:
    q = _q_ativas(db).filter(PontoBatida.tenant_id == admin.tenant_id)
    if atendente_id is not None:
        q = q.filter(PontoBatida.atendente_id == atendente_id)
    inicio, fim = _bounds_periodo(desde, ate)
    if inicio is not None:
        q = q.filter(PontoBatida.registrado_em >= inicio)
    if fim is not None:
        q = q.filter(PontoBatida.registrado_em < fim)
    batidas = q.order_by(PontoBatida.atendente_id.asc(), PontoBatida.registrado_em.asc()).all()
    nomes = {
        a.id: a.nome
        for a in db.query(Atendente).filter(Atendente.tenant_id == admin.tenant_id).all()
    }
    por_atendente: dict[int, list[PontoBatida]] = {}
    for b in batidas:
        por_atendente.setdefault(b.atendente_id, []).append(b)
    linhas: list[tuple[str, object]] = []
    for aid in sorted(por_atendente.keys(), key=lambda x: (nomes.get(x, "").lower(), x)):
        for it in _intervalos_de_batidas(por_atendente[aid]):
            linhas.append((nomes.get(aid, str(aid)), it))
    return linhas


def _titulo_periodo(desde: date | None, ate: date | None) -> str:
    if desde and ate and desde.year == ate.year and desde.month == ate.month and desde.day == 1:
        ultimo = (date(desde.year, desde.month % 12 + 1, 1) if desde.month < 12 else date(desde.year + 1, 1, 1))
        from datetime import timedelta

        fim_mes = ultimo - timedelta(days=1)
        if ate >= fim_mes:
            return f"{MESES_PT[desde.month]} / {desde.year}"
    d1 = desde.isoformat() if desde else "—"
    d2 = ate.isoformat() if ate else "—"
    return f"{d1} a {d2}"


def export_pdf_mensal(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date | None,
    ate: date | None,
) -> bytes:
    linhas = _coletar_intervalos(db, admin, atendente_id=atendente_id, desde=desde, ate=ate)
    titulo = _titulo_periodo(desde, ate)
    gerado = datetime.now(timezone.utc).astimezone(PONTO_TZ).strftime("%d/%m/%Y %H:%M")

    rows_html = ""
    total_min = 0.0
    for nome, it in linhas:
        trab = (it.duracao_segundos or 0) / 60 if it.duracao_segundos is not None else 0
        if not it.aberto:
            total_min += trab
        entrada = _as_utc(it.entrada_em).astimezone(PONTO_TZ).strftime("%d/%m/%Y %H:%M")
        saida = (
            _as_utc(it.saida_em).astimezone(PONTO_TZ).strftime("%d/%m/%Y %H:%M") if it.saida_em else "—"
        )
        rows_html += (
            "<tr>"
            f"<td>{escape(nome)}</td>"
            f"<td>{it.data.strftime('%d/%m/%Y')}</td>"
            f"<td>{entrada}</td>"
            f"<td>{saida}</td>"
            f"<td>{round((it.segundos_pausa or 0) / 60, 1)}</td>"
            f"<td>{round(trab, 1) if not it.aberto else '—'}</td>"
            f"<td>{'sim' if it.aberto else 'não'}</td>"
            "</tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Relatório de ponto</title>
<style>
  body {{ font-family: sans-serif; font-size: 11px; color: #111; }}
  h1 {{ font-size: 18px; margin-bottom: 4px; }}
  .meta {{ color: #555; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ border: 1px solid #ccc; padding: 4px 6px; text-align: left; }}
  th {{ background: #f0f0f0; }}
  .total {{ margin-top: 12px; font-weight: bold; }}
</style>
</head>
<body>
  <h1>Relatório de ponto — {escape(titulo)}</h1>
  <p class="meta">Gerado em {gerado} · DeskRudder</p>
  <table>
    <thead><tr>
      <th>Atendente</th><th>Data</th><th>Entrada</th><th>Saída</th>
      <th>Pausas (min)</th><th>Trabalhado (min)</th><th>Aberto</th>
    </tr></thead>
    <tbody>{rows_html or '<tr><td colspan="7">Sem registos no período.</td></tr>'}</tbody>
  </table>
  <p class="total">Total trabalhado (fechado): {round(total_min / 60, 2)} h ({round(total_min, 0)} min)</p>
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

    linhas = _coletar_intervalos(db, admin, atendente_id=atendente_id, desde=desde, ate=ate)
    wb = Workbook()
    ws = wb.active
    ws.title = "Ponto"
    ws.append(
        ["Atendente", "Data", "Entrada", "Saída", "Pausas (min)", "Trabalhado (min)", "Aberto"]
    )
    total_min = 0.0
    for nome, it in linhas:
        trab = (it.duracao_segundos or 0) / 60 if it.duracao_segundos is not None else None
        if trab is not None and not it.aberto:
            total_min += trab
        ws.append(
            [
                nome,
                it.data.isoformat(),
                _as_utc(it.entrada_em).astimezone(PONTO_TZ).strftime("%Y-%m-%d %H:%M"),
                _as_utc(it.saida_em).astimezone(PONTO_TZ).strftime("%Y-%m-%d %H:%M") if it.saida_em else "",
                round((it.segundos_pausa or 0) / 60, 2),
                round(trab, 2) if trab is not None and not it.aberto else "",
                "sim" if it.aberto else "não",
            ]
        )
    ws.append([])
    ws.append(["Total trabalhado (h)", round(total_min / 60, 2)])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
