import re
from typing import Literal

from pydantic import EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "production"] = "development"
    # Equivalente ao DEBUG do Django: use False em produção (validado em validate_production).
    DEBUG: bool = False
    DATABASE_URL: str
    SECRET_KEY: str = Field(
        ...,
        min_length=16,
        description="Chave JWT; em produção use 32+ caracteres aleatórios (ex.: openssl rand -hex 32).",
    )
    ALGORITHM: str = "HS256"
    # Em produção o validador exige no máximo 30 (sessão curta; mitiga vazamento de token).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Origens CORS separadas por vírgula (ex.: https://app.exemplo.com,https://www.exemplo.com)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    LOG_LEVEL: str = "INFO"
    # Cache de municípios (IBGE): intervalo entre verificações em background e idade máxima antes de re-sync completo.
    IBGE_MUNICIPIOS_SYNC_INTERVAL_SECONDS: int = 86400
    IBGE_MUNICIPIOS_MAX_AGE_HOURS: int = 168
    # Seed em produção: só cria o primeiro admin se AMBOS estiverem definidos (senha mín. 8 caracteres).
    # Sem SEED_ADMIN_EMAIL, nenhum admin é criado automaticamente em produção.
    SEED_ADMIN_EMAIL: EmailStr | None = None
    SEED_ADMIN_PASSWORD: str | None = None
    # Hostnames permitidos no header Host (TrustedHostMiddleware). Em produção não use "*".
    # Ex.: api.seudominio.com,127.0.0.1
    ALLOWED_HOSTS: str = "*"
    # Evolution API no mesmo Docker Compose (opcional): o backend cria instância + webhook e expõe QR no painel.
    EVOLUTION_INTERNAL_BASE_URL: str | None = None
    EVOLUTION_GLOBAL_API_KEY: str | None = None
    WHATSAPP_EMBEDDED_INSTANCE_NAME: str = "dxconnect"
    # URL base que a Evolution deve usar para POST no webhook do DX Connect (hostname Docker = nome do serviço).
    DX_CONNECT_WEBHOOK_BASE_URL: str | None = None
    # Diretório para ficheiros de mídia WhatsApp (caminho relativo ao cwd ou absoluto). Em Docker: mapear volume em /app/data.
    WHATSAPP_MEDIA_DIR: str = "data/whatsapp_media"
    # Tamanho máximo (bytes) ao descodificar base64 da Evolution antes de gravar em disco.
    WHATSAPP_MEDIA_MAX_BYTES: int = 25 * 1024 * 1024

    # Diretório para anexos de tickets (caminho relativo ao cwd ou absoluto). Em Docker: mapear volume em /app/data.
    TICKET_ANEXOS_DIR: str = "data/ticket_anexos"
    # Tamanho máximo (bytes) para cada anexo de ticket.
    TICKET_ANEXOS_MAX_BYTES: int = 25 * 1024 * 1024

    @property
    def evolution_embutida_disponivel(self) -> bool:
        return bool(
            (self.EVOLUTION_INTERNAL_BASE_URL or "").strip()
            and (self.EVOLUTION_GLOBAL_API_KEY or "").strip()
        )

    @field_validator("SEED_ADMIN_EMAIL", mode="before")
    @classmethod
    def normalize_seed_admin_email(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("CORS_ORIGINS")
    @classmethod
    def strip_cors(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_production(self):
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG não pode ser True quando ENVIRONMENT=production")
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY deve ter ao menos 32 caracteres quando ENVIRONMENT=production"
                )
            if not self.CORS_ORIGINS or self.cors_origins_list() == []:
                raise ValueError(
                    "CORS_ORIGINS deve listar ao menos a origem HTTPS do frontend em produção"
                )
            if self.ACCESS_TOKEN_EXPIRE_MINUTES > 30:
                raise ValueError(
                    "Em produção ACCESS_TOKEN_EXPIRE_MINUTES deve ser no máximo 30 (política de sessão curta)."
                )
            hosts = self.allowed_hosts_list()
            if not hosts or hosts == ["*"]:
                raise ValueError(
                    "Em produção defina ALLOWED_HOSTS com os hostnames que o Nginx/proxy usa "
                    "(ex.: api.seudominio.com,127.0.0.1), não *."
                )
            if not _database_url_exige_ssl(self.DATABASE_URL):
                raise ValueError(
                    "Em produção DATABASE_URL (PostgreSQL) deve exigir TLS "
                    "(ex.: ?sslmode=require ou sslmode=verify-full na URL)."
                )
        return self

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


def _database_url_exige_ssl(database_url: str) -> bool:
    """True se a URL PostgreSQL indica TLS (sslmode ou ssl=true na query)."""
    u = database_url.strip().lower()
    if not u.startswith(("postgresql://", "postgres://")):
        return False
    if "sslmode=require" in u or "sslmode=verify-full" in u or "sslmode=verify-ca" in u:
        return True
    if re.search(r"[&?]ssl=true\b", u):
        return True
    return False


settings = Settings()
