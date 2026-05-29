"""Filtros de isolamento por tenant nas queries (relevantes sobretudo em modo multi-tenant)."""

from sqlalchemy.orm import Query

from app.core.tenant_context import effective_tenant_id
from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.rede import Rede
from app.models.setor import Setor
from app.models.ticket import Ticket


def _tenant_filter_value(tenant_id: int | None) -> int:
    if tenant_id is not None:
        return tenant_id
    return effective_tenant_id()


def filtrar_tickets_por_tenant(q: Query, tenant_id: int | None = None) -> Query:
    tid = _tenant_filter_value(tenant_id)
    return q.filter(Ticket.tenant_id == tid)


def filtrar_empresas_por_tenant(q: Query, tenant_id: int | None = None) -> Query:
    tid = _tenant_filter_value(tenant_id)
    return q.filter(Empresa.tenant_id == tid)


def filtrar_redes_por_tenant(q: Query, tenant_id: int | None = None) -> Query:
    tid = _tenant_filter_value(tenant_id)
    return q.filter(Rede.tenant_id == tid)


def filtrar_setores_por_tenant(q: Query, tenant_id: int | None = None) -> Query:
    tid = _tenant_filter_value(tenant_id)
    return q.filter(Setor.tenant_id == tid)


def filtrar_atendentes_por_tenant(q: Query, tenant_id: int | None = None) -> Query:
    tid = _tenant_filter_value(tenant_id)
    return q.filter(Atendente.tenant_id == tid)
