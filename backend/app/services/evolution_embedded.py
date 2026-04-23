"""Provisionamento da Evolution no Docker (URL interna + API key global) e QR Code."""

from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.whatsapp_chat import WhatsappSettings
from app.services import evolution_api

logger = logging.getLogger(__name__)


def _webhook_base_url() -> str:
    b = (settings.DX_CONNECT_WEBHOOK_BASE_URL or "").strip()
    if b:
        return b.rstrip("/")
    return "http://backend:8000"


def _internal_base() -> str:
    u = (settings.EVOLUTION_INTERNAL_BASE_URL or "").strip().rstrip("/")
    if not u:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evolution embutida não está configurada (EVOLUTION_INTERNAL_BASE_URL / EVOLUTION_GLOBAL_API_KEY).",
        )
    return u


def _global_key() -> str:
    k = (settings.EVOLUTION_GLOBAL_API_KEY or "").strip()
    if not k:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evolution embutida não está configurada (EVOLUTION_GLOBAL_API_KEY).",
        )
    return k


def _instance_name() -> str:
    return (settings.WHATSAPP_EMBEDDED_INSTANCE_NAME or "dxconnect").strip() or "dxconnect"


def _ensure_webhook_secret(db: Session, row: WhatsappSettings) -> str:
    if row.webhook_secret and str(row.webhook_secret).strip():
        return str(row.webhook_secret).strip()
    s = secrets.token_urlsafe(32)
    row.webhook_secret = s
    db.commit()
    db.refresh(row)
    return s


def _apikey_from_instance_dict(d: dict[str, Any]) -> str | None:
    """Extrai apikey/token dos formatos v1/v2 da Evolution (plano ou aninhado)."""
    h = d.get("hash")
    if isinstance(h, dict) and h.get("apikey"):
        return str(h["apikey"]).strip()
    for key in ("token", "apikey", "instanceToken", "apiKey"):
        v = d.get(key)
        if v and str(v).strip():
            return str(v).strip()
    integ = d.get("integration")
    if isinstance(integ, dict):
        v = integ.get("token") or integ.get("apikey")
        if v and str(v).strip():
            return str(v).strip()
    return None


def _extract_create_apikey(data: dict[str, Any]) -> str | None:
    if not isinstance(data, dict):
        return None
    # Envelope comum (ex.: { "response": { ... } } ou { "data": { ... } })
    for wrap_key in ("response", "data"):
        inner = data.get(wrap_key)
        if isinstance(inner, dict) and inner is not data:
            got = _extract_create_apikey(inner)
            if got:
                return got
    h = data.get("hash")
    if isinstance(h, dict) and h.get("apikey"):
        return str(h["apikey"]).strip()
    inst = data.get("instance")
    if isinstance(inst, dict):
        got = _apikey_from_instance_dict(inst)
        if got:
            return got
    return _apikey_from_instance_dict(data)


