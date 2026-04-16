from pydantic import BaseModel, ConfigDict
from datetime import datetime


class AuditLogRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    atendente_id: int | None
    atendente_nome: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
