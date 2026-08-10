"""Renovações e alertas de licenças SaaS (#528 / DR-08)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente_saas import ClienteSaaS
from app.models.saas_alerta_emitido import SaasAlertaEmitido
from app.services.saas_clientes import SaasErro, obter
from app.services.saas_notify import notificar_equipe_saas

logger = logging.getLogger(__name__)

EVENTO_EM_RISCO = "renovacao_em_risco"
EVENTO_VENCIDO = "vencido_suspenso"


def renovar(db: Session, cliente_id: int, *, dias: int | None = None, nova_data: date | None = None) -> ClienteSaaS:
    row = obter(db, cliente_id)
    if nova_data is not None:
        row.data_renovacao = nova_data
    else:
        base = row.data_renovacao or date.today()
        if base < date.today():
            base = date.today()
        add = dias if dias is not None else max(1, int(settings.SAAS_TRIAL_DAYS or 30))
        if add < 1:
            raise SaasErro("Dias de renovação deve ser >= 1")
        row.data_renovacao = base + timedelta(days=add)

    if row.status in ("suspenso", "trial"):
        row.status = "ativo"
        db.flush()
        from app.services.saas_stack import aplicar_reativacao_stack

        return aplicar_reativacao_stack(db, row)
    db.flush()
    return row


def _ja_emitido(db: Session, cliente_id: int, evento: str, ref: date) -> bool:
    return (
        db.query(SaasAlertaEmitido.id)
        .filter(
            SaasAlertaEmitido.cliente_saas_id == cliente_id,
            SaasAlertaEmitido.evento == evento,
            SaasAlertaEmitido.referencia_data == ref,
        )
        .first()
        is not None
    )


def _registrar_alerta(db: Session, cliente_id: int, evento: str, ref: date) -> None:
    db.add(
        SaasAlertaEmitido(
            cliente_saas_id=cliente_id,
            evento=evento,
            referencia_data=ref,
        )
    )
    db.flush()


def processar_renovacoes(db: Session, *, limit: int = 200) -> int:
    """Worker: alerta próximos vencimentos e suspende vencidos (trial/ativo)."""
    if not settings.SAAS_CONTROL_PLANE:
        return 0

    hoje = date.today()
    janela = max(1, int(settings.SAAS_RENEWAL_ALERT_DAYS_BEFORE or 14))
    limite_alerta = hoje + timedelta(days=janela)

    acoes = 0
    rows = (
        db.query(ClienteSaaS)
        .filter(
            ClienteSaaS.data_renovacao.isnot(None),
            ClienteSaaS.status.in_(("trial", "ativo")),
        )
        .order_by(ClienteSaaS.data_renovacao.asc())
        .limit(limit)
        .all()
    )

    for row in rows:
        ref = row.data_renovacao
        if ref is None:
            continue

        if ref < hoje:
            if not _ja_emitido(db, row.id, EVENTO_VENCIDO, ref):
                row.status = "suspenso"
                db.flush()
                from app.services.saas_stack import aplicar_suspensao_stack

                aplicar_suspensao_stack(db, row)
                _registrar_alerta(db, row.id, EVENTO_VENCIDO, ref)
                notificar_equipe_saas(
                    db,
                    subject=f"[DeskRudder] Licença vencida — {row.nome} ({row.slug})",
                    body=(
                        f"A licença venceu em {ref.isoformat()} e foi marcada como suspensa.\n"
                        f"Renove no painel /saas/licencas/{row.id}.\n"
                    ),
                )
                acoes += 1
            continue

        if hoje <= ref <= limite_alerta:
            if not _ja_emitido(db, row.id, EVENTO_EM_RISCO, ref):
                dias = (ref - hoje).days
                _registrar_alerta(db, row.id, EVENTO_EM_RISCO, ref)
                notificar_equipe_saas(
                    db,
                    subject=f"[DeskRudder] Renovação em {dias} dia(s) — {row.slug}",
                    body=(
                        f"Cliente: {row.nome}\n"
                        f"Slug: {row.slug}\n"
                        f"Vence em: {ref.isoformat()} ({dias} dia(s))\n"
                        f"Painel: /saas/licencas/{row.id}\n"
                    ),
                )
                acoes += 1

    return acoes


def dias_para_renovacao(data_renovacao: date | None, *, hoje: date | None = None) -> int | None:
    if data_renovacao is None:
        return None
    base = hoje or date.today()
    return (data_renovacao - base).days
