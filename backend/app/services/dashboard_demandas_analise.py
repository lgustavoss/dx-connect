"""Análise operacional de demandas WhatsApp (#594).

Limiares (documentados; v1 fixos):
- LIMIAR_INSIGHT_ERRO: natureza `erro` com total ≥ N → sugerir avaliar atualização/bug
- LIMIAR_INSIGHT_DUVIDA: natureza `duvida` + mesmo motivo ≥ N → sugerir treinamento/KB
- LIMIAR_SUGESTAO_OUTROS: motivo slug `outros` + mesma descrição normalizada ≥ N → sugerir novo motivo
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.models.whatsapp_chat import WhatsappChat
from app.models.whatsapp_chat_demanda import WhatsappChatDemanda
from app.models.whatsapp_demanda_motivo_sugestao import (
    STATUS_ACEITA,
    STATUS_IGNORADA,
    WhatsappDemandaMotivoSugestao,
)
from app.schemas.dashboard import (
    ContagemIdNome,
    DemandaDrillItem,
    DemandaEmpresaRanking,
    DemandaInsight,
    SugestaoMotivoOutros,
)
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.ticket_classificacao import TicketMotivoRead
from app.services.chat_dashboard_filters import apply_chat_dashboard_filters, period_bounds
from app.services.kb import slugify
from app.services.ticket_classificacao_rules import MOTIVO_OUTROS_SLUG

LIMIAR_INSIGHT_ERRO = 5
LIMIAR_INSIGHT_DUVIDA = 5
LIMIAR_SUGESTAO_OUTROS = 3
RANKING_EMPRESAS_TOP = 15


def normalizar_descricao_demanda(valor: str | None) -> str | None:
    if valor is None:
        return None
    t = valor.strip().lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"\s+", " ", t)
    return t or None


def _base_demandas_stmt(
    *,
    de: date,
    ate: date,
    natureza_id: int | None = None,
    motivo_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
):
    de_dt, ate_dt = period_bounds(de, ate)
    stmt = (
        select(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
        )
    )
    if natureza_id is not None:
        stmt = stmt.where(WhatsappChatDemanda.natureza_id == natureza_id)
    if motivo_id is not None:
        stmt = stmt.where(WhatsappChatDemanda.motivo_id == motivo_id)
    if empresa_id is not None:
        stmt = stmt.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt = stmt.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(Empresa.rede_id == rede_id)
    return stmt


def listar_demandas_drilldown(
    db: Session,
    atendente: Atendente,
    *,
    de: date,
    ate: date,
    setor_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
    natureza_id: int | None = None,
    motivo_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> ListaPaginada[DemandaDrillItem]:
    de_dt, ate_dt = period_bounds(de, ate)
    count_stmt = (
        select(func.count(WhatsappChatDemanda.id))
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
        )
    )
    if natureza_id is not None:
        count_stmt = count_stmt.where(WhatsappChatDemanda.natureza_id == natureza_id)
    if motivo_id is not None:
        count_stmt = count_stmt.where(WhatsappChatDemanda.motivo_id == motivo_id)
    if empresa_id is not None:
        count_stmt = count_stmt.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        count_stmt = count_stmt.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(
            Empresa.rede_id == rede_id
        )
    count_stmt = apply_chat_dashboard_filters(count_stmt, db, atendente, setor_id=setor_id)
    total = int(db.execute(count_stmt).scalar_one())

    stmt = _base_demandas_stmt(
        de=de,
        ate=ate,
        natureza_id=natureza_id,
        motivo_id=motivo_id,
        empresa_id=empresa_id,
        rede_id=rede_id,
    )
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, setor_id=setor_id)
    stmt = (
        stmt.options(
            joinedload(WhatsappChatDemanda.chat).joinedload(WhatsappChat.empresa),
            joinedload(WhatsappChatDemanda.natureza),
            joinedload(WhatsappChatDemanda.motivo),
        )
        .order_by(WhatsappChatDemanda.created_at.desc(), WhatsappChatDemanda.id.desc())
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 100))
    )
    rows = db.execute(stmt).unique().scalars().all()
    items = [
        DemandaDrillItem(
            demanda_id=r.id,
            chat_id=r.chat_id,
            protocolo=r.chat.protocolo if r.chat else "",
            cliente_nome=r.chat.cliente_nome if r.chat else None,
            empresa_id=r.chat.empresa_id if r.chat else None,
            empresa_nome=r.chat.empresa.nome if r.chat and r.chat.empresa else None,
            natureza_id=r.natureza_id,
            natureza_nome=r.natureza.nome if r.natureza else "",
            motivo_id=r.motivo_id,
            motivo_nome=r.motivo.nome if r.motivo else None,
            desfecho=r.desfecho,
            descricao_curta=r.descricao_curta,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ListaPaginada(items=items, total=total)


def ranking_demandas_por_empresa(
    db: Session,
    atendente: Atendente,
    *,
    de: date,
    ate: date,
    setor_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
    top: int = RANKING_EMPRESAS_TOP,
) -> list[DemandaEmpresaRanking]:
    de_dt, ate_dt = period_bounds(de, ate)
    stmt = (
        select(
            WhatsappChat.empresa_id,
            func.coalesce(Empresa.nome, "Sem empresa").label("empresa_nome"),
            func.count().label("total"),
        )
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .outerjoin(Empresa, Empresa.id == WhatsappChat.empresa_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
        )
        .group_by(WhatsappChat.empresa_id, Empresa.nome)
        .order_by(func.count().desc(), func.coalesce(Empresa.nome, "Sem empresa").asc())
        .limit(top)
    )
    if empresa_id is not None:
        stmt = stmt.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt = stmt.where(Empresa.rede_id == rede_id)
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, setor_id=setor_id)

    ranking: list[DemandaEmpresaRanking] = []
    for eid, nome, total in db.execute(stmt):
        nat_id, nat_nome, nat_slug = _natureza_dominante_empresa(
            db,
            atendente,
            de=de,
            ate=ate,
            setor_id=setor_id,
            empresa_id=int(eid) if eid is not None else None,
            rede_id=rede_id,
            sem_empresa=eid is None,
        )
        ranking.append(
            DemandaEmpresaRanking(
                empresa_id=int(eid) if eid is not None else None,
                empresa_nome=str(nome),
                total=int(total),
                natureza_dominante_id=nat_id,
                natureza_dominante_nome=nat_nome,
                natureza_dominante_slug=nat_slug,
            )
        )
    return ranking


def _natureza_dominante_empresa(
    db: Session,
    atendente: Atendente,
    *,
    de: date,
    ate: date,
    setor_id: int | None,
    empresa_id: int | None,
    rede_id: int | None,
    sem_empresa: bool,
) -> tuple[int | None, str | None, str | None]:
    de_dt, ate_dt = period_bounds(de, ate)
    stmt = (
        select(TicketNatureza.id, TicketNatureza.nome, TicketNatureza.slug, func.count())
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .join(TicketNatureza, TicketNatureza.id == WhatsappChatDemanda.natureza_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
        )
        .group_by(TicketNatureza.id, TicketNatureza.nome, TicketNatureza.slug)
        .order_by(func.count().desc(), TicketNatureza.nome.asc())
        .limit(1)
    )
    if sem_empresa:
        stmt = stmt.where(WhatsappChat.empresa_id.is_(None))
    elif empresa_id is not None:
        stmt = stmt.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt = stmt.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(Empresa.rede_id == rede_id)
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, setor_id=setor_id)
    row = db.execute(stmt).first()
    if not row:
        return None, None, None
    return int(row[0]), str(row[1]), str(row[2])


def maior_demanda_global(por_natureza: list[ContagemIdNome]) -> ContagemIdNome | None:
    if not por_natureza:
        return None
    return max(por_natureza, key=lambda x: (x.total, -x.id))


def gerar_insights_demandas(
    db: Session,
    atendente: Atendente,
    *,
    de: date,
    ate: date,
    setor_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
) -> list[DemandaInsight]:
    de_dt, ate_dt = period_bounds(de, ate)
    insights: list[DemandaInsight] = []

    stmt_nat = (
        select(TicketNatureza.id, TicketNatureza.nome, TicketNatureza.slug, func.count())
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .join(TicketNatureza, TicketNatureza.id == WhatsappChatDemanda.natureza_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
            TicketNatureza.slug == "erro",
        )
        .group_by(TicketNatureza.id, TicketNatureza.nome, TicketNatureza.slug)
    )
    if empresa_id is not None:
        stmt_nat = stmt_nat.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt_nat = stmt_nat.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(
            Empresa.rede_id == rede_id
        )
    stmt_nat = apply_chat_dashboard_filters(stmt_nat, db, atendente, setor_id=setor_id)
    for nid, nome, _slug, total in db.execute(stmt_nat):
        total_i = int(total)
        if total_i >= LIMIAR_INSIGHT_ERRO:
            insights.append(
                DemandaInsight(
                    tipo="avaliar_atualizacao",
                    titulo="Erros recorrentes no período",
                    detalhe=(
                        f"Há {total_i} demandas de «{nome}». Avalie correção de produto "
                        f"ou atualização (limiar: {LIMIAR_INSIGHT_ERRO})."
                    ),
                    natureza_id=int(nid),
                    motivo_id=None,
                    total=total_i,
                    limiar=LIMIAR_INSIGHT_ERRO,
                )
            )

    stmt_mot = (
        select(
            TicketMotivo.id,
            TicketMotivo.nome,
            TicketNatureza.id,
            TicketNatureza.nome,
            func.count(),
        )
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .join(TicketMotivo, TicketMotivo.id == WhatsappChatDemanda.motivo_id)
        .join(TicketNatureza, TicketNatureza.id == WhatsappChatDemanda.natureza_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
            TicketNatureza.slug == "duvida",
            WhatsappChatDemanda.motivo_id.isnot(None),
        )
        .group_by(TicketMotivo.id, TicketMotivo.nome, TicketNatureza.id, TicketNatureza.nome)
        .having(func.count() >= LIMIAR_INSIGHT_DUVIDA)
        .order_by(func.count().desc())
    )
    if empresa_id is not None:
        stmt_mot = stmt_mot.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt_mot = stmt_mot.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(
            Empresa.rede_id == rede_id
        )
    stmt_mot = apply_chat_dashboard_filters(stmt_mot, db, atendente, setor_id=setor_id)
    for mid, mnome, nid, nnome, total in db.execute(stmt_mot):
        total_i = int(total)
        insights.append(
            DemandaInsight(
                tipo="sugerir_treinamento",
                titulo="Dúvidas repetidas no mesmo motivo",
                detalhe=(
                    f"«{mnome}» ({nnome}) apareceu {total_i} vezes. "
                    f"Considere treinamento ou material na base de ajuda "
                    f"(limiar: {LIMIAR_INSIGHT_DUVIDA})."
                ),
                natureza_id=int(nid),
                motivo_id=int(mid),
                total=total_i,
                limiar=LIMIAR_INSIGHT_DUVIDA,
            )
        )

    return insights


def sugerir_motivos_outros(
    db: Session,
    atendente: Atendente,
    *,
    de: date,
    ate: date,
    setor_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
) -> list[SugestaoMotivoOutros]:
    """Agrupa descrições em motivo `outros`; exclui já aceitas/ignoradas."""
    de_dt, ate_dt = period_bounds(de, ate)
    stmt = (
        select(
            TicketNatureza.id,
            TicketNatureza.nome,
            WhatsappChatDemanda.descricao_curta,
        )
        .select_from(WhatsappChatDemanda)
        .join(WhatsappChat, WhatsappChat.id == WhatsappChatDemanda.chat_id)
        .join(TicketMotivo, TicketMotivo.id == WhatsappChatDemanda.motivo_id)
        .join(TicketNatureza, TicketNatureza.id == WhatsappChatDemanda.natureza_id)
        .where(
            WhatsappChatDemanda.created_at >= de_dt,
            WhatsappChatDemanda.created_at < ate_dt,
            TicketMotivo.slug == MOTIVO_OUTROS_SLUG,
            WhatsappChatDemanda.descricao_curta.isnot(None),
        )
    )
    if empresa_id is not None:
        stmt = stmt.where(WhatsappChat.empresa_id == empresa_id)
    if rede_id is not None:
        stmt = stmt.join(Empresa, Empresa.id == WhatsappChat.empresa_id).where(Empresa.rede_id == rede_id)
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, setor_id=setor_id)

    buckets: dict[tuple[int, str], dict] = {}
    for nid, nnome, desc in db.execute(stmt):
        norm = normalizar_descricao_demanda(desc)
        if not norm:
            continue
        key = (int(nid), norm)
        if key not in buckets:
            buckets[key] = {
                "natureza_id": int(nid),
                "natureza_nome": str(nnome),
                "texto_normalizado": norm,
                "texto_exemplo": (desc or "").strip()[:500],
                "ocorrencias": 0,
            }
        buckets[key]["ocorrencias"] += 1

    if not buckets:
        return []

    decididas = {
        (int(r.natureza_id), r.texto_normalizado)
        for r in db.query(WhatsappDemandaMotivoSugestao)
        .filter(WhatsappDemandaMotivoSugestao.status.in_([STATUS_ACEITA, STATUS_IGNORADA]))
        .all()
    }

    out: list[SugestaoMotivoOutros] = []
    for key, data in buckets.items():
        if key in decididas:
            continue
        if data["ocorrencias"] < LIMIAR_SUGESTAO_OUTROS:
            continue
        out.append(
            SugestaoMotivoOutros(
                natureza_id=data["natureza_id"],
                natureza_nome=data["natureza_nome"],
                texto_normalizado=data["texto_normalizado"],
                texto_exemplo=data["texto_exemplo"],
                ocorrencias=data["ocorrencias"],
                limiar=LIMIAR_SUGESTAO_OUTROS,
            )
        )
    out.sort(key=lambda s: (-s.ocorrencias, s.natureza_nome, s.texto_normalizado))
    return out


def _motivo_para_read(row: TicketMotivo) -> TicketMotivoRead:
    return TicketMotivoRead(
        id=row.id,
        natureza_id=row.natureza_id,
        nome=row.nome,
        slug=row.slug,
        ordem=row.ordem,
        ativo=row.ativo,
        natureza_nome=row.natureza.nome if row.natureza else None,
    )


def aceitar_sugestao_motivo_outros(
    db: Session,
    atendente: Atendente,
    *,
    natureza_id: int,
    texto_normalizado: str,
    nome: str | None = None,
    slug: str | None = None,
) -> TicketMotivoRead:
    if atendente.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem aceitar sugestões.")
    norm = normalizar_descricao_demanda(texto_normalizado)
    if not norm:
        raise HTTPException(status_code=400, detail="Texto da sugestão inválido.")
    natureza = db.query(TicketNatureza).filter(TicketNatureza.id == natureza_id).first()
    if not natureza:
        raise HTTPException(status_code=404, detail="Natureza não encontrada.")

    existente = (
        db.query(WhatsappDemandaMotivoSugestao)
        .filter(
            WhatsappDemandaMotivoSugestao.natureza_id == natureza_id,
            WhatsappDemandaMotivoSugestao.texto_normalizado == norm,
        )
        .first()
    )
    if existente and existente.status == STATUS_ACEITA and existente.motivo_criado_id:
        row = (
            db.query(TicketMotivo)
            .options(joinedload(TicketMotivo.natureza))
            .filter(TicketMotivo.id == existente.motivo_criado_id)
            .first()
        )
        if row:
            return _motivo_para_read(row)

    nome_motivo = (nome or norm).strip()[:120]
    if not nome_motivo:
        raise HTTPException(status_code=400, detail="Nome do motivo inválido.")
    slug_base = (slug or slugify(nome_motivo))[:50]
    candidato = slug_base or "motivo"
    sufixo = 2
    while (
        db.query(TicketMotivo.id)
        .filter(TicketMotivo.natureza_id == natureza_id, TicketMotivo.slug == candidato)
        .first()
        is not None
    ):
        candidato = f"{slug_base[:40]}-{sufixo}"
        sufixo += 1

    ordem_max = (
        db.execute(
            select(func.coalesce(func.max(TicketMotivo.ordem), 0)).where(
                TicketMotivo.natureza_id == natureza_id,
                TicketMotivo.slug != MOTIVO_OUTROS_SLUG,
            )
        ).scalar_one()
    )
    row = TicketMotivo(
        natureza_id=natureza_id,
        nome=nome_motivo,
        slug=candidato,
        ordem=int(ordem_max) + 1,
        ativo=True,
    )
    db.add(row)
    db.flush()

    agora = datetime.now(timezone.utc)
    if existente:
        existente.status = STATUS_ACEITA
        existente.motivo_criado_id = row.id
        existente.decidido_por_id = atendente.id
        existente.decidido_em = agora
        existente.texto_exemplo = nome_motivo[:500]
    else:
        db.add(
            WhatsappDemandaMotivoSugestao(
                natureza_id=natureza_id,
                texto_normalizado=norm,
                texto_exemplo=nome_motivo[:500],
                status=STATUS_ACEITA,
                motivo_criado_id=row.id,
                decidido_por_id=atendente.id,
                decidido_em=agora,
            )
        )
    db.commit()
    row = (
        db.query(TicketMotivo)
        .options(joinedload(TicketMotivo.natureza))
        .filter(TicketMotivo.id == row.id)
        .first()
    )
    assert row is not None
    return _motivo_para_read(row)


def ignorar_sugestao_motivo_outros(
    db: Session,
    atendente: Atendente,
    *,
    natureza_id: int,
    texto_normalizado: str,
    texto_exemplo: str | None = None,
) -> None:
    if atendente.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem ignorar sugestões.")
    norm = normalizar_descricao_demanda(texto_normalizado)
    if not norm:
        raise HTTPException(status_code=400, detail="Texto da sugestão inválido.")
    natureza = db.query(TicketNatureza).filter(TicketNatureza.id == natureza_id).first()
    if not natureza:
        raise HTTPException(status_code=404, detail="Natureza não encontrada.")

    agora = datetime.now(timezone.utc)
    existente = (
        db.query(WhatsappDemandaMotivoSugestao)
        .filter(
            WhatsappDemandaMotivoSugestao.natureza_id == natureza_id,
            WhatsappDemandaMotivoSugestao.texto_normalizado == norm,
        )
        .first()
    )
    exemplo = (texto_exemplo or norm).strip()[:500]
    if existente:
        existente.status = STATUS_IGNORADA
        existente.motivo_criado_id = None
        existente.decidido_por_id = atendente.id
        existente.decidido_em = agora
        existente.texto_exemplo = exemplo
    else:
        db.add(
            WhatsappDemandaMotivoSugestao(
                natureza_id=natureza_id,
                texto_normalizado=norm,
                texto_exemplo=exemplo,
                status=STATUS_IGNORADA,
                decidido_por_id=atendente.id,
                decidido_em=agora,
            )
        )
    db.commit()
