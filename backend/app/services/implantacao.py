"""Checklist de implantação: template admin + cópia no ticket (#325 / #358–#361)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import EmpresaPdv, Setor, StatusTicket, Ticket, TicketHistorico, TicketMensagem
from app.models.comercial_contrato import Contrato
from app.models.crm import CrmNegociacaoCnpjLinha
from app.models.empresa import Empresa
from app.models.implantacao_checklist import (
    CHAVE_CADASTRAR_PDVS,
    ITENS_PADRAO,
    ImplantacaoChecklistTemplate,
    ImplantacaoChecklistTemplateItem,
    TicketChecklistItem,
)
from app.models.atendente import Atendente
from app.schemas.implantacao import (
    ImplantacaoTemplateCreate,
    ImplantacaoTemplateItemIn,
    ImplantacaoTemplateUpdate,
    TicketChecklistItemPatch,
)
from app.services.protocolo_mensal import gerar_protocolo_ticket
from app.services.ticket_escopo import rede_id_de_empresa

CHAVE_PDVS = CHAVE_CADASTRAR_PDVS


def _setor_implantacao(db: Session, tenant_id: int, preferido_id: int | None) -> Setor | None:
    if preferido_id:
        row = (
            db.query(Setor)
            .filter(Setor.id == preferido_id, Setor.tenant_id == tenant_id, Setor.ativo.is_(True))
            .first()
        )
        if row:
            return row
    for slug in ("implantacao", "suporte"):
        row = (
            db.query(Setor)
            .filter(Setor.tenant_id == tenant_id, Setor.slug == slug, Setor.ativo.is_(True))
            .first()
        )
        if row:
            return row
    return (
        db.query(Setor)
        .filter(Setor.tenant_id == tenant_id, Setor.ativo.is_(True))
        .order_by(Setor.id.asc())
        .first()
    )


def _itens_read(row: ImplantacaoChecklistTemplate) -> list[dict]:
    itens = sorted(row.itens or [], key=lambda i: (i.ordem, i.id))
    return [
        {
            "id": i.id,
            "titulo": i.titulo,
            "descricao": i.descricao,
            "ordem": i.ordem,
            "obrigatorio": bool(i.obrigatorio),
            "chave": i.chave,
        }
        for i in itens
    ]


def template_para_read(row: ImplantacaoChecklistTemplate) -> dict:
    return {
        "id": row.id,
        "nome": row.nome,
        "versao": row.versao,
        "setor_id": row.setor_id,
        "setor_nome": row.setor.nome if row.setor else None,
        "ativo": bool(row.ativo),
        "itens": _itens_read(row),
    }


def _substituir_itens(
    db: Session,
    row: ImplantacaoChecklistTemplate,
    itens: list[ImplantacaoTemplateItemIn],
) -> None:
    row.itens.clear()
    db.flush()
    for i, item in enumerate(itens, start=1):
        chave = (item.chave or "").strip() or None
        db.add(
            ImplantacaoChecklistTemplateItem(
                template_id=row.id,
                titulo=item.titulo.strip(),
                descricao=(item.descricao or "").strip() or None,
                ordem=i,
                obrigatorio=item.obrigatorio,
                chave=chave,
            )
        )
    db.flush()


def garantir_template_padrao(db: Session, tenant_id: int) -> ImplantacaoChecklistTemplate:
    row = (
        db.query(ImplantacaoChecklistTemplate)
        .options(joinedload(ImplantacaoChecklistTemplate.itens), joinedload(ImplantacaoChecklistTemplate.setor))
        .order_by(ImplantacaoChecklistTemplate.id.asc())
        .first()
    )
    if row:
        return row
    setor = _setor_implantacao(db, tenant_id, None)
    row = ImplantacaoChecklistTemplate(
        nome="Implantação padrão",
        versao=1,
        setor_id=setor.id if setor else None,
        ativo=True,
    )
    db.add(row)
    db.flush()
    for i, (titulo, desc, obrig, chave) in enumerate(ITENS_PADRAO, start=1):
        db.add(
            ImplantacaoChecklistTemplateItem(
                template_id=row.id,
                titulo=titulo,
                descricao=desc,
                ordem=i,
                obrigatorio=obrig,
                chave=chave,
            )
        )
    db.flush()
    return (
        db.query(ImplantacaoChecklistTemplate)
        .options(joinedload(ImplantacaoChecklistTemplate.itens), joinedload(ImplantacaoChecklistTemplate.setor))
        .filter(ImplantacaoChecklistTemplate.id == row.id)
        .first()
    )


def listar_templates(db: Session, *, incluir_inativos: bool, tenant_id: int) -> list[ImplantacaoChecklistTemplate]:
    garantir_template_padrao(db, tenant_id)
    q = db.query(ImplantacaoChecklistTemplate).options(
        joinedload(ImplantacaoChecklistTemplate.itens),
        joinedload(ImplantacaoChecklistTemplate.setor),
    )
    if not incluir_inativos:
        q = q.filter(ImplantacaoChecklistTemplate.ativo.is_(True))
    return q.order_by(ImplantacaoChecklistTemplate.id.asc()).all()


def obter_template(db: Session, template_id: int, *, apenas_ativos: bool = True) -> ImplantacaoChecklistTemplate:
    q = db.query(ImplantacaoChecklistTemplate).options(
        joinedload(ImplantacaoChecklistTemplate.itens),
        joinedload(ImplantacaoChecklistTemplate.setor),
    ).filter(ImplantacaoChecklistTemplate.id == template_id)
    if apenas_ativos:
        q = q.filter(ImplantacaoChecklistTemplate.ativo.is_(True))
    row = q.first()
    if not row:
        raise HTTPException(status_code=404, detail="Modelo de checklist não encontrado.")
    return row


def criar_template(db: Session, data: ImplantacaoTemplateCreate, tenant_id: int) -> ImplantacaoChecklistTemplate:
    if data.setor_id is not None:
        setor = _setor_implantacao(db, tenant_id, data.setor_id)
        if setor is None or setor.id != data.setor_id:
            raise HTTPException(status_code=400, detail="Setor inválido ou inativo.")
    row = ImplantacaoChecklistTemplate(
        nome=data.nome.strip(),
        versao=1,
        setor_id=data.setor_id,
        ativo=data.ativo,
    )
    db.add(row)
    db.flush()
    itens = data.itens or [
        ImplantacaoTemplateItemIn(titulo=t, descricao=d, ordem=i, obrigatorio=o, chave=c)
        for i, (t, d, o, c) in enumerate(ITENS_PADRAO, start=1)
    ]
    _substituir_itens(db, row, itens)
    return obter_template(db, row.id, apenas_ativos=False)


def atualizar_template(
    db: Session, row: ImplantacaoChecklistTemplate, data: ImplantacaoTemplateUpdate, tenant_id: int
) -> ImplantacaoChecklistTemplate:
    payload = data.model_dump(exclude_unset=True)
    if "nome" in payload and data.nome:
        row.nome = data.nome.strip()
    if "ativo" in payload and data.ativo is not None:
        row.ativo = data.ativo
    if "setor_id" in payload:
        if data.setor_id is None:
            row.setor_id = None
        else:
            setor = _setor_implantacao(db, tenant_id, data.setor_id)
            if setor is None or setor.id != data.setor_id:
                raise HTTPException(status_code=400, detail="Setor inválido ou inativo.")
            row.setor_id = data.setor_id
    if data.itens is not None:
        _substituir_itens(db, row, data.itens)
        row.versao = int(row.versao or 1) + 1
    db.flush()
    return obter_template(db, row.id, apenas_ativos=False)


def obter_template_ativo(db: Session, tenant_id: int) -> ImplantacaoChecklistTemplate:
    garantir_template_padrao(db, tenant_id)
    row = (
        db.query(ImplantacaoChecklistTemplate)
        .options(joinedload(ImplantacaoChecklistTemplate.itens), joinedload(ImplantacaoChecklistTemplate.setor))
        .filter(ImplantacaoChecklistTemplate.ativo.is_(True))
        .order_by(ImplantacaoChecklistTemplate.id.asc())
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=400,
            detail="Não há checklist de implantação ativo. Configure em Cadastros.",
        )
    if not row.itens:
        raise HTTPException(
            status_code=400,
            detail="O checklist de implantação ativo não tem itens.",
        )
    return row


def copiar_checklist_para_ticket(db: Session, ticket: Ticket, template: ImplantacaoChecklistTemplate) -> None:
    if db.query(TicketChecklistItem.id).filter(TicketChecklistItem.ticket_id == ticket.id).first():
        return
    for i, item in enumerate(sorted(template.itens, key=lambda x: (x.ordem, x.id)), start=1):
        db.add(
            TicketChecklistItem(
                ticket_id=ticket.id,
                template_item_id=item.id,
                titulo=item.titulo,
                descricao=item.descricao,
                ordem=item.ordem or i,
                obrigatorio=bool(item.obrigatorio),
                chave=item.chave,
            )
        )
    db.flush()


def progresso_pct(itens: list[TicketChecklistItem]) -> int:
    if not itens:
        return 0
    feitos = sum(1 for i in itens if i.concluido)
    return int(round(100 * feitos / len(itens)))


def itens_obrigatorios_pendentes(db: Session, ticket_id: int) -> list[TicketChecklistItem]:
    return (
        db.query(TicketChecklistItem)
        .filter(
            TicketChecklistItem.ticket_id == ticket_id,
            TicketChecklistItem.obrigatorio.is_(True),
            TicketChecklistItem.concluido.is_(False),
        )
        .order_by(TicketChecklistItem.ordem.asc())
        .all()
    )


def assert_pode_fechar_ticket(db: Session, ticket: Ticket) -> None:
    if not ticket.contrato_id:
        return
    pendentes = itens_obrigatorios_pendentes(db, ticket.id)
    if pendentes:
        nomes = ", ".join(p.titulo for p in pendentes[:4])
        extra = "…" if len(pendentes) > 4 else ""
        raise HTTPException(
            status_code=400,
            detail=f"Conclua os itens obrigatórios da implantação antes de fechar o ticket: {nomes}{extra}",
        )


def _pdvs_ativos(db: Session, empresa_id: int | None) -> int | None:
    if not empresa_id:
        return None
    return (
        db.query(func.count(EmpresaPdv.id))
        .filter(EmpresaPdv.empresa_id == empresa_id, EmpresaPdv.ativo.is_(True))
        .scalar()
        or 0
    )


def checklist_do_ticket(db: Session, ticket: Ticket) -> dict:
    itens = (
        db.query(TicketChecklistItem)
        .options(joinedload(TicketChecklistItem.concluido_por))
        .filter(TicketChecklistItem.ticket_id == ticket.id)
        .order_by(TicketChecklistItem.ordem.asc(), TicketChecklistItem.id.asc())
        .all()
    )
    if not ticket.contrato_id and not itens:
        return {
            "aplicavel": False,
            "ticket_id": ticket.id,
            "contrato_id": None,
            "negociacao_id": None,
            "empresa_id": ticket.empresa_id,
            "progresso_pct": 0,
            "itens_obrigatorios_pendentes": 0,
            "pdvs_ativos": None,
            "itens": [],
        }
    negociacao_id = None
    if ticket.contrato_id:
        contrato = db.query(Contrato).filter(Contrato.id == ticket.contrato_id).first()
        if contrato:
            linha = contrato.linha or db.query(CrmNegociacaoCnpjLinha).filter(
                CrmNegociacaoCnpjLinha.id == contrato.negociacao_linha_cnpj_id
            ).first()
            if linha:
                negociacao_id = linha.negociacao_id
    pend = sum(1 for i in itens if i.obrigatorio and not i.concluido)
    return {
        "aplicavel": True,
        "ticket_id": ticket.id,
        "contrato_id": ticket.contrato_id,
        "negociacao_id": negociacao_id,
        "empresa_id": ticket.empresa_id,
        "progresso_pct": progresso_pct(itens),
        "itens_obrigatorios_pendentes": pend,
        "pdvs_ativos": _pdvs_ativos(db, ticket.empresa_id),
        "itens": [
            {
                "id": i.id,
                "titulo": i.titulo,
                "descricao": i.descricao,
                "ordem": i.ordem,
                "obrigatorio": bool(i.obrigatorio),
                "chave": i.chave,
                "concluido": bool(i.concluido),
                "concluido_por_id": i.concluido_por_id,
                "concluido_por_nome": i.concluido_por.nome if i.concluido_por else None,
                "concluido_em": i.concluido_em,
                "observacao": i.observacao,
            }
            for i in itens
        ],
    }


def atualizar_item_checklist(
    db: Session,
    ticket: Ticket,
    item_id: int,
    data: TicketChecklistItemPatch,
    ator: Atendente,
) -> TicketChecklistItem:
    if ticket.fechado_em is not None and ator.role != "admin":
        raise HTTPException(status_code=403, detail="Ticket fechado. Apenas administradores podem alterar o checklist.")
    item = (
        db.query(TicketChecklistItem)
        .filter(TicketChecklistItem.id == item_id, TicketChecklistItem.ticket_id == ticket.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item do checklist não encontrado.")
    payload = data.model_dump(exclude_unset=True)
    if "observacao" in payload:
        item.observacao = (data.observacao or "").strip() or None
    if "concluido" in payload and data.concluido is not None:
        antes = bool(item.concluido)
        item.concluido = data.concluido
        if data.concluido:
            item.concluido_por_id = ator.id
            item.concluido_em = datetime.now(timezone.utc)
        else:
            item.concluido_por_id = None
            item.concluido_em = None
        if antes != bool(data.concluido):
            db.add(
                TicketHistorico(
                    ticket_id=ticket.id,
                    atendente_id=ator.id,
                    campo="checklist",
                    valor_antigo="concluído" if antes else "pendente",
                    valor_novo=f"{item.titulo}: {'concluído' if data.concluido else 'pendente'}",
                )
            )
    db.flush()
    return item


def ticket_por_contrato(db: Session, contrato_id: int) -> Ticket | None:
    return db.query(Ticket).filter(Ticket.contrato_id == contrato_id).first()


def criar_ticket_implantacao(db: Session, contrato: Contrato, ator: Atendente) -> Ticket | None:
    """Idempotente: um ticket por contrato. Devolve o existente se já houver."""
    existente = ticket_por_contrato(db, contrato.id)
    if existente:
        return existente
    if not contrato.empresa_id:
        return None
    empresa = db.query(Empresa).filter(Empresa.id == contrato.empresa_id).first()
    if not empresa:
        return None
    template = obter_template_ativo(db, ator.tenant_id)
    setor = _setor_implantacao(db, ator.tenant_id, template.setor_id)
    if not setor:
        raise HTTPException(
            status_code=400,
            detail="Defina o setor do checklist de implantação em Cadastros (Implantação ou Suporte).",
        )
    status_inicial = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    if not status_inicial:
        raise HTTPException(status_code=400, detail="Cadastre ao menos um status de ticket.")
    linha = contrato.linha or db.query(CrmNegociacaoCnpjLinha).filter(
        CrmNegociacaoCnpjLinha.id == contrato.negociacao_linha_cnpj_id
    ).first()
    razao = (linha.razao_social if linha else None) or empresa.nome
    assunto = f"Implantação — {razao}"[:500]
    descricao = (
        f"Ticket automático após assinatura do contrato #{contrato.id}.\n"
        f"Empresa: {empresa.nome}."
    )
    ticket = Ticket(
        tenant_id=ator.tenant_id,
        protocolo=gerar_protocolo_ticket(db),
        empresa_id=empresa.id,
        rede_id=rede_id_de_empresa(db, empresa.id, tenant_id=ator.tenant_id) or empresa.rede_id,
        setor_id=setor.id,
        status_id=status_inicial.id,
        contrato_id=contrato.id,
        assunto=assunto,
        descricao=descricao,
        aberto_por_id=None,
    )
    db.add(ticket)
    db.flush()
    from app.services.sla_policy import aplicar_sla_snapshot_ao_ticket

    aplicar_sla_snapshot_ao_ticket(db, ticket)
    db.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=ator.id,
            tipo="abertura",
            corpo=descricao,
        )
    )
    copiar_checklist_para_ticket(db, ticket, template)
    db.flush()
    return ticket
