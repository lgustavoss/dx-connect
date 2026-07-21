from typing import Any

from pydantic import BaseModel, Field, field_validator


class WhatsappSettingsRead(BaseModel):
    evolution_base_url: str | None = None
    evolution_instance_name: str | None = None
    has_api_key: bool = False
    has_webhook_secret: bool = False
    evolution_embutida_disponivel: bool = False
    auto_msg_espera_ativa: bool = True
    auto_msg_espera_texto: str | None = None
    auto_msg_assumido_ativa: bool = True
    auto_msg_assumido_texto: str | None = None
    auto_msg_encerrado_ativa: bool = True
    auto_msg_encerrado_texto: str | None = None
    auto_msg_fora_horario_ativa: bool = True
    auto_msg_fora_horario_texto: str | None = None
    horario_inicio: str | None = None
    horario_fim: str | None = None
    horario_timezone: str = "America/Sao_Paulo"
    horario_semana: dict[str, Any] | None = None
    usar_feriados_nacionais: bool = False
    nome_empresa_exibicao: str | None = None
    inativ_encerramento_ativa: bool = False
    inativ_aviso_minutos: int | None = None
    inativ_encerramento_apos_aviso_minutos: int | None = None
    auto_msg_inativ_aviso_ativa: bool = True
    auto_msg_inativ_aviso_texto: str | None = None
    avaliacao_ativa: bool = False
    avaliacao_janela_minutos: int = 30
    auto_msg_avaliacao_ativa: bool = True
    auto_msg_avaliacao_texto: str | None = None
    auto_msg_avaliacao_obrigado_texto: str | None = None
    auto_msg_avaliacao_timeout_texto: str | None = None
    auto_msg_avaliacao_pular_texto: str | None = None

    model_config = {"from_attributes": True}


class WhatsappSettingsUpdate(BaseModel):
    evolution_base_url: str | None = None
    evolution_instance_name: str | None = None
    evolution_api_key: str | None = Field(None, description="Nova API key; omitir para manter.")
    webhook_secret: str | None = Field(None, description="Novo segredo; omitir para manter.")
    auto_msg_espera_ativa: bool | None = None
    auto_msg_espera_texto: str | None = None
    auto_msg_assumido_ativa: bool | None = None
    auto_msg_assumido_texto: str | None = None
    auto_msg_encerrado_ativa: bool | None = None
    auto_msg_encerrado_texto: str | None = None
    auto_msg_fora_horario_ativa: bool | None = None
    auto_msg_fora_horario_texto: str | None = None
    horario_inicio: str | None = None
    horario_fim: str | None = None
    horario_timezone: str | None = None
    horario_semana: dict[str, Any] | None = None
    usar_feriados_nacionais: bool | None = None
    nome_empresa_exibicao: str | None = None
    inativ_encerramento_ativa: bool | None = None
    inativ_aviso_minutos: int | None = Field(None, ge=1, le=24 * 60)
    inativ_encerramento_apos_aviso_minutos: int | None = Field(None, ge=1, le=24 * 60)
    auto_msg_inativ_aviso_ativa: bool | None = None
    auto_msg_inativ_aviso_texto: str | None = None
    avaliacao_ativa: bool | None = None
    avaliacao_janela_minutos: int | None = Field(None, ge=1, le=24 * 60)
    auto_msg_avaliacao_ativa: bool | None = None
    auto_msg_avaliacao_texto: str | None = None
    auto_msg_avaliacao_obrigado_texto: str | None = None
    auto_msg_avaliacao_timeout_texto: str | None = None
    auto_msg_avaliacao_pular_texto: str | None = None

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
