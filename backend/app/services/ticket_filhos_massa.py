"""Abertura de tickets filhos em massa por empresa da rede (#117)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.rede import Rede
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketMensagem
from app.services.protocolo_mensal import gerar_protocolo_ticket
from app.services.ticket_escopo import rede_id_efetivo_ticket

MAX_FILHOS_MASSA = 100


@dataclass(frozen=True)
class EmpresaFilhoMassaOpcao:
    id: int
    nome: str
    ja_tem_filho: bool


def _rede_id_do_ticket(db: Session, ticket: Ticket) -> int:
    rede_id = rede_id_efetivo_ticket(db, ticket)
    if rede_id is None:
        raise ValueError("O ticket pai precisa ter rede definida para abrir filhos em massa.")
    return rede_id


def listar_opcoes_filhos_massa(db: Session, parent: Ticket) -> tuple[int, str | None, list[EmpresaFilhoMassaOpcao]]:
    rede_id = _rede_id_do_ticket(db, parent)
    rede_nome = None
    if parent.rede is not None:
        rede_nome = parent.rede.nome
    elif parent.empresa is not None and parent.empresa.rede is not None:
        rede_nome = parent.empresa.rede.nome
    else:
        rede = db.query(Rede).filter(Rede.id == rede_id, Rede.tenant_id == parent.tenant_id).first()
        rede_nome = rede.nome if rede else None

    empresas = (
        db.query(Empresa)
        .filter(
            Empresa.tenant_id == parent.tenant_id,
            Empresa.rede_id == rede_id,
            Empresa.ativo.is_(True),
        )
        .order_by(Empresa.nome.asc(), Empresa.id.asc())
        .all()
    )
    com_filho = {
        eid
        for (eid,) in db.query(Ticket.empresa_id)
        .filter(Ticket.parent_ticket_id == parent.id, Ticket.empresa_id.isnot(None))
        .all()
        if eid is not None
    }
    opcoes = [EmpresaFilhoMassaOpcao(id=e.id, nome=e.nome, ja_tem_filho=e.id in com_filho) for e in empresas]
    return rede_id, rede_nome, opcoes


def criar_filhos_em_massa(
    db: Session,
    *,
    parent: Ticket,
    atendente: Atendente,
    empresa_ids: list[int],
    assunto: str,
    descricao: str | None,
    setor_id: int,
) -> list[Ticket]:
    if not empresa_ids:
        raise ValueError("Selecione ao menos uma empresa.")
    if len(empresa_ids) > MAX_FILHOS_MASSA:
        raise ValueError(f"Máximo de {MAX_FILHOS_MASSA} tickets filhos por operação.")

    rede_id = _rede_id_do_ticket(db, parent)
    ids_unicos = list(dict.fromkeys(empresa_ids))
    if len(ids_unicos) != len(empresa_ids):
        raise ValueError("Lista de empresas contém duplicatas.")

    empresas = (
        db.query(Empresa)
        .filter(
            Empresa.id.in_(ids_unicos),
            Empresa.tenant_id == parent.tenant_id,
            Empresa.rede_id == rede_id,
            Empresa.ativo.is_(True),
        )
        .all()
    )
    if len(empresas) != len(ids_unicos):
        raise ValueError("Uma ou mais empresas são inválidas ou não pertencem à rede do ticket pai.")

    com_filho = {
        eid
        for (eid,) in db.query(Ticket.empresa_id)
        .filter(Ticket.parent_ticket_id == parent.id, Ticket.empresa_id.isnot(None))
        .all()
        if eid is not None
    }
    for e in empresas:
        if e.id in com_filho:
            raise ValueError(f"Já existe ticket filho para a empresa «{e.nome}».")

    status_inicial = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    if not status_inicial:
        raise ValueError("Cadastre ao menos um status de ticket ativo.")

    corpo = (descricao or "").strip() or "—"
    criados: list[Ticket] = []
    for empresa in sorted(empresas, key=lambda x: x.nome.lower()):
        ticket = Ticket(
            tenant_id=parent.tenant_id,
            protocolo=gerar_protocolo_ticket(db),
            empresa_id=empresa.id,
            rede_id=empresa.rede_id,
            setor_id=setor_id,
            status_id=status_inicial.id,
            assunto=assunto.strip(),
            descricao=descricao,
            parent_ticket_id=parent.id,
        )
        db.add(ticket)
        db.flush()
        from app.services.sla_policy import aplicar_sla_snapshot_ao_ticket

        aplicar_sla_snapshot_ao_ticket(db, ticket)
        from app.services.sla_calculo import registrar_primeira_resposta_se_necessario

        registrar_primeira_resposta_se_necessario(db, ticket)
        db.add(
            TicketMensagem(
                ticket_id=ticket.id,
                atendente_id=atendente.id,
                tipo="abertura",
                corpo=corpo,
            )
        )
        criados.append(ticket)
    return criados
