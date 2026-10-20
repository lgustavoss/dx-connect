from datetime import datetime

from pydantic import BaseModel, Field


class RustdeskVinculoRead(BaseModel):
    empresa_id: int
    empresa_nome: str
    rede_id: int | None = None
    rede_nome: str = ""
    rotulo_nome: str = ""
    pdv_id: int
    pdv_codigo: str
    pdv_ativo: bool
    tipo_acesso_remoto_nome: str | None = None


class RustdeskPeerRead(BaseModel):
    rustdesk_id: str
    hostname: str | None = None
    username: str | None = None
    sistema: str | None = None
    ip: str | None = None
    last_seen: datetime | None = None
    online: bool | None = None
    vinculos: list[RustdeskVinculoRead]
    sem_vinculo: bool
    id_repetido: bool


class RustdeskPdvAusenteRead(RustdeskVinculoRead):
    acesso_remoto_id: str | None = None


class RustdeskListaRead(BaseModel):
    items: list[RustdeskPeerRead]
    total: int
    pdvs_nao_vistos: list[RustdeskPdvAusenteRead]
    monitoramento_online: bool
    agent_configurado: bool
    agent_indisponivel: bool
    sincronizado_em: datetime | None = None


class RustdeskVincularIn(BaseModel):
    pdv_id: int
    confirmar_substituicao: bool = False


class RustdeskVincularOut(RustdeskVinculoRead):
    acesso_remoto_id: str = Field(min_length=1)


class RustdeskDesvincularIn(BaseModel):
    pdv_id: int


class RustdeskDesvincularOut(BaseModel):
    pdv_id: int
    acesso_remoto_id: str | None = None


class RustdeskExcluirOut(BaseModel):
    rustdesk_id: str
    removido: bool = True


class RustdeskConfiguracaoRead(BaseModel):
    configurado: bool
    servidor_id: str = ""
    servidor_relay: str = ""
    chave: str = ""
