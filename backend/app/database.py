import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings


def database_url_psycopg2(url: str) -> str:
    """SQLAlchemy 2.1+ trata postgresql:// como psycopg (v3). O projeto instala psycopg2."""
    raw = (url or "").strip()
    if "://" not in raw:
        return raw
    scheme, rest = raw.split("://", 1)
    scheme_l = scheme.lower()
    if scheme_l in ("postgres", "postgresql") or scheme_l.startswith("postgresql+"):
        if scheme_l == "postgresql+psycopg2":
            return raw
        return f"postgresql+psycopg2://{rest}"
    return raw


def _create_engine():
    url = settings.DATABASE_URL
    # Pytest + SQLite :memory:: um pool estático para todas as conexões verem o mesmo schema (#46).
    if os.environ.get("DX_CONNECT_TESTING") == "1" and url.startswith("sqlite"):
        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url_psycopg2(url), pool_pre_ping=True)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
