"""Serviço do catálogo comercial de custos (#321 / #329–#335).

Regras de negócio (lote B):
- TEF no catálogo = valores padrão; na proposta pode haver override de custo e valor ao cliente (#331).
- Desconto posto <100k L: ativado manualmente (desconto_posto_100k); nos 3 primeiros meses,
  se em algum mês passar de 100k o comercial remove o desconto — controlo interno, sem job (#332).
- calcular_custo_pacote devolve snapshot serializável imutável para gravar em contrato depois (#335).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.comercial_custo import (
    TIPO_COMPOSTO_TEF,
    TIPO_PERCENTUAL_SM,
    TIPO_VALOR_FIXO,
    TIPOS_CUSTO_CATALOGO,
    CustoCatalogoItem,
    SalarioMinimoReferencia,
)
from app.schemas.comercial_custo import (
    CustoCatalogoItemCreate,
    CustoCatalogoItemUpdate,
    CustoSimularLinha,
    CustoSimularResponse,
    CustoTefOverride,
    SalarioMinimoAtualizarValor,
    SalarioMinimoCreate,
    SalarioMinimoUpdate,
)

# Percentual SM quando o comercial ativa o desconto declarado pelo cliente (<100k L/mês).
PERCENTUAL_DESCONTO_POSTO_100K = Decimal("20")


def _ranges_overlap(
    a_ini: date,
    a_fim: date | None,
    b_ini: date,
    b_fim: date | None,
) -> bool:
    """Intervalos inclusivos; fim null = aberto."""
    if a_fim is not None and a_fim < b_ini:
        return False
    if b_fim is not None and b_fim < a_ini:
        return False
    return True


def validar_vigencia_sm(
    db: Session,
    *,
    vigencia_inicio: date,
    vigencia_fim: date | None,
    exclude_id: int | None = None,
) -> None:
    q = db.query(SalarioMinimoReferencia)
    if exclude_id is not None:
        q = q.filter(SalarioMinimoReferencia.id != exclude_id)
    for row in q.all():
        if _ranges_overlap(vigencia_inicio, vigencia_fim, row.vigencia_inicio, row.vigencia_fim):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Vigência sobrepõe outro salário mínimo "
                    f"(id={row.id}, {row.vigencia_inicio}–{row.vigencia_fim or 'vigente'})."
                ),
            )


def obter_sm_na_data(db: Session, ref: date) -> SalarioMinimoReferencia | None:
    return (
        db.query(SalarioMinimoReferencia)
        .filter(
            SalarioMinimoReferencia.vigencia_inicio <= ref,
            or_(
                SalarioMinimoReferencia.vigencia_fim.is_(None),
                SalarioMinimoReferencia.vigencia_fim >= ref,
            ),
        )
        .order_by(SalarioMinimoReferencia.vigencia_inicio.desc())
        .first()
    )


def criar_sm(db: Session, data: SalarioMinimoCreate) -> SalarioMinimoReferencia:
    validar_vigencia_sm(db, vigencia_inicio=data.vigencia_inicio, vigencia_fim=data.vigencia_fim)
    row = SalarioMinimoReferencia(
        valor=data.valor,
        vigencia_inicio=data.vigencia_inicio,
        vigencia_fim=data.vigencia_fim,
    )
    db.add(row)
    db.flush()
    return row


def obter_sm_vigente_aberto(db: Session) -> SalarioMinimoReferencia | None:
    """Último SM com vigência aberta (fim null)."""
    return (
        db.query(SalarioMinimoReferencia)
        .filter(SalarioMinimoReferencia.vigencia_fim.is_(None))
        .order_by(SalarioMinimoReferencia.vigencia_inicio.desc())
        .first()
    )


def atualizar_valor_sm(db: Session, data: SalarioMinimoAtualizarValor) -> SalarioMinimoReferencia:
    """
    Altera o SM a partir de `vigencia_inicio` sem reescrever o passado:
    fecha o registro vigente no dia anterior e cria um novo (histórico).
    Se ainda não houver nenhum SM, cria o primeiro.
    """
    aberto = obter_sm_vigente_aberto(db)
    if aberto is None:
        if db.query(SalarioMinimoReferencia).count() == 0:
            return criar_sm(
                db,
                SalarioMinimoCreate(valor=data.valor, vigencia_inicio=data.vigencia_inicio, vigencia_fim=None),
            )
        raise HTTPException(
            status_code=400,
            detail="Não há salário mínimo vigente aberto. Corrija o histórico ou cadastre um SM com vigência aberta.",
        )

    if data.vigencia_inicio <= aberto.vigencia_inicio:
        raise HTTPException(
            status_code=400,
            detail=(
                "A data do novo valor deve ser posterior ao início do SM vigente "
                f"({aberto.vigencia_inicio.isoformat()})."
            ),
        )

    fim_anterior = data.vigencia_inicio - timedelta(days=1)
    if fim_anterior < aberto.vigencia_inicio:
        raise HTTPException(
            status_code=400,
            detail="Intervalo inválido ao encerrar o SM vigente.",
        )

    aberto.vigencia_fim = fim_anterior
    db.flush()

    novo = SalarioMinimoReferencia(
        valor=data.valor,
        vigencia_inicio=data.vigencia_inicio,
        vigencia_fim=None,
    )
    db.add(novo)
    db.flush()
    return novo


def atualizar_sm(db: Session, row: SalarioMinimoReferencia, data: SalarioMinimoUpdate) -> SalarioMinimoReferencia:
    payload = data.model_dump(exclude_unset=True)
    inicio = payload.get("vigencia_inicio", row.vigencia_inicio)
    fim = payload.get("vigencia_fim", row.vigencia_fim) if "vigencia_fim" in payload else row.vigencia_fim
    if "vigencia_fim" in payload and payload["vigencia_fim"] is None:
        fim = None
    if fim is not None and fim < inicio:
        raise HTTPException(status_code=400, detail="vigencia_fim deve ser >= vigencia_inicio")
    validar_vigencia_sm(db, vigencia_inicio=inicio, vigencia_fim=fim, exclude_id=row.id)
    for k, v in payload.items():
        setattr(row, k, v)
    db.flush()
    return row


def _validar_campos_item(
    tipo: str,
    *,
    percentual_sm,
    valor_fixo,
    tef_base,
    tef_adicional,
    aplica_tier_posto: bool,
) -> None:
    if tipo not in TIPOS_CUSTO_CATALOGO:
        raise HTTPException(status_code=400, detail=f"tipo inválido: {tipo}")
    if tipo == TIPO_PERCENTUAL_SM and percentual_sm is None:
        raise HTTPException(status_code=400, detail="percentual_sm é obrigatório para percentual_sm")
    if tipo == TIPO_VALOR_FIXO and valor_fixo is None:
        raise HTTPException(status_code=400, detail="valor_fixo é obrigatório para valor_fixo")
    if tipo == TIPO_COMPOSTO_TEF and (tef_base is None or tef_adicional is None):
        raise HTTPException(status_code=400, detail="tef_base e tef_adicional são obrigatórios para composto_tef")
    if aplica_tier_posto and tipo != TIPO_PERCENTUAL_SM:
        raise HTTPException(status_code=400, detail="aplica_tier_posto só se aplica a itens percentual_sm")


def criar_item(db: Session, data: CustoCatalogoItemCreate) -> CustoCatalogoItem:
    if db.query(CustoCatalogoItem).filter(CustoCatalogoItem.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="Slug de item de custo já existe.")
    _validar_campos_item(
        data.tipo,
        percentual_sm=data.percentual_sm,
        valor_fixo=data.valor_fixo,
        tef_base=data.tef_base,
        tef_adicional=data.tef_adicional,
        aplica_tier_posto=data.aplica_tier_posto,
    )
    row = CustoCatalogoItem(**data.model_dump())
    db.add(row)
    db.flush()
    return row


def atualizar_item(db: Session, row: CustoCatalogoItem, data: CustoCatalogoItemUpdate) -> CustoCatalogoItem:
    payload = data.model_dump(exclude_unset=True)
    if "slug" in payload:
        slug = str(payload["slug"]).strip().lower()
        payload["slug"] = slug
        dup = (
            db.query(CustoCatalogoItem)
            .filter(CustoCatalogoItem.slug == slug, CustoCatalogoItem.id != row.id)
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Slug de item de custo já existe.")
    tipo = payload.get("tipo", row.tipo)
    percentual = payload.get("percentual_sm", row.percentual_sm)
    valor_fixo = payload.get("valor_fixo", row.valor_fixo)
    tef_base = payload.get("tef_base", row.tef_base)
    tef_adicional = payload.get("tef_adicional", row.tef_adicional)
    aplica_tier = payload.get("aplica_tier_posto", row.aplica_tier_posto)
    _validar_campos_item(
        tipo,
        percentual_sm=percentual,
        valor_fixo=valor_fixo,
        tef_base=tef_base,
        tef_adicional=tef_adicional,
        aplica_tier_posto=bool(aplica_tier),
    )
    for k, v in payload.items():
        setattr(row, k, v)
    db.flush()
    return row


def _item_vigente_em(item: CustoCatalogoItem, ref: date) -> bool:
    if item.vigencia_inicio and item.vigencia_inicio > ref:
        return False
    if item.vigencia_fim and item.vigencia_fim < ref:
        return False
    return True


def _dec(v) -> Decimal:
    return Decimal(v).quantize(Decimal("0.01"))


def _percentual_efetivo(item: CustoCatalogoItem, desconto_posto_100k: bool) -> Decimal:
    """
    Itens com aplica_tier_posto: desconto_posto_100k=True → 20% SM (cliente declarou <100k).
    Sem desconto → percentual do catálogo (tipicamente 30%).
    Controlo após os 3 meses / perda do desconto se passar 100k em algum mês = manual (#332).
    """
    if item.aplica_tier_posto and desconto_posto_100k:
        return PERCENTUAL_DESCONTO_POSTO_100K
    return Decimal(item.percentual_sm or 0)


def _tef_custo_efetivo(
    item: CustoCatalogoItem,
    override: CustoTefOverride | None,
) -> tuple[Decimal, Decimal, bool]:
    """Retorna (base, adicional, usou_override) para o custo interno."""
    if override and override.tef_custo_base is not None and override.tef_custo_adicional is not None:
        return Decimal(override.tef_custo_base), Decimal(override.tef_custo_adicional), True
    return Decimal(item.tef_base or 0), Decimal(item.tef_adicional or 0), False


def _tef_valor_cliente(
    override: CustoTefOverride | None,
    quantidade_pdvs: int,
) -> Decimal | None:
    if not override or override.tef_valor_cliente_base is None:
        return None
    base = Decimal(override.tef_valor_cliente_base)
    adicional = Decimal(override.tef_valor_cliente_adicional or 0)
    extras = max(0, quantidade_pdvs - 1)
    return (base + adicional * extras).quantize(Decimal("0.01"))


def calcular_custo_pacote(
    db: Session,
    *,
    item_ids: list[int],
    quantidade_pdvs: int = 1,
    data_referencia: date | None = None,
    desconto_posto_100k: bool = False,
    tef_override: CustoTefOverride | None = None,
) -> CustoSimularResponse:
    """
    Motor canónico (#335): linhas de custo + total + snapshot JSON.
    Valor ao cliente do TEF (se informado) entra só no snapshot — não soma em total_custo.
    """
    ref = data_referencia or date.today()
    sm_row = obter_sm_na_data(db, ref)
    sm_valor = Decimal(sm_row.valor) if sm_row else None

    ids_unicos = list(dict.fromkeys(item_ids))
    itens = (
        db.query(CustoCatalogoItem)
        .filter(CustoCatalogoItem.id.in_(ids_unicos), CustoCatalogoItem.ativo.is_(True))
        .all()
    )
    by_id = {i.id: i for i in itens}
    faltando = [i for i in ids_unicos if i not in by_id]
    if faltando:
        raise HTTPException(status_code=400, detail=f"Itens inexistentes ou inativos: {faltando}")

    if tef_override is not None:
        tem_tef = any(by_id[i].tipo == TIPO_COMPOSTO_TEF for i in ids_unicos)
        if not tem_tef:
            raise HTTPException(
                status_code=400,
                detail="tef_override só pode ser usado quando há um item composto_tef no pacote.",
            )

    linhas: list[CustoSimularLinha] = []
    snapshot_itens: list[dict] = []
    total = Decimal("0.00")

    for iid in ids_unicos:
        item = by_id[iid]
        if not _item_vigente_em(item, ref):
            raise HTTPException(
                status_code=400,
                detail=f"Item «{item.nome}» fora da vigência em {ref.isoformat()}.",
            )

        percentual_usado: Decimal | None = None
        override_custo = False
        tef_valor_cli: Decimal | None = None
        snap: dict = {
            "id": item.id,
            "slug": item.slug,
            "nome": item.nome,
            "tipo": item.tipo,
            "aplica_tier_posto": bool(item.aplica_tier_posto),
        }

        if item.tipo == TIPO_PERCENTUAL_SM:
            if sm_valor is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item «{item.nome}» exige salário mínimo vigente na data de referência.",
                )
            percentual_usado = _percentual_efetivo(item, desconto_posto_100k)
            valor = (sm_valor * percentual_usado / Decimal("100")).quantize(Decimal("0.01"))
            snap["percentual_catalogo"] = str(Decimal(item.percentual_sm or 0))
            snap["percentual_usado"] = str(percentual_usado)
            snap["valor"] = str(valor)

        elif item.tipo == TIPO_VALOR_FIXO:
            valor = _dec(item.valor_fixo or 0)
            snap["valor"] = str(valor)

        elif item.tipo == TIPO_COMPOSTO_TEF:
            base_cat = Decimal(item.tef_base or 0)
            adic_cat = Decimal(item.tef_adicional or 0)
            base, adicional, override_custo = _tef_custo_efetivo(item, tef_override)
            extras = max(0, quantidade_pdvs - 1)
            valor = (base + adicional * extras).quantize(Decimal("0.01"))
            tef_valor_cli = _tef_valor_cliente(tef_override, quantidade_pdvs)
            snap.update(
                {
                    "tef_base_catalogo": str(_dec(base_cat)),
                    "tef_adicional_catalogo": str(_dec(adic_cat)),
                    "tef_base_usado": str(_dec(base)),
                    "tef_adicional_usado": str(_dec(adicional)),
                    "override_custo": override_custo,
                    "valor_custo": str(valor),
                }
            )
            if tef_override and tef_override.tef_valor_cliente_base is not None:
                snap["tef_valor_cliente_base"] = str(_dec(tef_override.tef_valor_cliente_base))
                snap["tef_valor_cliente_adicional"] = str(
                    _dec(tef_override.tef_valor_cliente_adicional or 0)
                )
                snap["tef_valor_cliente"] = str(tef_valor_cli) if tef_valor_cli is not None else None
        else:
            raise HTTPException(status_code=400, detail=f"Tipo de item não suportado: {item.tipo}")

        linhas.append(
            CustoSimularLinha(
                item_id=item.id,
                nome=item.nome,
                slug=item.slug,
                tipo=item.tipo,
                valor=valor,
                percentual_usado=percentual_usado,
                override_custo=override_custo,
                tef_valor_cliente=tef_valor_cli,
            )
        )
        snapshot_itens.append(snap)
        total += valor

    total_q = total.quantize(Decimal("0.01"))
    snapshot = {
        "versao": 1,
        "calculado_em": datetime.now(timezone.utc).isoformat(),
        "data_referencia": ref.isoformat(),
        "salario_minimo": (
            {"id": sm_row.id, "valor": str(_dec(sm_valor))} if sm_row and sm_valor is not None else None
        ),
        "desconto_posto_100k": desconto_posto_100k,
        "quantidade_pdvs": quantidade_pdvs,
        "itens": snapshot_itens,
        "total_custo": str(total_q),
    }

    return CustoSimularResponse(
        data_referencia=ref,
        salario_minimo=sm_valor,
        salario_minimo_id=sm_row.id if sm_row else None,
        quantidade_pdvs=quantidade_pdvs,
        desconto_posto_100k=desconto_posto_100k,
        linhas=linhas,
        total=total_q,
        total_custo=total_q,
        snapshot=snapshot,
    )


def simular_custo(
    db: Session,
    *,
    item_ids: list[int],
    quantidade_pdvs: int = 1,
    data_referencia: date | None = None,
    desconto_posto_100k: bool = False,
    tef_override: CustoTefOverride | None = None,
) -> CustoSimularResponse:
    """Fachada da API — delega ao motor (#335)."""
    return calcular_custo_pacote(
        db,
        item_ids=item_ids,
        quantidade_pdvs=quantidade_pdvs,
        data_referencia=data_referencia,
        desconto_posto_100k=desconto_posto_100k,
        tef_override=tef_override,
    )
