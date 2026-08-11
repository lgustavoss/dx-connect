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

    # Mídia do chat interno (#495).
    CHAT_INTERNO_MEDIA_DIR: str = "data/chat_interno_media"
    CHAT_INTERNO_MEDIA_MAX_BYTES: int = 25 * 1024 * 1024

    # Mensagem pública com notificação por e-mail (#140): janela antes do envio e TTL do lock de edição.
    TICKET_MENSAGEM_EMAIL_GRACE_SECONDS: int = 120
    TICKET_MENSAGEM_EDIT_LOCK_TTL_SECONDS: int = 300
    TICKET_MENSAGEM_EMAIL_WORKER_INTERVAL_SECONDS: int = 5
    NOTIFICACAO_EMAIL_DEBOUNCE_MINUTES: int = 5
    NOTIFICACAO_EMAIL_WORKER_INTERVAL_SECONDS: int = 10
    WEBHOOK_OUTBOX_WORKER_INTERVAL_SECONDS: int = 15
    # Webhook de saída ao fechar ticket (#119). URL vazia = desligado.
    TICKET_CLOSED_WEBHOOK_URL: str | None = None
    TICKET_CLOSED_WEBHOOK_SECRET: str | None = None
    # Tentativas HTTP para Evolution API (falhas transitórias).
    EVOLUTION_HTTP_MAX_ATTEMPTS: int = 3
    WHATSAPP_INACTIVITY_WORKER_INTERVAL_SECONDS: int = 60
    TICKET_DISTRIBUICAO_WORKER_INTERVAL_SECONDS: int = 45
    SLA_WORKER_INTERVAL_SECONDS: int = 60

    # Control-plane comercial DeskRudder (painel de licenças / SaaS).
    # True só na instância deskrudder.com.br — False nas instâncias dos clientes.
    SAAS_CONTROL_PLANE: bool = False
    # Trial público (DR-07): dias até data_renovacao ao criar trial.
    SAAS_TRIAL_DAYS: int = 14
    # Renovações (DR-08): janela de alerta antes do vencimento.
    SAAS_RENEWAL_ALERT_DAYS_BEFORE: int = 14
    SAAS_RENEWAL_WORKER_INTERVAL_SECONDS: int = 3600
    # Provisionamento (DR-04): worker + execução opcional dos scripts do host.
    SAAS_PROVISION_WORKER_INTERVAL_SECONDS: int = 30
    SAAS_PROVISION_EXEC_ENABLED: bool = False
    # Domínio base dos clientes (ex.: deskrudder.com.br → slug.deskrudder.com.br).
    SAAS_PROVISION_BASE_DOMAIN: str | None = None
    SAAS_PROVISION_API_PORT_START: int = 8001
    # Caixa da equipe comercial DeskRudder (trial, provisionamento, renovação).
    SAAS_NOTIFY_EMAIL: str | None = None
    # Raiz do repositório no host (para provision-client.sh). Vazio = parents do pacote app.
    SAAS_REPO_ROOT: str | None = None
    # Módulos comerciais activos nesta instância (códigos separados por vírgula, ex.: helpdesk,whatsapp).
    # Preenchido no client.env pelo provisionamento a partir do plano da licença.
    SAAS_MODULOS: str = "helpdesk"
    # Modo legado: vários clientes no mesmo Postgres (subdomínio numérico + coluna tenant_id).
    # Produção comercial: manter False (um Postgres por cliente / deploy).
    DX_CONNECT_MULTI_TENANT: bool = False
    # URL pública do painel em single-tenant (ex.: cliente01.deskrudder.com.br).
    # Se vazio, GET /tenant/atual usa {tenant_id}.CONNECT_APP_BASE_DOMAIN só em multi-tenant.
    CLIENT_APP_HOST: str | None = None
    # Validade do link de redefinição de senha (#105).
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    # Multi-tenant legado: subdomínio {tenant_id}.CONNECT_APP_BASE_DOMAIN e endereços {local}@INBOUND_EMAIL_DOMAIN
    CONNECT_APP_BASE_DOMAIN: str = "deskrudder.com.br"
    # Domínio Resend com Receiving (ex.: notify.deskrudder.com.br). Endereços: {setor}.t{tenant}@domínio.
    INBOUND_EMAIL_DOMAIN: str = "notify.deskrudder.com.br"
    # Host sem subdomínio (ex.: deskrudder.com.br) ou dev local sem header.
    DEFAULT_TENANT_ID: int = 1

    # Webhook de ingestão de e-mail (padrão SaaS). Sem segredo, o endpoint responde 503.
    EMAIL_INBOUND_WEBHOOK_SECRET: str | None = None
    # Fallback se o destinatário não corresponder a tenant_inbound_addresses (legado).
    EMAIL_INBOUND_DEFAULT_EMPRESA_ID: int | None = None
    EMAIL_INBOUND_DEFAULT_SETOR_ID: int | None = None

    # Resend (envio transaccional HTTP). Opcional: sobrepõe ausência de API key na BD (útil em dev/CI).
    RESEND_API_KEY: str | None = None
    # Segredo Svix do webhook Resend (evento email.received → /v1/webhooks/resend-inbound).
    RESEND_WEBHOOK_SECRET: str | None = None
    TRANSACTIONAL_FROM_EMAIL: str | None = None
    TRANSACTIONAL_FROM_NAME: str | None = None
    # Respostas ao cliente: Reply-To público (ex. suporte@suaempresa.com.br) enquanto From usa @notify na Resend.
    SUPPORT_REPLY_TO_EMAIL: str | None = None

    # Diretório para logo da empresa do sistema (caminho relativo ao cwd ou absoluto).
    SYSTEM_LOGO_DIR: str = "data/system_logo"
    # Tamanho máximo (bytes) para upload de logo (2MB).
    SYSTEM_LOGO_MAX_BYTES: int = 2 * 1024 * 1024

    # Imagens inline nos artigos da base de conhecimento (#294).
    KB_MEDIA_DIR: str = "data/kb_media"
    KB_MEDIA_MAX_BYTES: int = 2 * 1024 * 1024

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
            if self.DX_CONNECT_MULTI_TENANT:
                raise ValueError(
                    "DX_CONNECT_MULTI_TENANT não é suportado em produção. "
                    "Use um deploy (Postgres + API) por cliente — ver docs/DEPLOYMENT_ARCHITECTURE.md."
                )
        return self

    @property
    def single_tenant_mode(self) -> bool:
        return not self.DX_CONNECT_MULTI_TENANT

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
