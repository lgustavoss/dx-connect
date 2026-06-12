from pydantic import BaseModel, Field


class NotificacaoPreferenciasRead(BaseModel):
    email_habilitado: bool = True
    email_ticket_atribuido: bool = True
    email_nova_mensagem: bool = True


class NotificacaoPreferenciasUpdate(BaseModel):
    email_habilitado: bool | None = None
    email_ticket_atribuido: bool | None = None
    email_nova_mensagem: bool | None = None
