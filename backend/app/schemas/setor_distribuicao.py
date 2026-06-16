from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.distribuicao_ticket import DistribuicaoEstrategia, DistribuicaoModo


class SetorDistribuicaoRead(BaseModel):
    modo: DistribuicaoModo = DistribuicaoModo.manual
    timeout_minutos: int = 30
    estrategia: DistribuicaoEstrategia = DistribuicaoEstrategia.round_robin
    atendentes_elegiveis: list[int] | None = None

    model_config = ConfigDict(from_attributes=True)


class SetorDistribuicaoUpdate(BaseModel):
    modo: DistribuicaoModo
    timeout_minutos: int = Field(default=30, ge=1, le=24 * 60)
    estrategia: DistribuicaoEstrategia = DistribuicaoEstrategia.round_robin
    atendentes_elegiveis: list[int] | None = None

    @field_validator("atendentes_elegiveis")
    @classmethod
    def deduplicar_elegiveis(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        seen: set[int] = set()
        out: list[int] = []
        for i in v:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out
