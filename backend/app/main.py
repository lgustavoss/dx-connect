import logging
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.database import get_db

from app.api import (
    auth,
    redes,
    empresas,
    setores,
    atendentes,
    funcionarios_rede,
    status_ticket,
    tickets,
    dashboard,
    relatorios,
    audit,
    tipo_negocio,
    cadastro_aux,
    notificacoes,
    events,
    presenca,
    whatsapp_settings,
    whatsapp_chats,
    whatsapp_webhook,
    email_inbound_webhook,
    resend_inbound_webhook,
    respostas_prontas,
    pdv_catalogos,
    ticket_catalogos,
    empresa_pdvs,
    comercial_custos,
    system_settings,
    tenant,
    public_csat,
    system,
    routing,
    sla,
    kb,
    chat_interno,
    portal_chats,
    portal,
    saas,
    saas_public,
)
from app.config import settings
from app.core.audit import clear_audit_request_context, set_audit_request_context
from app.core.tenant_context import resolve_tenant_id, set_request_tenant_id
from app.core.lifecycle import dev_create_all_tables, production_require_alembic
from app.database import Base, engine
import app.models  # noqa: F401 — registra mapeamentos ORM / metadata


def _configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).setLevel(level)


_configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import os

    from app.services.realtime_emit import register_realtime_loop

    register_realtime_loop(asyncio.get_running_loop())

    # Testes (pytest): schema mínimo sem seed, backfill nem thread IBGE — ver tests/conftest.py (#46).

    if os.environ.get("DX_CONNECT_TESTING") == "1":
        dev_create_all_tables(engine, Base.metadata)
        yield
        return

    if settings.is_production:
        production_require_alembic(engine)
    else:
        dev_create_all_tables(engine, Base.metadata)

    if not settings.is_production:
        try:
            from app.seed import run_seed

            run_seed()
        except Exception as e:
            logger.warning(
                "Seed inicial não concluído (desenvolvimento). Use `python -m app.seed` no container/host. %s",
                e,
            )
    else:
        logger.info(
            "Produção: seed automático desativado. Crie dados iniciais com deploy (ex.: `python -m app.seed` controlado) ou painel."
        )
    # Tickets antigos: primeira linha do tempo a partir de descrição legada
    try:
        from app.models.ticket import Ticket, TicketMensagem
        from app.database import SessionLocal

        s = SessionLocal()
        try:
            for t in s.query(Ticket).all():
                n = s.query(TicketMensagem).filter(TicketMensagem.ticket_id == t.id).count()
                if n == 0:
                    body = (t.descricao or "").strip() or (
                        "(Abertura sem texto adicional — registro anterior ao histórico de mensagens.)"
                    )
                    s.add(TicketMensagem(ticket_id=t.id, atendente_id=None, tipo="abertura", corpo=body))
            s.commit()
        except Exception as ex:
            logger.warning("Backfill ticket_mensagens: %s", ex)
            s.rollback()
        finally:
            s.close()
    except Exception as ex:
        logger.warning("Backfill ticket_mensagens (import): %s", ex)
    # Somente desenvolvimento: compensa DBs antigos sem migration (produção deve usar só Alembic).
    if not settings.is_production:
        try:
            from sqlalchemy import text

            colunas_empresas = [
                "tipo_negocio_id INTEGER REFERENCES tipos_negocio(id)",
                "cnpj_cpf VARCHAR(18)",
                "razao_social VARCHAR(255)",
                "nome_fantasia VARCHAR(255)",
                "inscricao_estadual VARCHAR(20)",
                "endereco VARCHAR(255)",
                "numero VARCHAR(20)",
                "complemento VARCHAR(100)",
                "bairro VARCHAR(100)",
                "cidade VARCHAR(100)",
                "estado VARCHAR(2)",
                "cep VARCHAR(10)",
                "email VARCHAR(255)",
                "telefone VARCHAR(20)",
            ]
            with engine.begin() as conn:
                for col in colunas_empresas:
                    try:
                        conn.execute(text(f"ALTER TABLE empresas ADD COLUMN IF NOT EXISTS {col}"))
                    except Exception:
                        pass
                try:
                    conn.execute(text("ALTER TABLE redes ADD COLUMN IF NOT EXISTS login_retaguarda VARCHAR(120)"))
                except Exception:
                    pass
        except Exception:
            pass

    def ibge_municipios_sync_loop() -> None:
        from app.database import SessionLocal
        from app.services.ibge_municipios_sync import sync_ibge_municipios_if_stale

        interval = max(60, settings.IBGE_MUNICIPIOS_SYNC_INTERVAL_SECONDS)
        while True:
            db = SessionLocal()
            try:
                sync_ibge_municipios_if_stale(db)
                db.commit()
            except Exception as e:
                logger.warning("Sincronização em background (municípios IBGE): %s", e)
                db.rollback()
            finally:
                db.close()
            time.sleep(interval)

    threading.Thread(target=ibge_municipios_sync_loop, daemon=True, name="ibge-municipios-sync").start()

    def ticket_mensagem_email_outbox_loop() -> None:
        from app.database import SessionLocal
        from app.services.ticket_mensagem_email_outbox import process_pending_ticket_mensagem_emails

        interval = max(2, settings.TICKET_MENSAGEM_EMAIL_WORKER_INTERVAL_SECONDS)
        while True:
            db = SessionLocal()
            try:
                n = process_pending_ticket_mensagem_emails(db, limit=30)
                db.commit()
            except Exception as e:
                logger.warning("Worker e-mail de mensagens de ticket: %s", e)
                db.rollback()
            finally:
                db.close()
            time.sleep(interval)

    threading.Thread(
        target=ticket_mensagem_email_outbox_loop,
        daemon=True,
        name="ticket-mensagem-email-outbox",
    ).start()

    def notificacao_email_outbox_loop() -> None:
        from app.database import SessionLocal
        from app.services.notificacao_atendente_email import process_pending_notificacao_emails

        interval = max(5, settings.NOTIFICACAO_EMAIL_WORKER_INTERVAL_SECONDS)
        while True:
            db = SessionLocal()
            try:
                n = process_pending_notificacao_emails(db, limit=30)
                db.commit()
            except Exception as e:
                logger.warning("Worker e-mail de notificações: %s", e)
                db.rollback()
            finally:
                db.close()
            time.sleep(interval)

    threading.Thread(
        target=notificacao_email_outbox_loop,
        daemon=True,
        name="notificacao-email-outbox",
    ).start()

    def webhook_outbox_loop() -> None:
        from app.database import SessionLocal
        from app.services.ticket_closed_webhook import process_pending_webhooks

        interval = max(5, settings.WEBHOOK_OUTBOX_WORKER_INTERVAL_SECONDS)
        while True:
            db = SessionLocal()
            try:
                process_pending_webhooks(db, limit=30)
                db.commit()
            except Exception as e:
                logger.warning("Worker webhook outbox: %s", e)
                db.rollback()
            finally:
                db.close()
            time.sleep(interval)

    threading.Thread(
        target=webhook_outbox_loop,
        daemon=True,
        name="webhook-outbox",
    ).start()

    def whatsapp_inactivity_loop() -> None:
        from app.database import SessionLocal
        from app.services.whatsapp_avaliacao import process_whatsapp_avaliacao_timeouts
        from app.services.whatsapp_inactivity_worker import process_whatsapp_inactivity_closures

        interval = max(15, settings.WHATSAPP_INACTIVITY_WORKER_INTERVAL_SECONDS)
        while True:
            db = SessionLocal()
            try:
                process_whatsapp_inactivity_closures(db, limit=200)
                process_whatsapp_avaliacao_timeouts(db, limit=200)
            except Exception as e:
                logger.warning("Worker inatividade/avaliação WhatsApp: %s", e)
                db.rollback()
            finally:
                db.close()
            time.sleep(interval)

    threading.Thread(
        target=whatsapp_inactivity_loop,
        daemon=True,
        name="whatsapp-inactivity",
    ).start()

    def ticket_distribuicao_loop() -> None:
        from app.database import SessionLocal
        from app.services.ticket_distribuicao import processar_distribuicao_timeout

        interval = max(30, settings.TICKET_DISTRIBUICAO_WORKER_INTERVAL_SECONDS)
        while True:
            db = SessionLocal()
            try:
                n = processar_distribuicao_timeout(db, limit=50)
                if n:
                    db.commit()
                else:
                    db.rollback()
            except Exception as e:
                logger.warning("Worker distribuição de tickets: %s", e)
                db.rollback()
            finally:
                db.close()
            time.sleep(interval)

    threading.Thread(
        target=ticket_distribuicao_loop,
        daemon=True,
        name="ticket-distribuicao",
    ).start()

    def sla_violacao_loop() -> None:
        from app.database import SessionLocal
        from app.services.sla_notificacao import processar_alertas_sla

        interval = max(30, settings.SLA_WORKER_INTERVAL_SECONDS)
        while True:
            db = SessionLocal()
            try:
                n = processar_alertas_sla(db, limit=200)
                if n:
                    db.commit()
                else:
                    db.rollback()
            except Exception as e:
                logger.warning("Worker SLA: %s", e)
                db.rollback()
            finally:
                db.close()
            time.sleep(interval)

    threading.Thread(
        target=sla_violacao_loop,
        daemon=True,
        name="sla-violacao",
    ).start()

    if settings.SAAS_CONTROL_PLANE:

        def saas_provision_loop() -> None:
            from app.database import SessionLocal
            from app.services.saas_provisionamento import processar_provisionamentos_pendentes

            interval = max(10, settings.SAAS_PROVISION_WORKER_INTERVAL_SECONDS)
            while True:
                db = SessionLocal()
                try:
                    n = processar_provisionamentos_pendentes(db, limit=5)
                    if n:
                        db.commit()
                    else:
                        db.rollback()
                except Exception as e:
                    logger.warning("Worker SaaS provisionamento: %s", e)
                    db.rollback()
                finally:
                    db.close()
                time.sleep(interval)

        threading.Thread(
            target=saas_provision_loop,
            daemon=True,
            name="saas-provisionamento",
        ).start()

        def saas_renovacao_loop() -> None:
            from app.database import SessionLocal
            from app.services.saas_renovacoes import processar_renovacoes

            interval = max(60, settings.SAAS_RENEWAL_WORKER_INTERVAL_SECONDS)
            while True:
                db = SessionLocal()
                try:
                    n = processar_renovacoes(db, limit=200)
                    if n:
                        db.commit()
                    else:
                        db.rollback()
                except Exception as e:
                    logger.warning("Worker SaaS renovações: %s", e)
                    db.rollback()
                finally:
                    db.close()
                time.sleep(interval)

        threading.Thread(
            target=saas_renovacao_loop,
            daemon=True,
            name="saas-renovacoes",
        ).start()

    yield