def _rows_from_fetch_payload(fetch_data: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(fetch_data, list):
        for x in fetch_data:
            if isinstance(x, dict):
                rows.append(x)
    elif isinstance(fetch_data, dict):
        if isinstance(fetch_data.get("response"), list):
            for x in fetch_data["response"]:
                if isinstance(x, dict):
                    rows.append(x)
        elif isinstance(fetch_data.get("instance"), list):
            for x in fetch_data["instance"]:
                if isinstance(x, dict):
                    rows.append(x)
        elif isinstance(fetch_data.get("instance"), dict):
            rows.append(fetch_data["instance"])
        elif isinstance(fetch_data.get("instances"), list):
            for x in fetch_data["instances"]:
                if isinstance(x, dict):
                    rows.append(x)
        elif isinstance(fetch_data.get("data"), list):
            for x in fetch_data["data"]:
                if isinstance(x, dict):
                    rows.append(x)
    return rows


def _token_from_fetch_payload(fetch_data: Any, want_name: str) -> str | None:
    """Extrai token/apikey da instância a partir de fetchInstances (formatos comuns v1/v2)."""
    rows = _rows_from_fetch_payload(fetch_data)
    want = want_name.strip().lower()
    for item in rows:
        inner = item.get("instance")
        if isinstance(inner, dict):
            name = str(inner.get("instanceName") or inner.get("name") or "").strip().lower()
            if name == want:
                got = _apikey_from_instance_dict(inner)
                if got:
                    return got
        name = str(item.get("name") or item.get("instanceName") or "").strip().lower()
        if name != want:
            continue
        got = _apikey_from_instance_dict(item)
        if got:
            return got
    return None


def provisionar_e_ligar_webhook(db: Session, row: WhatsappSettings) -> dict[str, Any]:
    """
    Cria (ou reutiliza) a instância na Evolution, grava URL interna + apikey da instância + webhook no DX Connect.
    Devolve payload do connect (QR) quando possível.
    """
    if not settings.evolution_embutida_disponivel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serviço Evolution embutido não está ativo. Suba o stack com `docker compose up` (serviço evolution-api) "
            "e variáveis EVOLUTION_INTERNAL_BASE_URL / EVOLUTION_GLOBAL_API_KEY no backend.",
        )
    secret = _ensure_webhook_secret(db, row)
    internal = _internal_base()
    gkey = _global_key()
    iname = _instance_name()
    webhook_url = f"{_webhook_base_url()}/v1/webhooks/evolution"

    body: dict[str, Any] = {
        "instanceName": iname,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
        "webhook": {
            "url": webhook_url,
            "byEvents": False,
            "events": ["MESSAGES_UPSERT"],
            "headers": {"X-Dx-Webhook-Secret": secret},
        },
    }

    code, data, err = evolution_api.evolution_create_instance(internal, gkey, body)
    api_inst: str | None = None
    if code in (200, 201) and isinstance(data, dict):
        api_inst = _extract_create_apikey(data)
    elif code in (403, 409) or (isinstance(data, dict) and data.get("error")):
        fc, fd, _fe = evolution_api.evolution_fetch_instances(internal, gkey)
        if fc == 200:
            api_inst = _token_from_fetch_payload(fd, iname)
        if not api_inst:
            logger.warning("Evolution create falhou (%s): %s — %s", code, err, data)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=err or (data if isinstance(data, str) else "Não foi possível criar ou localizar a instância na Evolution."),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=err or f"Evolution retornou HTTP {code}",
        )

    # Algumas imagens não devolvem hash.apikey no create nem apikey no fetch
    # (ex.: AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=false). A Evolution aceita
    # a mesma AUTHENTICATION_API_KEY global no header para connect/sendText.
    if not api_inst:
        logger.warning(
            "Evolution não devolveu apikey por instância no create/fetch; a usar apikey global configurada no stack."
        )
        api_inst = gkey

    row.evolution_base_url = internal
    row.evolution_instance_name = iname
    row.evolution_api_key = api_inst
    db.commit()
    db.refresh(row)

    cq, qdata, qerr = evolution_api.evolution_connect(internal, api_inst, iname)
    if cq != 200:
        logger.warning("Connect após provisionar: HTTP %s %s", cq, qerr)

    return {
        "instance": iname,
        "webhook_url": webhook_url,
        "qrcode": qdata if cq == 200 else None,
        "connect_http_status": cq,
        "connect_erro": qerr if cq != 200 else None,
    }


def obter_qrcode(db: Session, row: WhatsappSettings) -> dict[str, Any]:
    if not row.evolution_base_url or not row.evolution_instance_name or not row.evolution_api_key:
        raise HTTPException(status_code=400, detail="Provisione primeiro (modo simples) ou preencha a configuração manual.")
    code, data, err = evolution_api.evolution_connect(
        row.evolution_base_url,
        row.evolution_api_key,
        row.evolution_instance_name,
    )
    if code != 200:
        raise HTTPException(status_code=502, detail=err or f"HTTP {code}")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Resposta inválida da Evolution.")
    return data


def estado_conexao(db: Session, row: WhatsappSettings) -> dict[str, Any]:
    if not row.evolution_base_url or not row.evolution_instance_name or not row.evolution_api_key:
        return {"configurado": False, "state": None}
    code, data, err = evolution_api.evolution_connection_state_json(
        row.evolution_base_url,
        row.evolution_instance_name,
        row.evolution_api_key,
    )
    if code != 200:
        return {"configurado": True, "state": None, "erro": err or f"HTTP {code}"}
    return {"configurado": True, "state": data}


def repor_instancia(db: Session, row: WhatsappSettings) -> None:
    """Apaga a instância na Evolution (API key global) e limpa credenciais locais da instância."""
    if not settings.evolution_embutida_disponivel:
        raise HTTPException(status_code=400, detail="Modo embutido indisponível.")
    internal = _internal_base()
    gkey = _global_key()
    iname = _instance_name()
    try:
        evolution_api.evolution_delete_instance(internal, gkey, iname)
    except Exception:
        logger.exception("Evolution delete (repor)")
    row.evolution_api_key = None
    row.evolution_instance_name = None
    row.evolution_base_url = internal
    db.commit()
