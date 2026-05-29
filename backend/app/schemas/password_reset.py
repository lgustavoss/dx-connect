from pydantic import BaseModel, Field


class SolicitarRedefinicaoSenha(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class RedefinirSenhaComToken(BaseModel):
    token: str = Field(..., min_length=16, max_length=512)
    senha_nova: str = Field(..., min_length=8, max_length=128)


class MensagemAuth(BaseModel):
    detail: str
