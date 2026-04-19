import logging
import sys
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import auth, redes, empresas, setores, atendentes, funcionarios_rede, status_ticket, tickets, dashboard, audit, tipo_negocio, cadastro_aux, chat_assistant, whatsapp
from app.config import settings
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
app.include_router(audit.router, prefix=API_V1_PREFIX)
app.include_router(tipo_negocio.router, prefix=API_V1_PREFIX)
app.include_router(cadastro_aux.router, prefix=API_V1_PREFIX)
app.include_router(chat_assistant.router, prefix=API_V1_PREFIX)
app.include_router(whatsapp.router, prefix=API_V1_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}
