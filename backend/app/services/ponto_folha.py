"""Export contábil / template folha RH (#975)."""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

from fastapi import HTTPException
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.auth import ROLES_ATENDENTE
from app.models.atendente import Atendente
from app.models.audit_log import AuditLog
from app.models.ponto_batida import PontoBatida
from app.services import escala as escala_svc
from app.services import ponto as ponto_svc
from app.services import ponto_cobertura as cob_svc
from app.services import ponto_settings as ponto_settings_svc
from app.services.ponto_relatorio import _coletar_ajustes_audit, _rotulo_acao_ajuste

COLUNAS = [
    "matricula",
    "nome",
    "email",
    "desde",
    "ate",
    "dias_escala",
    "dias_feriado",
    "previsto_horas",
    "realizado_horas",
    "banco_horas",
    "atrasos",
    "faltas",
    "he_minutos",
    "ajustes",
]


def _segundos_para_horas(seg: int) -> str:
    return f"{(seg / 3600.0):.2f}".replace(".", ",")


def _atendentes_folha(
    db: Session, admin: Atendente, *, atendente_id: int | None
) -> list[Atendente]:
    q = db.query(Atendente).filter(
        Atendente.tenant_id == admin.tenant_id,
        Atendente.ativo.is_(True),
        Atendente.role.in_(tuple(ROLES_ATENDENTE)),
    )
    if atendente_id is not None:
        q = q.filter(Atendente.id == atendente_id)
    return q.order_by(Atendente.nome.asc()).all()


def _ajustes_por_atendente(ajustes: list[AuditLog]) -> dict[int, int]:
    contagem: dict[int, int] = {}
    for a in ajustes:
        payload = a.payload if isinstance(getattr(a, "payload", None), dict) else {}
        if not isinstance(payload, dict):
            continue
        aid = payload.get("atendente_id")
        if aid is None:
            continue
        try:
            aid_i = int(aid)
        except (TypeError, ValueError):
            continue
        contagem[aid_i] = contagem.get(aid_i, 0) + 1
    return contagem


def _linha_folha(
    db: Session,
    atendente: Atendente,
    *,
    desde: date,
    ate: date,
    ajustes_n: int,
) -> dict:
    bh = ponto_svc.banco_horas(db, atendente, desde=desde, ate=ate)
    faltas = 0
    atrasos = 0
    d = desde
    usa = escala_svc.escala_configurada(atendente)
    while d <= ate:
        feriado = ponto_settings_svc.eh_feriado(db, atendente.tenant_id, d)
        esp = cob_svc.eh_dia_esperado_efetivo(db, atendente, d) if not feriado else False
        ini, fim = ponto_svc._bounds_periodo(d, d)
        bats = (
            ponto_svc._q_ativas(db)
            .filter(
                PontoBatida.atendente_id == atendente.id,
                PontoBatida.registrado_em >= ini,
                PontoBatida.registrado_em < fim,
            )
            .all()
        )
        te = any(b.tipo == "entrada" for b in bats)
        ts = any(b.tipo == "saida" for b in bats)
        atrasado = ponto_svc._atrasado_entrada(atendente, ponto_svc._primeira_entrada_do_dia(bats))
        st = ponto_svc._status_dia(
            usa_escala=usa or esp,
            esperado=esp,
            tem_entrada=te,
            tem_saida=ts,
            feriado=feriado,
            atrasado=atrasado,
        )
        if st == "falta":
            faltas += 1
        if atrasado or st == "atraso":
            atrasos += 1
        d += timedelta(days=1)

    he = ponto_svc._he_minutos_periodo(db, atendente, desde=desde, ate=ate)
    return {
        "matricula": str(atendente.id),
        "nome": atendente.nome,
        "email": atendente.email or "",
        "desde": desde.isoformat(),
        "ate": ate.isoformat(),
        "dias_escala": bh.dias_escala,
        "dias_feriado": bh.dias_feriado,
        "previsto_horas": _segundos_para_horas(bh.segundos_esperados),
        "realizado_horas": _segundos_para_horas(bh.segundos_realizados),
        "banco_horas": _segundos_para_horas(bh.saldo_segundos),
        "atrasos": atrasos,
        "faltas": faltas,
        "he_minutos": he,
        "ajustes": ajustes_n,
    }


def coletar_linhas(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date,
    ate: date,
) -> list[dict]:
    if ate < desde:
        raise HTTPException(status_code=400, detail="Período inválido (até < desde).")
    ajustes = _coletar_ajustes_audit(db, admin, desde=desde, ate=ate)
    por_at = _ajustes_por_atendente(ajustes)
    return [
        _linha_folha(db, a, desde=desde, ate=ate, ajustes_n=por_at.get(a.id, 0))
        for a in _atendentes_folha(db, admin, atendente_id=atendente_id)
    ]


def export_folha_csv(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date,
    ate: date,
) -> str:
    linhas = coletar_linhas(db, admin, atendente_id=atendente_id, desde=desde, ate=ate)
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.DictWriter(buf, fieldnames=COLUNAS, delimiter=";")
    w.writeheader()
    for row in linhas:
        w.writerow(row)
    return buf.getvalue()


def export_folha_xlsx(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None,
    desde: date,
    ate: date,
) -> bytes:
    linhas = coletar_linhas(db, admin, atendente_id=atendente_id, desde=desde, ate=ate)
    wb = Workbook()
    ws = wb.active
    ws.title = "Folha"
    ws.append(COLUNAS)
    for row in linhas:
        ws.append([row[c] for c in COLUNAS])
    ws2 = wb.create_sheet("Ajustes")
    ws2.append(["Quando", "Autor", "Ação", "Batida ID", "Motivo", "Payload"])
    for a in _coletar_ajustes_audit(db, admin, desde=desde, ate=ate):
        payload = a.payload if isinstance(getattr(a, "payload", None), dict) else {}
        ws2.append(
            [
                a.created_at.isoformat() if a.created_at else "",
                a.atendente.nome if a.atendente else "",
                _rotulo_acao_ajuste(a.action),
                a.entity_id,
                (payload or {}).get("motivo") or "",
                str(payload or ""),
            ]
        )
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
