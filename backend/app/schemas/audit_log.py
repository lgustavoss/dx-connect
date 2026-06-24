from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any


class AuditLogRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    atendente_id: int | None
    atendente_nome: str | None = None
    payload_json: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
