from pydantic import BaseModel, Field


class NotificacaoPreferenciasRead(BaseModel):
    email_habilitado: bool = True
    email_ticket_atribuido: bool = True
    email_nova_mensagem: bool = True
    email_sla_em_risco: bool = True
    email_sla_violado: bool = True
    push_habilitado: bool = False
    push_fila: bool = True


class NotificacaoPreferenciasUpdate(BaseModel):
    email_habilitado: bool | None = None
    email_ticket_atribuido: bool | None = None
    email_nova_mensagem: bool | None = None
    email_sla_em_risco: bool | None = None
    email_sla_violado: bool | None = None
    push_habilitado: bool | None = None
    push_fila: bool | None = None
