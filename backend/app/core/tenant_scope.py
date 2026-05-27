"""Filtros de isolamento por tenant nas queries."""

from sqlalchemy.orm import Query

from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.rede import Rede
from app.models.setor import Setor
from app.models.ticket import Ticket


def filtrar_tickets_por_tenant(q: Query, tenant_id: int) -> Query:
    return q.filter(Ticket.tenant_id == tenant_id)


def filtrar_empresas_por_tenant(q: Query, tenant_id: int) -> Query:
    return q.filter(Empresa.tenant_id == tenant_id)


def filtrar_redes_por_tenant(q: Query, tenant_id: int) -> Query:
    return q.filter(Rede.tenant_id == tenant_id)


def filtrar_setores_por_tenant(q: Query, tenant_id: int) -> Query:
    return q.filter(Setor.tenant_id == tenant_id)


def filtrar_atendentes_por_tenant(q: Query, tenant_id: int) -> Query:
    return q.filter(Atendente.tenant_id == tenant_id)
