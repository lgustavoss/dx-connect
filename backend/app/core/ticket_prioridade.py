import enum


class PrioridadeTicket(str, enum.Enum):
    baixa = "baixa"
    normal = "normal"
    alta = "alta"
    urgente = "urgente"


PRIORIDADES_TICKET = tuple(p.value for p in PrioridadeTicket)
