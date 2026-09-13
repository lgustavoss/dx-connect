"""Motor e consulta de alertas operacionais por instância (#1036 / #1037 / #1038)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.audit import registrar_audit
from app.models.cliente_saas import ClienteSaaS
from app.models.saas_alerta_ops import SaasAlertaOps, SaasAlertaOpsEvento

logger = logging.getLogger(__name__)

SINAIS = {
    "instancia_indisponivel": {
        "modulo": "api",
        "severidade": "vermelho",
        "titulo": "Instância indisponível (health)",
    },
    "instancia_nao_pronta": {
        "modulo": "api",
        "severidade": "amarelo",
        "titulo": "Instância não pronta (readiness)",
    },
    "stack_parada": {
        "modulo": "stack",
        "severidade": "vermelho",
        "titulo": "Stack da instância parada",
    },
    "stack_desconhecida": {
        "modulo": "stack",
        "severidade": "amarelo",
        "titulo": "Status da stack desconhecido",
    },
}

ESTADOS_ABERTOS = ("ativo", "mitigado")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _alerta_aberto(db: Session, cliente_id: int, codigo: str) -> SaasAlertaOps | None:
    return (
        db.query(SaasAlertaOps)
        .filter(
            SaasAlertaOps.cliente_saas_id == cliente_id,
            SaasAlertaOps.codigo_sinal == codigo,
            SaasAlertaOps.estado.in_(ESTADOS_ABERTOS),
        )
        .order_by(SaasAlertaOps.ciclo_id.desc())
        .first()
    )


def _proximo_ciclo(db: Session, cliente_id: int, codigo: str) -> int:
    max_ciclo = (
        db.query(func.max(SaasAlertaOps.ciclo_id))
        .filter(
            SaasAlertaOps.cliente_saas_id == cliente_id,
            SaasAlertaOps.codigo_sinal == codigo,
        )
        .scalar()
    )
    return int(max_ciclo or 0) + 1


def _registrar_evento(
    db: Session,
    alerta: SaasAlertaOps,
    tipo: str,
    mensagem: str,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        SaasAlertaOpsEvento(
            alerta_id=alerta.id,
            tipo=tipo,
            mensagem=mensagem,
            payload=payload,
        )
    )


def abrir_ou_atualizar_alerta(
    db: Session,
    *,
    cliente: ClienteSaaS,
    codigo: str,
    evidencia: dict[str, Any] | None = None,
) -> tuple[SaasAlertaOps, bool]:
    meta = SINAIS[codigo]
    aberto = _alerta_aberto(db, cliente.id, codigo)
    agora = _now()
    if aberto:
        aberto.last_seen_at = agora
        aberto.evidencia = evidencia
        db.flush()
        return aberto, False

    alerta = SaasAlertaOps(
        cliente_saas_id=cliente.id,
        codigo_sinal=codigo,
        modulo=meta["modulo"],
        severidade=meta["severidade"],
        estado="ativo",
        ciclo_id=_proximo_ciclo(db, cliente.id, codigo),
        started_at=agora,
        last_seen_at=agora,
        evidencia=evidencia,
        titulo=meta["titulo"],
    )
    db.add(alerta)
    db.flush()
    _registrar_evento(
        db,
        alerta,
        "aberto",
        f"Alerta aberto: {meta['titulo']}",
        payload=evidencia,
    )
    registrar_audit(
        db,
        entity_type="saas_alerta_ops",
        entity_id=alerta.id,
        action="alerta_aberto",
        atendente_id=None,
        payload={
            "cliente_saas_id": cliente.id,
            "slug": cliente.slug,
            "codigo_sinal": codigo,
            "severidade": meta["severidade"],
        },
    )
    return alerta, True


def resolver_alerta_se_aberto(
    db: Session,
    *,
    cliente: ClienteSaaS,
    codigo: str,
    evidencia: dict[str, Any] | None = None,
) -> SaasAlertaOps | None:
    aberto = _alerta_aberto(db, cliente.id, codigo)
    if not aberto:
        return None
    agora = _now()
    aberto.estado = "resolvido"
    aberto.resolved_at = agora
    aberto.last_seen_at = agora
    if evidencia:
        aberto.evidencia = {**(aberto.evidencia or {}), **evidencia}
    db.flush()
    _registrar_evento(
        db,
        aberto,
        "resolvido",
        "Sinal normalizado — alerta resolvido automaticamente",
        payload=evidencia,
    )
    registrar_audit(
        db,
        entity_type="saas_alerta_ops",
        entity_id=aberto.id,
        action="alerta_resolvido",
        atendente_id=None,
        payload={"cliente_saas_id": cliente.id, "codigo_sinal": codigo},
    )
    return aberto


def mitigar_alerta(
    db: Session,
    alerta_id: int,
    mensagem: str | None = None,
    *,
    atendente_id: int | None = None,
) -> SaasAlertaOps:
    alerta = db.query(SaasAlertaOps).filter(SaasAlertaOps.id == alerta_id).first()
    if not alerta:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    if alerta.estado == "resolvido":
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Alerta já resolvido")
    if alerta.estado == "mitigado":
        return alerta
    agora = _now()
    alerta.estado = "mitigado"
    alerta.mitigated_at = agora
    db.flush()
    _registrar_evento(
        db,
        alerta,
        "mitigado",
        mensagem or "Marcado como mitigado pela equipe Ops",
    )
    registrar_audit(
        db,
        entity_type="saas_alerta_ops",
        entity_id=alerta.id,
        action="alerta_mitigado",
        atendente_id=atendente_id,
        payload={"cliente_saas_id": alerta.cliente_saas_id, "codigo_sinal": alerta.codigo_sinal},
    )
    return alerta


def _urls_probe(cliente: ClienteSaaS) -> list[str]:
    urls: list[str] = []
    base = (cliente.instancia_url or "").strip().rstrip("/")
    if base:
        # instancia_url costuma ser a UI; health fica na API. Preferimos porta local na VPS.
        pass
    if cliente.api_port:
        urls.append(f"http://127.0.0.1:{cliente.api_port}/health")
        urls.append(f"http://127.0.0.1:{cliente.api_port}/health/ready")
    if base and "/health" not in base:
        # Tentativa pública só se não houver porta (dev/remoto).
        if not cliente.api_port:
            urls.append(f"{base}/health")
            urls.append(f"{base}/health/ready")
    return urls


def _http_get(url: str, timeout: float) -> tuple[int | None, dict[str, Any] | None, str | None]:
    try:
        req = Request(url, method="GET", headers={"Accept": "application/json", "User-Agent": "dx-connect-saas-ops"})
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL controlada (porta/instância do cliente)
            code = getattr(resp, "status", None) or resp.getcode()
            raw = resp.read(65536)
            body = None
            try:
                import json

                body = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                body = None
            return int(code), body if isinstance(body, dict) else None, None
    except HTTPError as e:
        return int(e.code), None, str(e.reason or e)
    except URLError as e:
        return None, None, str(e.reason if hasattr(e, "reason") else e)
    except Exception as e:  # noqa: BLE001
        return None, None, str(e)


def _avaliar_cliente(db: Session, cliente: ClienteSaaS, falhas: dict[int, dict[str, int]]) -> int:
    """Avalia sinais de um cliente. Retorna quantos alertas mudaram (abriu/resolveu)."""
    mudancas = 0
    timeout = float(settings.SAAS_ALERTAS_OPS_PROBE_TIMEOUT_SECONDS)
    limiar = max(1, settings.SAAS_ALERTAS_OPS_PROBE_FALHAS)
    contadores = falhas.setdefault(cliente.id, {})

    # --- stack ---
    stack = (cliente.stack_status or "").strip().lower() or None
    provisionado = (cliente.provisionamento_status or "") == "sucesso"
    if stack == "stopped":
        _, created = abrir_ou_atualizar_alerta(
            db,
            cliente=cliente,
            codigo="stack_parada",
            evidencia={"stack_status": stack, "slug": cliente.slug},
        )
        if created:
            mudancas += 1
        if resolver_alerta_se_aberto(db, cliente=cliente, codigo="stack_desconhecida"):
            mudancas += 1
    elif stack == "running":
        if resolver_alerta_se_aberto(
            db, cliente=cliente, codigo="stack_parada", evidencia={"stack_status": stack}
        ):
            mudancas += 1
        if resolver_alerta_se_aberto(
            db, cliente=cliente, codigo="stack_desconhecida", evidencia={"stack_status": stack}
        ):
            mudancas += 1
    elif provisionado and stack in (None, "unknown"):
        _, created = abrir_ou_atualizar_alerta(
            db,
            cliente=cliente,
            codigo="stack_desconhecida",
            evidencia={"stack_status": stack or "unknown", "slug": cliente.slug},
        )
        if created:
            mudancas += 1
        if resolver_alerta_se_aberto(db, cliente=cliente, codigo="stack_parada"):
            mudancas += 1

    # --- health probe ---
    urls = _urls_probe(cliente)
    health_url = next((u for u in urls if u.endswith("/health") and not u.endswith("/ready")), None)
    ready_url = next((u for u in urls if u.endswith("/health/ready")), None)

    if health_url:
        code, body, err = _http_get(health_url, timeout)
        ok = code is not None and 200 <= code < 300
        if ok:
            contadores["health"] = 0
            if resolver_alerta_se_aberto(
                db,
                cliente=cliente,
                codigo="instancia_indisponivel",
                evidencia={"url": health_url, "http_status": code, "body_status": (body or {}).get("status")},
            ):
                mudancas += 1
        else:
            contadores["health"] = contadores.get("health", 0) + 1
            if contadores["health"] >= limiar:
                _, created = abrir_ou_atualizar_alerta(
                    db,
                    cliente=cliente,
                    codigo="instancia_indisponivel",
                    evidencia={
                        "url": health_url,
                        "http_status": code,
                        "erro": err,
                        "falhas_consecutivas": contadores["health"],
                    },
                )
                if created:
                    mudancas += 1

    if ready_url:
        code, body, err = _http_get(ready_url, timeout)
        status_body = (body or {}).get("status") if body else None
        ok = code is not None and 200 <= code < 300 and status_body not in ("degraded", "unavailable")
        if ok:
            contadores["ready"] = 0
            if resolver_alerta_se_aberto(
                db,
                cliente=cliente,
                codigo="instancia_nao_pronta",
                evidencia={"url": ready_url, "http_status": code, "body_status": status_body},
            ):
                mudancas += 1
        else:
            contadores["ready"] = contadores.get("ready", 0) + 1
            if contadores["ready"] >= limiar:
                _, created = abrir_ou_atualizar_alerta(
                    db,
                    cliente=cliente,
                    codigo="instancia_nao_pronta",
                    evidencia={
                        "url": ready_url,
                        "http_status": code,
                        "body_status": status_body,
                        "erro": err,
                        "falhas_consecutivas": contadores["ready"],
                    },
                )
                if created:
                    mudancas += 1

    return mudancas


# Contadores em memória do processo (worker). Em multi-worker, limiar é best-effort.
_FALHAS_PROBE: dict[int, dict[str, int]] = {}


def processar_alertas_ops(db: Session, limit: int = 200) -> int:
    """Avalia instâncias ativas/trial e atualiza alertas. Retorna nº de mudanças."""
    if not settings.SAAS_CONTROL_PLANE:
        return 0

    clientes = (
        db.query(ClienteSaaS)
        .filter(ClienteSaaS.status.in_(("trial", "ativo")))
        .order_by(ClienteSaaS.id.asc())
        .limit(limit)
        .all()
    )
    total = 0
    for c in clientes:
        try:
            total += _avaliar_cliente(db, c, _FALHAS_PROBE)
        except Exception as e:  # noqa: BLE001
            logger.warning("Avaliação alertas ops cliente %s: %s", c.slug, e)
    return total


def listar_alertas(
    db: Session,
    *,
    estado: str | None = None,
    severidade: str | None = None,
    modulo: str | None = None,
    cliente_saas_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SaasAlertaOps], int]:
    q = db.query(SaasAlertaOps).options(joinedload(SaasAlertaOps.cliente))
    if estado:
        q = q.filter(SaasAlertaOps.estado == estado)
    if severidade:
        q = q.filter(SaasAlertaOps.severidade == severidade)
    if modulo:
        q = q.filter(SaasAlertaOps.modulo == modulo)
    if cliente_saas_id is not None:
        q = q.filter(SaasAlertaOps.cliente_saas_id == cliente_saas_id)
    total = q.count()
    # Criticidade: ativo/mitigado/resolvido (A→R) e vermelho antes de amarelo (desc).
    items = (
        q.order_by(
            SaasAlertaOps.estado.asc(),
            SaasAlertaOps.severidade.desc(),
            SaasAlertaOps.started_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def resumo_global(db: Session, *, cliente_saas_id: int | None = None) -> dict[str, Any]:
    q = db.query(SaasAlertaOps).filter(SaasAlertaOps.estado.in_(ESTADOS_ABERTOS))
    if cliente_saas_id is not None:
        q = q.filter(SaasAlertaOps.cliente_saas_id == cliente_saas_id)
    abertos = q.all()
    por_sev = {"amarelo": 0, "vermelho": 0}
    por_modulo: dict[str, int] = {}
    clientes: set[int] = set()
    for a in abertos:
        por_sev[a.severidade] = por_sev.get(a.severidade, 0) + 1
        por_modulo[a.modulo] = por_modulo.get(a.modulo, 0) + 1
        clientes.add(a.cliente_saas_id)
    modulos_top = sorted(
        [{"modulo": m, "total": n} for m, n in por_modulo.items()],
        key=lambda x: (-x["total"], x["modulo"]),
    )
    return {
        "alertas_ativos": len(abertos),
        "por_severidade": por_sev,
        "instancias_afetadas": len(clientes),
        "modulos_mais_incidentes": modulos_top[:10],
    }


def obter_alerta(db: Session, alerta_id: int) -> SaasAlertaOps:
    row = (
        db.query(SaasAlertaOps)
        .options(joinedload(SaasAlertaOps.cliente), joinedload(SaasAlertaOps.eventos))
        .filter(SaasAlertaOps.id == alerta_id)
        .first()
    )
    if not row:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    return row


def listar_por_cliente(db: Session, cliente_id: int, limit: int = 50) -> list[SaasAlertaOps]:
    """Lista alertas do cliente com cliente + eventos em uma query (sem N+1)."""
    return (
        db.query(SaasAlertaOps)
        .options(joinedload(SaasAlertaOps.cliente), joinedload(SaasAlertaOps.eventos))
        .filter(SaasAlertaOps.cliente_saas_id == cliente_id)
        .order_by(
            SaasAlertaOps.estado.asc(),
            SaasAlertaOps.severidade.desc(),
            SaasAlertaOps.started_at.desc(),
        )
        .limit(limit)
        .all()
    )
