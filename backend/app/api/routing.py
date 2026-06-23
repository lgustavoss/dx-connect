from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.models.rede import Rede
from app.models.routing_rule import RoutingRule
from app.models.setor import Setor
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.schemas.routing import (
    RoutingAction,
    RoutingCondition,
    RoutingResultRead,
    RoutingRuleCreate,
    RoutingRuleRead,
    RoutingRuleReorder,
    RoutingRuleUpdate,
    RoutingSimulateRequest,
)
from app.services.routing_evaluate import RoutingContext, evaluate_routing, resultado_para_read_dict

router = APIRouter(prefix="/routing", tags=["routing"])


def _validar_acoes(db: Session, tenant_id: int, acoes: RoutingAction) -> None:
    if acoes.setor_id is not None:
        setor = db.query(Setor).filter(Setor.id == acoes.setor_id, Setor.tenant_id == tenant_id).first()
        if not setor:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setor da ação não encontrado")
    if acoes.natureza_id is not None:
        nat = db.query(TicketNatureza).filter(TicketNatureza.id == acoes.natureza_id).first()
        if not nat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Natureza não encontrada")
    if acoes.motivo_id is not None:
        mot = db.query(TicketMotivo).filter(TicketMotivo.id == acoes.motivo_id).first()
        if not mot:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Motivo não encontrado")
        if acoes.natureza_id is not None and mot.natureza_id != acoes.natureza_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Motivo não pertence à natureza informada",
            )
    if acoes.atendente_id is not None:
        at = db.query(Atendente).filter(Atendente.id == acoes.atendente_id, Atendente.tenant_id == tenant_id).first()
        if not at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Atendente não encontrado")


def _validar_rede(db: Session, tenant_id: int, rede_id: int | None) -> None:
    if rede_id is None:
        return
    rede = db.query(Rede).filter(Rede.id == rede_id, Rede.tenant_id == tenant_id).first()
    if not rede:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rede não encontrada")


def _row_para_read(rule: RoutingRule) -> RoutingRuleRead:
    return RoutingRuleRead.from_orm_row(rule)


@router.get("/rules", response_model=list[RoutingRuleRead])
def listar_regras(
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    q = db.query(RoutingRule).filter(RoutingRule.tenant_id == atendente.tenant_id)
    if not incluir_inativos:
        q = q.filter(RoutingRule.ativo.is_(True))
    rules = q.order_by(RoutingRule.ordem.asc(), RoutingRule.id.asc()).all()
    return [_row_para_read(r) for r in rules]


@router.post("/rules", response_model=RoutingRuleRead, status_code=201)
def criar_regra(
    data: RoutingRuleCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    _validar_rede(db, atendente.tenant_id, data.rede_id)
    _validar_acoes(db, atendente.tenant_id, data.acoes)
    max_ordem = (
        db.query(RoutingRule.ordem)
        .filter(RoutingRule.tenant_id == atendente.tenant_id)
        .order_by(RoutingRule.ordem.desc())
        .limit(1)
        .scalar()
    )
    ordem = (max_ordem + 1) if max_ordem is not None else 0
    rule = RoutingRule(
        tenant_id=atendente.tenant_id,
        nome=data.nome.strip(),
        ativo=data.ativo,
        ordem=ordem,
        rede_id=data.rede_id,
        condicoes=[c.model_dump(mode="json") for c in data.condicoes],
        acoes=data.acoes.model_dump(mode="json", exclude_none=True),
    )
    db.add(rule)
    db.flush()
    registrar_audit(db, "routing_rule", rule.id, "create", atendente.id)
    db.commit()
    db.refresh(rule)
    return _row_para_read(rule)


@router.put("/rules/reorder", response_model=list[RoutingRuleRead])
def reordenar_regras(
    data: RoutingRuleReorder,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    ids = [item.id for item in data.items]
    rules = (
        db.query(RoutingRule)
        .filter(RoutingRule.tenant_id == atendente.tenant_id, RoutingRule.id.in_(ids))
        .all()
    )
    if len(rules) != len(ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uma ou mais regras não encontradas")
    ordem_por_id = {item.id: item.ordem for item in data.items}
    for rule in rules:
        rule.ordem = ordem_por_id[rule.id]
    registrar_audit(db, "routing_rule", 0, "reorder", atendente.id)
    db.commit()
    rules = (
        db.query(RoutingRule)
        .filter(RoutingRule.tenant_id == atendente.tenant_id)
        .order_by(RoutingRule.ordem.asc(), RoutingRule.id.asc())
        .all()
    )
    return [_row_para_read(r) for r in rules]


@router.post("/rules/simulate", response_model=RoutingResultRead)
def simular_regra(
    data: RoutingSimulateRequest,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    ctx = RoutingContext(
        email_from=data.email_from,
        email_to=data.email_to,
        assunto=data.assunto,
        canal=data.canal,
        rede_id=data.rede_id,
    )
    resultado = evaluate_routing(db, tenant_id=atendente.tenant_id, context=ctx)
    if resultado.matched and not data.aplicar_setor and data.setor_id_atual is not None:
        resultado.setor_id = data.setor_id_atual
    return RoutingResultRead.model_validate(resultado_para_read_dict(resultado))


@router.get("/rules/{rule_id}", response_model=RoutingRuleRead)
def obter_regra(
    rule_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    return _row_para_read(rule)


@router.put("/rules/{rule_id}", response_model=RoutingRuleRead)
def atualizar_regra(
    rule_id: int,
    data: RoutingRuleUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    rule = db.query(RoutingRule).filter(
        RoutingRule.id == rule_id, RoutingRule.tenant_id == atendente.tenant_id
    ).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")

    payload = data.model_dump(exclude_unset=True)
    if "nome" in payload and payload["nome"] is not None:
        rule.nome = payload["nome"].strip()
    if "ativo" in payload:
        rule.ativo = payload["ativo"]
    if "rede_id" in payload:
        _validar_rede(db, atendente.tenant_id, payload["rede_id"])
        rule.rede_id = payload["rede_id"]
    if "condicoes" in payload and payload["condicoes"] is not None:
        conds = [RoutingCondition.model_validate(c) for c in payload["condicoes"]]
        rule.condicoes = [c.model_dump(mode="json") for c in conds]
    if "acoes" in payload and payload["acoes"] is not None:
        acoes = RoutingAction.model_validate(payload["acoes"])
        _validar_acoes(db, atendente.tenant_id, acoes)
        rule.acoes = acoes.model_dump(mode="json", exclude_none=True)

    registrar_audit(db, "routing_rule", rule.id, "update", atendente.id)
    db.commit()
    db.refresh(rule)
    return _row_para_read(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_regra(
    rule_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    rule = db.query(RoutingRule).filter(
        RoutingRule.id == rule_id, RoutingRule.tenant_id == atendente.tenant_id
    ).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    db.delete(rule)
    registrar_audit(db, "routing_rule", rule_id, "delete", atendente.id)
    db.commit()