_docs_kw = {}
if settings.is_production:
    _docs_kw = {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(
    title="DX Connect API",
    description="API do sistema de tickets e suporte",
    version="0.1.0",
    lifespan=lifespan,
    **_docs_kw,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Executado antes do CORS no pedido (último add_middleware = mais externo): valida header Host.
_th = settings.allowed_hosts_list()
if _th != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_th)


@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    """Define ``request.state.tenant_id``. Webhooks e health ficam isentos."""
    path = request.url.path
    if path.startswith("/v1/webhooks/") or path in (
        "/",
        "/health",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    ):
        return await call_next(request)
    try:
        tid = resolve_tenant_id(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    set_request_tenant_id(request, tid)
    return await call_next(request)


@app.middleware("http")
async def audit_request_context_middleware(request: Request, call_next):
    """Propaga IP, user-agent e request_id para registros de auditoria."""
    rid = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    if not rid:
        rid = str(uuid.uuid4())
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else None
    if not ip and request.client:
        ip = request.client.host
    set_audit_request_context(
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        request_id=rid,
    )
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        clear_audit_request_context()


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Cabeçalhos básicos na API; em produção complemente no Nginx/CDN (HSTS, CSP no HTML estático)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    if proto == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura exceções não tratadas, loga o traceback e retorna 500 com mensagem amigável."""
    logger.exception("Exceção não tratada: %s %s - %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Não foi possível concluir a ação. Tente novamente ou contate o suporte."},
    )

# Rotas versionadas (v2+ no futuro: outro prefix ou routers paralelos).
API_V1_PREFIX = "/v1"

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(redes.router, prefix=API_V1_PREFIX)
app.include_router(empresas.router, prefix=API_V1_PREFIX)
app.include_router(setores.router, prefix=API_V1_PREFIX)
app.include_router(atendentes.router, prefix=API_V1_PREFIX)
app.include_router(funcionarios_rede.router, prefix=API_V1_PREFIX)
app.include_router(status_ticket.router, prefix=API_V1_PREFIX)
app.include_router(tickets.router, prefix=API_V1_PREFIX)
app.include_router(dashboard.router, prefix=API_V1_PREFIX)
app.include_router(relatorios.router, prefix=API_V1_PREFIX)
app.include_router(audit.router, prefix=API_V1_PREFIX)
app.include_router(tipo_negocio.router, prefix=API_V1_PREFIX)
app.include_router(cadastro_aux.router, prefix=API_V1_PREFIX)
app.include_router(notificacoes.router, prefix=API_V1_PREFIX)
app.include_router(events.router, prefix=API_V1_PREFIX)
app.include_router(presenca.router, prefix=API_V1_PREFIX)
app.include_router(whatsapp_settings.router, prefix=API_V1_PREFIX)
app.include_router(whatsapp_chats.router, prefix=API_V1_PREFIX)
app.include_router(whatsapp_webhook.router, prefix=API_V1_PREFIX)
app.include_router(email_inbound_webhook.router, prefix=API_V1_PREFIX)
app.include_router(resend_inbound_webhook.router, prefix=API_V1_PREFIX)
app.include_router(respostas_prontas.router, prefix=API_V1_PREFIX)
app.include_router(pdv_catalogos.router, prefix=API_V1_PREFIX)
app.include_router(ticket_catalogos.router, prefix=API_V1_PREFIX)
app.include_router(comercial_custos.router, prefix=API_V1_PREFIX)
app.include_router(empresa_pdvs.router, prefix=API_V1_PREFIX)
app.include_router(system_settings.router, prefix=API_V1_PREFIX)
app.include_router(tenant.router, prefix=API_V1_PREFIX)
app.include_router(public_csat.router, prefix=API_V1_PREFIX)
app.include_router(system.router, prefix=API_V1_PREFIX)
app.include_router(routing.router, prefix=API_V1_PREFIX)
app.include_router(sla.router, prefix=API_V1_PREFIX)
app.include_router(kb.router, prefix=API_V1_PREFIX)
app.include_router(chat_interno.router, prefix=API_V1_PREFIX)
app.include_router(portal_chats.router, prefix=API_V1_PREFIX)
app.include_router(portal.router, prefix=API_V1_PREFIX)
app.include_router(saas.router, prefix=API_V1_PREFIX)
app.include_router(saas_public.router, prefix=API_V1_PREFIX)


def _app_route_paths() -> set[str]:
    """Coleta paths das rotas (FastAPI >= 0.137 guarda routers incluídos em árvore)."""
    return set(app.openapi().get("paths", {}))


def _app_capabilities() -> dict[str, bool]:
    paths = _app_route_paths()
    return {
        "settings_empresa_sistema": "/v1/settings/empresa-sistema" in paths,
        "settings_email": "/v1/settings/email" in paths,
        "tenant_atual": "/v1/tenant/atual" in paths,
        "pdv_catalogos": "/v1/pdv-rotulos" in paths,
        "ticket_catalogos": "/v1/ticket-naturezas" in paths,
        "empresa_pdvs": "/v1/empresas/{empresa_id}/pdvs" in paths
        or any(p.startswith("/v1/empresas/") and "/pdvs" in p for p in paths),
        "multi_tenant_mode": settings.DX_CONNECT_MULTI_TENANT,
        "evolution_embutida": settings.evolution_embutida_disponivel,
        "system_info": "/v1/system/info" in paths,
        "system_release_notes": "/v1/system/release-notes" in paths,
    }


@app.get("/health")
def health():
    from app.services.health_checks import build_health_payload

    return build_health_payload(capabilities=_app_capabilities())


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    from app.services.health_checks import build_readiness_payload

    body, status_code = build_readiness_payload(db=db, capabilities=_app_capabilities())
    return JSONResponse(content=body, status_code=status_code)
