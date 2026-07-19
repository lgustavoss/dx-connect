"""Escopo de dados do portal do cliente (funcionário da rede)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede
from app.models.ticket import Ticket
from app.services.funcionario_escopo import empresa_ids_vinculados, rede_id_efetiva


def empresa_ids_visiveis(db: Session, funcionario: FuncionarioRede) -> set[int]:
    return empresa_ids_vinculados(db, funcionario, apenas_ativas=True)


def ticket_no_escopo(db: Session, funcionario: FuncionarioRede, ticket: Ticket) -> bool:
    """Ticket visível se empresa está no escopo, ou (coordenação) rede sem empresa no escopo do sócio."""
    rede_id = rede_id_efetiva(db, funcionario)
    if rede_id is None:
        return False
    if ticket.rede_id is not None and int(ticket.rede_id) != int(rede_id):
        # Fallback: empresa do ticket pode estar na rede
        if ticket.empresa_id is None:
            return False
    ids = empresa_ids_visiveis(db, funcionario)
    if ticket.empresa_id is not None:
        return int(ticket.empresa_id) in ids
    # Ticket só com rede (coordenação): sócio/supervisor com escopo all da mesma rede
    if ticket.rede_id is not None and int(ticket.rede_id) == int(rede_id):
        from app.services.funcionario_escopo import escopo_efetivo

        return escopo_efetivo(funcionario) == "all"
    return False


def assert_empresa_no_escopo(db: Session, funcionario: FuncionarioRede, empresa_id: int) -> Empresa:
    emp = db.query(Empresa).filter(Empresa.id == empresa_id, Empresa.ativo.is_(True)).first()
    if not emp or int(empresa_id) not in empresa_ids_visiveis(db, funcionario):
        # 404 para não revelar existência fora do escopo
        raise LookupError("Empresa não encontrada")
    return emp


def tenant_id_do_funcionario(db: Session, funcionario: FuncionarioRede) -> int:
    rede_id = rede_id_efetiva(db, funcionario)
    if rede_id is not None:
        from app.models.rede import Rede

        rede = db.query(Rede).filter(Rede.id == rede_id).first()
        if rede is not None:
            return int(rede.tenant_id)
    ids = empresa_ids_visiveis(db, funcionario)
    if ids:
        emp = db.query(Empresa).filter(Empresa.id == next(iter(ids))).first()
        if emp is not None:
            return int(emp.tenant_id)
    from app.core.tenant_context import effective_tenant_id

    return int(effective_tenant_id())
