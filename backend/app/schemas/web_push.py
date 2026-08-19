from pydantic import BaseModel, Field


class PushSubscriptionCreate(BaseModel):
    endpoint: str = Field(min_length=8, max_length=2048)
    p256dh: str = Field(min_length=8, max_length=255)
    auth: str = Field(min_length=8, max_length=255)
    user_agent: str | None = Field(default=None, max_length=512)


class PushSubscriptionRead(BaseModel):
    id: int
    endpoint: str
    user_agent: str | None = None

    model_config = {"from_attributes": True}


class PushVapidPublic(BaseModel):
    configurado: bool
    public_key: str | None = None
