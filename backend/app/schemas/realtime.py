from typing import Any

from pydantic import BaseModel, Field


class RealtimeEventEnvelope(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
