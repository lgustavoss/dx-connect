from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PresencaSetorResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class PresencaOnlineItem(BaseModel):
    atendente_id: int
    nome: str
    email: str
    role: str
    online_desde: datetime
    setores: list[PresencaSetorResumo] = []


class PresencaOnlineLista(BaseModel):
    itens: list[PresencaOnlineItem]
