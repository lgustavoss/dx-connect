"""Token Cursor MCP pessoal do saas_ops (#915)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SaasMcpTokenEstado(BaseModel):
    configurado: bool
    gerado_em: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SaasMcpTokenGerado(SaasMcpTokenEstado):
    """Plaintext só nesta resposta."""

    token: str
