"""Pools Boleto Cloud e vínculos cliente→pool no control-plane (#1392)."""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.boleto_pool import BOLETO_CLOUD_URL_SANDBOX, BoletoPool, BoletoPoolVinculo
from app.models.cliente_saas import ClienteSaaS
from app.schemas.saas_boleto_cloud import (
    BoletoCloudRead,
    BoletoCloudTestarResultado,
    BoletoCloudUpsert,
    BoletoPoolLista,
    BoletoPoolRead,
    BoletoPoolUpsert,
    BoletoVinculoCreate,
    BoletoVinculoLista,
    BoletoVinculoRead,
)
from app.services.secret_box import decrypt_str, encrypt_str

logger = logging.getLogger(__name__)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def pool_para_read(db: Session, row: BoletoPool) -> BoletoPoolRead:
    vinculados = (
        db.query(BoletoPoolVinculo)
        .filter(
            BoletoPoolVinculo.pool_id == row.id,
            BoletoPoolVinculo.vigencia_ate.is_(None),
        )
        .count()
    )
    return BoletoPoolRead(
        id=row.id,
        apelido=row.apelido,
        email_login=row.email_login,
        api_base_url=row.api_base_url or BOLETO_CLOUD_URL_SANDBOX,
        faixa_teto=row.faixa_teto,
        notas=row.notas,
        ativo=bool(row.ativo),
        tem_api_key=bool((row.api_key_cifrada or "").strip()),
        clientes_vinculados=vinculados,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def listar_pools(db: Session) -> BoletoPoolLista:
    rows = db.query(BoletoPool).order_by(BoletoPool.apelido.asc(), BoletoPool.id.asc()).all()
    items = [pool_para_read(db, r) for r in rows]
    return BoletoPoolLista(items=items, total=len(items))


def obter_pool(db: Session, pool_id: int) -> BoletoPool:
    row = db.query(BoletoPool).filter(BoletoPool.id == pool_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pool não encontrado.")
    return row


def criar_pool(db: Session, data: BoletoPoolUpsert) -> BoletoPoolRead:
    apelido = (data.apelido or "").strip()
    if not apelido:
        raise HTTPException(status_code=400, detail="Informe o apelido do pool.")
    base = (data.api_base_url or BOLETO_CLOUD_URL_SANDBOX).strip().rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(status_code=400, detail="A URL base deve começar com https://")

    row = BoletoPool(
        apelido=apelido,
        email_login=(data.email_login or "").strip() or None,
        api_base_url=base,
        faixa_teto=data.faixa_teto,
        notas=(data.notas or "").strip() or None,
        ativo=data.ativo,
    )
    api_key = (data.api_key or "").strip()
    if api_key:
        row.api_key_cifrada = encrypt_str(api_key)
    db.add(row)
    db.commit()
    db.refresh(row)
    return pool_para_read(db, row)


def atualizar_pool(db: Session, pool_id: int, data: BoletoPoolUpsert) -> BoletoPoolRead:
    row = obter_pool(db, pool_id)
    apelido = (data.apelido or "").strip()
    if not apelido:
        raise HTTPException(status_code=400, detail="Informe o apelido do pool.")
    base = (data.api_base_url or BOLETO_CLOUD_URL_SANDBOX).strip().rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(status_code=400, detail="A URL base deve começar com https://")

    row.apelido = apelido
    row.email_login = (data.email_login or "").strip() or None
    row.api_base_url = base
    row.faixa_teto = data.faixa_teto
    row.notas = (data.notas or "").strip() or None
    row.ativo = data.ativo
    api_key = (data.api_key or "").strip()
    if api_key:
        row.api_key_cifrada = encrypt_str(api_key)
    db.commit()
    db.refresh(row)
    return pool_para_read(db, row)


def _auth_header(api_key: str) -> dict[str, str]:
    cred = base64.b64encode(f"{api_key}:token".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {cred}", "Accept": "application/json"}


def testar_pool(db: Session, pool_id: int, client: httpx.Client | None = None) -> BoletoCloudTestarResultado:
    row = obter_pool(db, pool_id)
    if not row.ativo:
        raise HTTPException(status_code=400, detail="O pool está inativo. Ative antes de testar.")
    if not (row.api_key_cifrada or "").strip():
        raise HTTPException(status_code=400, detail="Cadastre a API Key antes de testar.")
    try:
        api_key = decrypt_str(row.api_key_cifrada)
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Não foi possível ler a API Key cifrada.") from e

    base = (row.api_base_url or BOLETO_CLOUD_URL_SANDBOX).rstrip("/") + "/"
    # Auth-only: lista boletos (não exige token de conta bancária).
    url = urljoin(base, "boletos")

    own = client is None
    http = client or httpx.Client(timeout=20.0)
    try:
        resp = http.get(url, headers=_auth_header(api_key), params={"max": 1})
    except httpx.HTTPError as e:
        logger.info("boleto_cloud_testar_rede_falhou: %s", type(e).__name__)
        return BoletoCloudTestarResultado(
            ok=False,
            mensagem="Não foi possível alcançar o Boleto Cloud. Verifique a URL e a rede.",
            http_status=None,
        )
    finally:
        if own:
            http.close()

    if resp.status_code in (401, 403):
        return BoletoCloudTestarResultado(
            ok=False,
            mensagem="API Key recusada pelo Boleto Cloud.",
            http_status=resp.status_code,
        )
    if 200 <= resp.status_code < 300 or resp.status_code in (400, 404, 422):
        # 400/404/422 com auth aceita = key válida (path/params podem variar).
        return BoletoCloudTestarResultado(
            ok=True,
            mensagem="Conexão com o Boleto Cloud OK (API Key aceita).",
            http_status=resp.status_code,
        )
    return BoletoCloudTestarResultado(
        ok=False,
        mensagem=f"Resposta inesperada do Boleto Cloud (HTTP {resp.status_code}).",
        http_status=resp.status_code,
    )


def _vinculo_ativo_agora(v: BoletoPoolVinculo, agora: datetime | None = None) -> bool:
    agora = agora or _agora()
    de = v.vigencia_de
    if de.tzinfo is None:
        de = de.replace(tzinfo=timezone.utc)
    if de > agora:
        return False
    ate = v.vigencia_ate
    if ate is None:
        return True
    if ate.tzinfo is None:
        ate = ate.replace(tzinfo=timezone.utc)
    return ate > agora


def _vinculo_to_read(v: BoletoPoolVinculo) -> BoletoVinculoRead:
    cli = getattr(v, "cliente", None)
    pool = getattr(v, "pool", None)
    return BoletoVinculoRead(
        id=v.id,
        cliente_saas_id=v.cliente_saas_id,
        cliente_nome=cli.nome if cli else None,
        cliente_slug=cli.slug if cli else None,
        pool_id=v.pool_id,
        pool_apelido=pool.apelido if pool else None,
        vigencia_de=v.vigencia_de,
        vigencia_ate=v.vigencia_ate,
        ativo_agora=_vinculo_ativo_agora(v),
        notas=v.notas,
        created_at=v.created_at,
    )


def listar_vinculos_cliente(db: Session, cliente_saas_id: int) -> BoletoVinculoLista:
    cli = db.query(ClienteSaaS).filter(ClienteSaaS.id == cliente_saas_id).first()
    if not cli:
        raise HTTPException(status_code=404, detail="Cliente SaaS não encontrado.")
    rows = (
        db.query(BoletoPoolVinculo)
        .filter(BoletoPoolVinculo.cliente_saas_id == cliente_saas_id)
        .order_by(BoletoPoolVinculo.vigencia_de.desc(), BoletoPoolVinculo.id.desc())
        .all()
    )
    return BoletoVinculoLista(items=[_vinculo_to_read(r) for r in rows], total=len(rows))


def vincular_cliente(db: Session, cliente_saas_id: int, data: BoletoVinculoCreate) -> BoletoVinculoRead:
    cli = db.query(ClienteSaaS).filter(ClienteSaaS.id == cliente_saas_id).first()
    if not cli:
        raise HTTPException(status_code=404, detail="Cliente SaaS não encontrado.")
    pool = obter_pool(db, data.pool_id)
    if not pool.ativo:
        raise HTTPException(status_code=400, detail="Não é possível vincular a um pool inativo.")

    agora = _agora()
    if data.encerrar_anterior:
        abertos = (
            db.query(BoletoPoolVinculo)
            .filter(
                BoletoPoolVinculo.cliente_saas_id == cliente_saas_id,
                BoletoPoolVinculo.vigencia_ate.is_(None),
            )
            .all()
        )
        for ant in abertos:
            ant.vigencia_ate = agora

    inicio = data.vigencia_de or agora
    row = BoletoPoolVinculo(
        cliente_saas_id=cliente_saas_id,
        pool_id=pool.id,
        vigencia_de=inicio,
        vigencia_ate=None,
        notas=(data.notas or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # lazy load
    _ = row.pool
    _ = row.cliente
    return _vinculo_to_read(row)


def vinculo_ativo_do_cliente(db: Session, cliente_saas_id: int) -> BoletoPoolVinculo | None:
    rows = (
        db.query(BoletoPoolVinculo)
        .filter(BoletoPoolVinculo.cliente_saas_id == cliente_saas_id)
        .order_by(BoletoPoolVinculo.vigencia_de.desc())
        .all()
    )
    for v in rows:
        if _vinculo_ativo_agora(v):
            return v
    return None


# --- Compatibilidade piloto (primeiro pool) ---

def obter_piloto(db: Session) -> BoletoPool | None:
    return db.query(BoletoPool).order_by(BoletoPool.id.asc()).first()


def obter_mascarado(db: Session) -> BoletoCloudRead:
    row = obter_piloto(db)
    if not row:
        raise HTTPException(status_code=404, detail="Credencial Boleto Cloud ainda não cadastrada.")
    return BoletoCloudRead(
        id=row.id,
        apelido=row.apelido,
        api_base_url=row.api_base_url or BOLETO_CLOUD_URL_SANDBOX,
        ativo=bool(row.ativo),
        tem_api_key=bool((row.api_key_cifrada or "").strip()),
        tem_conta_token=bool((row.conta_token_cifrado or "").strip()),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def upsert(db: Session, data: BoletoCloudUpsert) -> BoletoCloudRead:
    """Mantém o PUT legado: cria/atualiza o primeiro pool."""
    body = BoletoPoolUpsert(
        apelido=data.apelido,
        api_base_url=data.api_base_url,
        ativo=data.ativo,
        api_key=data.api_key,
    )
    row = obter_piloto(db)
    if not row:
        criar_pool(db, body)
    else:
        atualizar_pool(db, row.id, body)
    row = obter_piloto(db)
    assert row is not None
    token = (data.conta_token or "").strip()
    if token:
        row.conta_token_cifrado = encrypt_str(token)
        db.commit()
        db.refresh(row)
    return BoletoCloudRead(
        id=row.id,
        apelido=row.apelido,
        api_base_url=row.api_base_url or BOLETO_CLOUD_URL_SANDBOX,
        ativo=bool(row.ativo),
        tem_api_key=bool((row.api_key_cifrada or "").strip()),
        tem_conta_token=bool((row.conta_token_cifrado or "").strip()),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def testar_conexao(db: Session, client: httpx.Client | None = None) -> BoletoCloudTestarResultado:
    row = obter_piloto(db)
    if not row:
        raise HTTPException(status_code=404, detail="Credencial Boleto Cloud ainda não cadastrada.")
    return testar_pool(db, row.id, client=client)
