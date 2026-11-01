from pydantic import BaseModel, Field


class DispositivoCreate(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    plataforma: str = Field(default="android", max_length=32)


class DispositivoRead(BaseModel):
    id: int
    token: str
    plataforma: str

    model_config = {"from_attributes": True}
