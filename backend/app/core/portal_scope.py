"""Escopo de dados do portal do cliente (funcionário da rede).

RBAC por papel (#604):
- colaborador: tickets/chats **próprios** (aberto_por / contacto vinculado)
- supervisor: tickets/chats das **empresas vinculadas**
- sócio: tudo da **rede**

Ver também `docs/PORTAL_CLIENTE.md`.
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede
from app.models.ticket import Ticket
from app.services.funcionario_escopo import empresa_ids_vinculados, escopo_efetivo, rede_id_efetiva

TiposPortal = frozenset({"colaborador", "supervisor", "socio"})


def tipo_portal(funcionario: FuncionarioRede) -> str:
    t = (funcionario.tipo or "colaborador").strip().lower()
    return t if t in TiposPortal else "colaborador"


def empresa_ids_visiveis(db: Session, funcionario: FuncionarioRede) -> set[int]:
    return empresa_ids_vinculados(db, funcionario, apenas_ativas=True)


def _ticket_empresa_rede_visivel(db: Session, funcionario: FuncionarioRede, ticket: Ticket) -> bool:
    """Empresa/rede do ticket dentro do vínculo do funcionário (sem filtro de autor)."""
    rede_id = rede_id_efetiva(db, funcionario)
    if rede_id is None:
        return False
    if ticket.rede_id is not None and int(ticket.rede_id) != int(rede_id):
        if ticket.empresa_id is None:
            return False
    ids = empresa_ids_visiveis(db, funcionario)
    if ticket.empresa_id is not None:
        return int(ticket.empresa_id) in ids
    if ticket.rede_id is not None and int(ticket.rede_id) == int(rede_id):
        return escopo_efetivo(funcionario) == "all"
    return False


def ticket_no_escopo(db: Session, funcionario: FuncionarioRede, ticket: Ticket) -> bool:
    if not _ticket_empresa_rede_visivel(db, funcionario, ticket):
        return False
    if tipo_portal(funcionario) == "colaborador":
        ap = ticket.aberto_por_id
        return ap is not None and int(ap) == int(funcionario.id)
    return True


def filtro_query_tickets_portal(query: Query, db: Session, funcionario: FuncionarioRede) -> Query | None:
    """Aplica escopo RBAC à query de tickets. Retorna None se a listagem deve ser vazia."""
    ids = empresa_ids_visiveis(db, funcionario)
    rede_id = rede_id_efetiva(db, funcionario)
    filtros = []
    if ids:
        filtros.append(Ticket.empresa_id.in_(ids))
    if rede_id is not None and escopo_efetivo(funcionario) == "all":
        filtros.append((Ticket.empresa_id.is_(None)) & (Ticket.rede_id == rede_id))
    if not filtros:
        return None
    query = query.filter(or_(*filtros))
    if tipo_portal(funcionario) == "colaborador":
        query = query.filter(Ticket.aberto_por_id == funcionario.id)
    return query


def chat_no_escopo(db: Session, funcionario: FuncionarioRede, chat) -> bool:
    """Escopo de chats WhatsApp no portal (#604; API em #603)."""
    from app.models.whatsapp_chat import WhatsappChat

    if not isinstance(chat, WhatsappChat):
        return False
    rede_id = rede_id_efetiva(db, funcionario)
    if rede_id is None:
        return False
    if chat.empresa_id is None:
        return tipo_portal(funcionario) == "socio" and escopo_efetivo(funcionario) == "all"
    emp = db.query(Empresa).filter(Empresa.id == chat.empresa_id).first()
    if not emp or int(emp.rede_id) != int(rede_id):
        return False
    papel = tipo_portal(funcionario)
    if papel == "colaborador":
        fid = chat.funcionario_rede_id
        return fid is not None and int(fid) == int(funcionario.id)
    if papel == "supervisor":
        return int(chat.empresa_id) in empresa_ids_visiveis(db, funcionario)
    return True


def filtro_query_chats_portal(query: Query, db: Session, funcionario: FuncionarioRede) -> Query | None:
    """Filtro SQLAlchemy para listagem de chats no portal (#603)."""
    from app.models.whatsapp_chat import WhatsappChat

    ids = empresa_ids_visiveis(db, funcionario)
    rede_id = rede_id_efetiva(db, funcionario)
    if rede_id is None:
        return None
    papel = tipo_portal(funcionario)
    if papel == "colaborador":
        return query.filter(WhatsappChat.funcionario_rede_id == funcionario.id)
    if papel == "supervisor":
        if not ids:
            return None
        return query.filter(WhatsappChat.empresa_id.in_(ids))
    rede_empresa_ids = db.query(Empresa.id).filter(Empresa.rede_id == rede_id)
    return query.filter(
        or_(
            WhatsappChat.empresa_id.in_(rede_empresa_ids),
            WhatsappChat.empresa_id.is_(None),
        )
    )


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
