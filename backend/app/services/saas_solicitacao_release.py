"""Conclusão automática de solicitações no release CalVer (#956)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.saas_solicitacao_produto import (
    SaasSolicitacaoProduto,
    SaasSolicitacaoProdutoComentario,
)
from app.services import saas_solicitacao_ingest as ingest
from app.services.solicitacao_melhoria import (
    aplicar_comentario_origem_saas,
    aplicar_status_origem_saas,
    aplicar_versao_alvo_origem_saas,
)
from app.services.solicitacao_melhoria_copy import normalizar_versao_alvo
from app.services.saas_solicitacao_triagem import _deve_aplicar_local

logger = logging.getLogger(__name__)

_PROTOCOLO_RE = re.compile(r"#S(\d{6})-(\d{4})", re.IGNORECASE)
_ISSUE_RE = re.compile(r"(?<![A-Za-z0-9])#(\d{3,5})\b")


def extrair_referencias_release(textos: list[str]) -> tuple[set[str], set[int]]:
    """Protocolos #S… e issues GitHub citadas no CHANGELOG/PR."""
    protocolos: set[str] = set()
    issues: set[int] = set()
    for raw in textos:
        texto = raw or ""
        for m in _PROTOCOLO_RE.finditer(texto):
            protocolos.add(f"#S{m.group(1).upper()}-{m.group(2)}")
        for m in _ISSUE_RE.finditer(texto):
            issues.add(int(m.group(1)))
    return protocolos, issues


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _ids_grupo(db: Session, row: SaasSolicitacaoProduto) -> list[int]:
    if row.grupo_id is None:
        return [row.id]
    return [
        r.id
        for r in db.query(SaasSolicitacaoProduto)
        .filter(SaasSolicitacaoProduto.grupo_id == row.grupo_id)
        .all()
    ]


def _marcar_concluida_release(
    db: Session,
    row: SaasSolicitacaoProduto,
    *,
    versao: str,
    comentario: str,
    origem_sync: str,
) -> bool:
    """Marca pedido concluído com versão. Idempotente. Sem commit."""
    versao_n = normalizar_versao_alvo(versao)
    if not versao_n:
        return False
    alterou = False
    if normalizar_versao_alvo(row.versao_alvo) != versao_n:
        row.versao_alvo = versao_n
        alterou = True
    if row.status != "concluida":
        row.status = "concluida"
        alterou = True
    if alterou:
        row.triagem_atualizada_em = _agora()
        db.add(row)
        db.flush()
    if _deve_aplicar_local(row):
        aplicar_versao_alvo_origem_saas(db, row.origem_solicitacao_id, versao_n)
        aplicar_status_origem_saas(
            db,
            row.origem_solicitacao_id,
            status_novo="concluida",
            motivo_nao_desenvolvimento=None,
            atendente_id=None,
        )
    ja = (
        db.query(SaasSolicitacaoProdutoComentario)
        .filter(
            SaasSolicitacaoProdutoComentario.solicitacao_id == row.id,
            SaasSolicitacaoProdutoComentario.corpo == comentario,
            SaasSolicitacaoProdutoComentario.publico_cliente.is_(True),
        )
        .first()
    )
    if ja is None:
        db.add(
            SaasSolicitacaoProdutoComentario(
                solicitacao_id=row.id,
                corpo=comentario,
                publico_cliente=True,
                autor_nome="DeskRudder",
            )
        )
        db.flush()
        if _deve_aplicar_local(row):
            aplicar_comentario_origem_saas(
                db,
                row.origem_solicitacao_id,
                corpo=comentario,
                origem_externa_id=origem_sync,
                autor_nome="DeskRudder",
            )
        alterou = True
    return alterou


def concluir_pedidos_release(
    db: Session,
    *,
    versao: str,
    textos_changelog: list[str],
) -> dict[str, int]:
    """Resolve pedidos citados no release → concluida + versao_alvo. Falha parcial não aborta."""
    versao_n = normalizar_versao_alvo(versao)
    if not versao_n:
        return {"processados": 0, "concluidos": 0, "ignorados": 0, "erros": 0}

    protocolos, issues = extrair_referencias_release(textos_changelog)
    if not protocolos and not issues:
        return {"processados": 0, "concluidos": 0, "ignorados": 0, "erros": 0}

    q = db.query(SaasSolicitacaoProduto)
    filtros = []
    if protocolos:
        filtros.append(SaasSolicitacaoProduto.protocolo.in_(sorted(protocolos)))
    if issues:
        filtros.append(SaasSolicitacaoProduto.github_issue_number.in_(sorted(issues)))
    from sqlalchemy import or_

    candidatos = q.filter(or_(*filtros)).all()
    vistos: set[int] = set()
    concluidos = 0
    ignorados = 0
    erros = 0
    comentario = f"Melhoria disponível a partir da versão {versao_n} (ou superior)."
    origem = f"release:{versao_n}"

    for row in candidatos:
        if row.status == "nao_sera_desenvolvida":
            ignorados += 1
            continue
        if row.status == "concluida" and normalizar_versao_alvo(row.versao_alvo) == versao_n:
            ignorados += 1
            continue
        for sid in _ids_grupo(db, row):
            if sid in vistos:
                continue
            vistos.add(sid)
            alvo = ingest.obter(db, sid)
            try:
                if _marcar_concluida_release(
                    db,
                    alvo,
                    versao=versao_n,
                    comentario=comentario,
                    origem_sync=origem,
                ):
                    concluidos += 1
                else:
                    ignorados += 1
            except Exception:
                erros += 1
                logger.exception("Falha ao concluir solicitação SaaS id=%s no release %s", sid, versao_n)

    if concluidos or erros:
        db.commit()
    return {
        "processados": len(vistos),
        "concluidos": concluidos,
        "ignorados": ignorados,
        "erros": erros,
    }
