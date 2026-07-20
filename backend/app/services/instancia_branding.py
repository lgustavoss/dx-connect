"""Branding white-label da instância — KB pública (/kb) e portal do cliente (/portal)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.empresa_sistema import EmpresaSistema
from app.models.kb import KbPortalSettings
from app.schemas.kb import KbPublicBrandingRead
from app.schemas.portal import PortalPublicBrandingRead

DEFAULT_COR_PRIMARIA = "#0D9488"
DEFAULT_COR_HEADER = "#0B2D4A"
DEFAULT_COR_TEXTO_HEADER = "#FFFFFF"
DEFAULT_COR_TEXTO_CORPO = "#0F172A"
DEFAULT_COR_FUNDO = "#F8FAFC"
TEXTO_BOAS_VINDAS_PORTAL_PADRAO = (
    "Acompanhe e abra chamados da sua empresa com a equipe de suporte."
)


def empresa_sistema_row(db: Session) -> EmpresaSistema | None:
    return db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()


def portal_settings_row(db: Session, tenant_id: int) -> KbPortalSettings | None:
    return db.query(KbPortalSettings).filter(KbPortalSettings.tenant_id == tenant_id).first()


def nome_exibicao_empresa(row: EmpresaSistema | None) -> str:
    if not row:
        return "Central de ajuda"
    for attr in ("nome_fantasia", "nome", "razao_social"):
        val = getattr(row, attr, None)
        if val and str(val).strip():
            return str(val).strip()
    return "Central de ajuda"


def logo_url_publica(row: EmpresaSistema | None) -> str | None:
    if row and row.logo_filename and str(row.logo_filename).strip():
        return "/v1/kb/public/logo"
    return None


def _cores_branding(settings: KbPortalSettings | None) -> dict[str, str]:
    cor_primaria = (settings.cor_primaria if settings else None) or DEFAULT_COR_PRIMARIA
    cor_link = (settings.cor_link if settings and settings.cor_link else None) or cor_primaria
    cor_header = (settings.cor_header if settings else None) or DEFAULT_COR_HEADER
    # Menu lateral: cor própria ou mesma da navbar
    cor_sidebar = None
    if settings and settings.cor_sidebar and str(settings.cor_sidebar).strip():
        cor_sidebar = str(settings.cor_sidebar).strip()
    return {
        "cor_primaria": cor_primaria,
        "cor_header": cor_header,
        "cor_sidebar": cor_sidebar or cor_header,
        "cor_texto_header": (settings.cor_texto_header if settings else None) or DEFAULT_COR_TEXTO_HEADER,
        "cor_texto_corpo": (settings.cor_texto_corpo if settings else None) or DEFAULT_COR_TEXTO_CORPO,
        "cor_fundo": (settings.cor_fundo if settings else None) or DEFAULT_COR_FUNDO,
        "cor_link": cor_link,
    }


def branding_kb_publico(db: Session, tenant_id: int) -> KbPublicBrandingRead:
    row = empresa_sistema_row(db)
    settings = portal_settings_row(db, tenant_id)
    nome = nome_exibicao_empresa(row)
    cores = _cores_branding(settings)
    titulo_custom = (settings.portal_titulo or "").strip() if settings else ""
    if titulo_custom:
        portal_titulo = titulo_custom
    elif nome != "Central de ajuda":
        portal_titulo = f"Central de ajuda — {nome}"
    else:
        portal_titulo = "Central de ajuda"
    return KbPublicBrandingRead(
        nome_exibicao=nome,
        portal_titulo=portal_titulo,
        logo_url=logo_url_publica(row),
        texto_boas_vindas=settings.texto_boas_vindas if settings else None,
        exibir_marca_deskrudder=bool(settings.exibir_marca_deskrudder) if settings else True,
        feedback_habilitado=bool(settings.feedback_habilitado) if settings else True,
        chat_habilitado=bool(settings.chat_habilitado) if settings else False,
        **cores,
    )


def _titulo_portal_cliente(nome: str) -> str:
    """Título exibido no /portal — independente do `portal_titulo` da central /kb."""
    if nome != "Central de ajuda":
        return f"Portal — {nome}"
    return "Portal do cliente"


def branding_portal_cliente(db: Session, tenant_id: int) -> PortalPublicBrandingRead:
    row = empresa_sistema_row(db)
    settings = portal_settings_row(db, tenant_id)
    nome = nome_exibicao_empresa(row)
    cores = _cores_branding(settings)
    portal_titulo = _titulo_portal_cliente(nome)
    texto = (settings.texto_boas_vindas or "").strip() if settings else ""
    return PortalPublicBrandingRead(
        nome_exibicao=nome,
        portal_titulo=portal_titulo,
        logo_url=logo_url_publica(row),
        texto_boas_vindas=texto or TEXTO_BOAS_VINDAS_PORTAL_PADRAO,
        exibir_marca_deskrudder=bool(settings.exibir_marca_deskrudder) if settings else True,
        chat_habilitado=bool(settings.chat_habilitado) if settings else False,
        **cores,
    )
