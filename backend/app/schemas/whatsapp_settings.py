from typing import Any

from pydantic import BaseModel, Field, field_validator


class WhatsappSettingsRead(BaseModel):
    evolution_base_url: str | None = None
    evolution_instance_name: str | None = None
    has_api_key: bool = False
    has_webhook_secret: bool = False
    evolution_embutida_disponivel: bool = False

    model_config = {"from_attributes": True}


class WhatsappSettingsUpdate(BaseModel):
    evolution_base_url: str | None = None
    evolution_instance_name: str | None = None
    evolution_api_key: str | None = Field(None, description="Nova API key; omitir para manter.")
    webhook_secret: str | None = Field(None, description="Novo segredo; omitir para manter.")

    @field_validator("evolution_base_url", mode="before")
    @classmethod
    def strip_base(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s or None


class WhatsappTesteConexaoResultado(BaseModel):
    ok: bool
    detalhe: str | None = None


class WhatsappProvisionEmbutidoResponse(BaseModel):
    instance: str
    webhook_url: str
    qrcode: dict[str, Any] | None = None
    connect_http_status: int | None = None
    connect_erro: str | None = None
