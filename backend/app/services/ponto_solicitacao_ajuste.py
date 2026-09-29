"""Solicitações de inclusão/correção/abono de ponto (#1135 / abono).

Aprovação nesta versão: só admin. O parâmetro `aprovador` e o filtro por
tenant isolam o ponto de extensão para supervisor de setor (grupos de permissão).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.ponto_batida import PontoBatida
from app.models.ponto_solicitacao_ajuste import PontoSolicitacaoAjuste
from app.schemas.ponto import PontoSolicitacaoAjusteRead
from app.services import ponto as ponto_svc
from app.services import ponto_ausencia as ausencia_svc
from app.services import ponto_settings as ponto_settings_svc
from app.services.escala import PONTO_TZ

TIPOS_SOLICITACAO = frozenset({"inclusao", "correcao", "abono"})
TIPOS_BATIDA = frozenset({"entrada", "saida"})
ESTADOS_DECISAO = frozenset({"aprovada", "rejeitada"})


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_read(row: PontoSolicitacaoAjuste) -> PontoSolicitacaoAjusteRead:
    tem = bool(getattr(row, "anexo_storage_key", None))
    return PontoSolicitacaoAjusteRead(
        id=row.id,
        atendente_id=row.atendente_id,
        atendente_nome=row.atendente.nome if row.atendente else None,
        tipo=row.tipo,
        estado=row.estado,
        motivo=row.motivo,
        data_ref=row.data_ref,
        tipo_batida=row.tipo_batida,
        horario_solicitado=row.horario_solicitado,
        horario_anterior=getattr(row, "horario_anterior", None),
        batida_id=row.batida_id,
        tem_anexo=tem,
        anexo_nome=row.anexo_nome if tem else None,
        anexo_content_type=row.anexo_content_type if tem else None,
        anexo_tamanho_bytes=row.anexo_tamanho_bytes if tem else None,
        decisao_motivo=row.decisao_motivo,
        decidido_por_id=row.decidido_por_id,
        decidido_em=row.decidido_em,
        created_at=row.created_at,
    )


def _exigir_pode_decidir(aprovador: Atendente) -> None:
    """Hook de escopo: hoje só admin; depois supervisor por setor entra aqui."""
    if aprovador.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem decidir solicitações de ponto.",
        )


def contar_pendentes(db: Session, tenant_id: int) -> int:
    return (
        db.query(PontoSolicitacaoAjuste)
        .filter(
            PontoSolicitacaoAjuste.tenant_id == tenant_id,
            PontoSolicitacaoAjuste.estado == "pendente",
        )
        .count()
    )


def criar(
    db: Session,
    atendente: Atendente,
    *,
    tipo: str,
    motivo: str,
    horario_solicitado: datetime | None = None,
    tipo_batida: str | None = None,
    batida_id: int | None = None,
    data_ref: date | None = None,
    anexo_storage_key: str | None = None,
    anexo_nome: str | None = None,
    anexo_content_type: str | None = None,
    anexo_tamanho_bytes: int | None = None,
) -> PontoSolicitacaoAjusteRead:
    ponto_svc.exigir_acesso_ponto(atendente)
    if tipo not in TIPOS_SOLICITACAO:
        raise HTTPException(status_code=400, detail="Tipo de solicitação inválido")
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 3:
        raise HTTPException(status_code=400, detail="Informe o motivo (mínimo 3 caracteres).")

    if tipo == "abono":
        if data_ref is None:
            raise HTTPException(status_code=400, detail="Informe a data do abono.")
        dia = data_ref
        if ponto_settings_svc.eh_feriado(db, atendente.tenant_id, dia):
            raise HTTPException(status_code=400, detail="Não é possível abonar um feriado.")
        if ausencia_svc.tipo_ausencia_aprovada_no_dia(db, atendente.id, dia):
            raise HTTPException(status_code=400, detail="Já existe ausência aprovada neste dia.")
        pendente_abono = (
            db.query(PontoSolicitacaoAjuste)
            .filter(
                PontoSolicitacaoAjuste.atendente_id == atendente.id,
                PontoSolicitacaoAjuste.estado == "pendente",
                PontoSolicitacaoAjuste.tipo == "abono",
                PontoSolicitacaoAjuste.data_ref == dia,
            )
            .first()
        )
        if pendente_abono:
            raise HTTPException(status_code=400, detail="Já existe um abono pendente neste dia.")
        row = PontoSolicitacaoAjuste(
            tenant_id=atendente.tenant_id,
            atendente_id=atendente.id,
            tipo="abono",
            estado="pendente",
            motivo=motivo_limpo,
            data_ref=dia,
            tipo_batida=None,
            horario_solicitado=None,
            batida_id=None,
            anexo_storage_key=anexo_storage_key,
            anexo_nome=anexo_nome,
            anexo_content_type=anexo_content_type,
            anexo_tamanho_bytes=anexo_tamanho_bytes,
        )
    else:
        if not tipo_batida or tipo_batida not in TIPOS_BATIDA:
            raise HTTPException(status_code=400, detail="Tipo de batida inválido")
        if horario_solicitado is None:
            raise HTTPException(status_code=400, detail="Informe o horário solicitado.")
        quando = _as_utc(horario_solicitado)
        dia = data_ref or quando.astimezone(PONTO_TZ).date()

        if tipo == "correcao":
            if batida_id is None:
                raise HTTPException(status_code=400, detail="Informe a batida a corrigir.")
            batida = (
                db.query(PontoBatida)
                .filter(
                    PontoBatida.id == batida_id,
                    PontoBatida.tenant_id == atendente.tenant_id,
                    PontoBatida.atendente_id == atendente.id,
                    PontoBatida.anulada.is_(False),
                )
                .first()
            )
            if not batida:
                raise HTTPException(status_code=404, detail="Batida não encontrada")
            horario_anterior = _as_utc(batida.registrado_em)
        else:
            batida = None
            horario_anterior = None
            if batida_id is not None:
                raise HTTPException(status_code=400, detail="Inclusão não deve referenciar batida existente.")

        pendente_igual = (
            db.query(PontoSolicitacaoAjuste)
            .filter(
                PontoSolicitacaoAjuste.atendente_id == atendente.id,
                PontoSolicitacaoAjuste.estado == "pendente",
                PontoSolicitacaoAjuste.tipo == tipo,
                PontoSolicitacaoAjuste.data_ref == dia,
                PontoSolicitacaoAjuste.tipo_batida == tipo_batida,
            )
            .first()
        )
        if pendente_igual and tipo == "correcao" and pendente_igual.batida_id == batida_id:
            raise HTTPException(status_code=400, detail="Já existe uma correção pendente para esta batida.")
        if pendente_igual and tipo == "inclusao":
            raise HTTPException(
                status_code=400,
                detail="Já existe uma inclusão pendente deste tipo neste dia.",
            )

        row = PontoSolicitacaoAjuste(
            tenant_id=atendente.tenant_id,
            atendente_id=atendente.id,
            tipo=tipo,
            estado="pendente",
            motivo=motivo_limpo,
            data_ref=dia,
            tipo_batida=tipo_batida,
            horario_solicitado=quando,
            horario_anterior=horario_anterior,
            batida_id=batida_id if tipo == "correcao" else None,
            anexo_storage_key=anexo_storage_key,
            anexo_nome=anexo_nome,
            anexo_content_type=anexo_content_type,
            anexo_tamanho_bytes=anexo_tamanho_bytes,
        )

    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_solicitacao_ajuste",
        row.id,
        "create",
        atendente.id,
        payload={
            "tipo": tipo,
            "tipo_batida": row.tipo_batida,
            "data_ref": str(row.data_ref),
            "horario_solicitado": row.horario_solicitado.isoformat() if row.horario_solicitado else None,
            "horario_anterior": row.horario_anterior.isoformat() if getattr(row, "horario_anterior", None) else None,
            "batida_id": row.batida_id,
            "motivo": motivo_limpo,
            "tem_anexo": bool(anexo_storage_key),
        },
    )
    db.commit()
    db.refresh(row)
    row = (
        db.query(PontoSolicitacaoAjuste)
        .options(joinedload(PontoSolicitacaoAjuste.atendente))
        .filter(PontoSolicitacaoAjuste.id == row.id)
        .first()
    )
    assert row is not None
    return _to_read(row)


def listar_me(db: Session, atendente: Atendente) -> list[PontoSolicitacaoAjusteRead]:
    ponto_svc.exigir_acesso_ponto(atendente)
    rows = (
        db.query(PontoSolicitacaoAjuste)
        .options(joinedload(PontoSolicitacaoAjuste.atendente))
        .filter(PontoSolicitacaoAjuste.atendente_id == atendente.id)
        .order_by(PontoSolicitacaoAjuste.created_at.desc())
        .limit(100)
        .all()
    )
    return [_to_read(r) for r in rows]


def listar_para_aprovador(
    db: Session,
    aprovador: Atendente,
    *,
    estado: str | None = "pendente",
) -> list[PontoSolicitacaoAjusteRead]:
    _exigir_pode_decidir(aprovador)
    q = (
        db.query(PontoSolicitacaoAjuste)
        .options(joinedload(PontoSolicitacaoAjuste.atendente))
        .filter(PontoSolicitacaoAjuste.tenant_id == aprovador.tenant_id)
    )
    if estado:
        q = q.filter(PontoSolicitacaoAjuste.estado == estado)
    rows = q.order_by(PontoSolicitacaoAjuste.created_at.asc()).limit(200).all()
    return [_to_read(r) for r in rows]


def decidir(
    db: Session,
    aprovador: Atendente,
    solicitacao_id: int,
    *,
    estado: str,
    decisao_motivo: str,
) -> PontoSolicitacaoAjusteRead:
    _exigir_pode_decidir(aprovador)
    if estado not in ESTADOS_DECISAO:
        raise HTTPException(status_code=400, detail="Estado de decisão inválido")
    motivo_limpo = (decisao_motivo or "").strip()
    if estado == "aprovada" and len(motivo_limpo) < 3:
        motivo_limpo = "Aprovado"
    if estado == "rejeitada" and len(motivo_limpo) < 3:
        raise HTTPException(status_code=400, detail="Informe o motivo da rejeição (mínimo 3 caracteres).")

    row = (
        db.query(PontoSolicitacaoAjuste)
        .options(joinedload(PontoSolicitacaoAjuste.atendente))
        .filter(
            PontoSolicitacaoAjuste.id == solicitacao_id,
            PontoSolicitacaoAjuste.tenant_id == aprovador.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if row.estado != "pendente":
        raise HTTPException(status_code=400, detail="Solicitação já foi decidida")

    row.estado = estado
    row.decisao_motivo = motivo_limpo
    row.decidido_por_id = aprovador.id
    row.decidido_em = datetime.now(timezone.utc)

    if estado == "aprovada":
        if row.tipo == "abono":
            ausencia_svc.criar_abono_aprovado(
                db,
                tenant_id=row.tenant_id,
                atendente_id=row.atendente_id,
                data_ref=row.data_ref,
                motivo=row.motivo,
                decidido_por_id=aprovador.id,
            )
        else:
            motivo_apply = f"Solicitação #{row.id}: {row.motivo}"
            if row.tipo == "inclusao":
                assert row.tipo_batida and row.horario_solicitado
                ponto_svc.admin_criar_batida(
                    db,
                    aprovador,
                    atendente_id=row.atendente_id,
                    tipo=row.tipo_batida,
                    registrado_em=row.horario_solicitado,
                    motivo=motivo_apply,
                    commit=False,
                )
            else:
                assert row.batida_id is not None
                assert row.tipo_batida and row.horario_solicitado
                ponto_svc.admin_atualizar_batida(
                    db,
                    aprovador,
                    row.batida_id,
                    tipo=row.tipo_batida,
                    registrado_em=row.horario_solicitado,
                    motivo=motivo_apply,
                    commit=False,
                )

    registrar_audit(
        db,
        "ponto_solicitacao_ajuste",
        row.id,
        f"decidir_{estado}",
        aprovador.id,
        payload={"decisao_motivo": motivo_limpo, "tipo": row.tipo},
    )
    db.commit()
    db.refresh(row)
    row = (
        db.query(PontoSolicitacaoAjuste)
        .options(joinedload(PontoSolicitacaoAjuste.atendente))
        .filter(PontoSolicitacaoAjuste.id == row.id)
        .first()
    )
    assert row is not None
    return _to_read(row)


def obter_anexo(
    db: Session,
    viewer: Atendente,
    solicitacao_id: int,
) -> tuple[bytes, str, str]:
    """Retorna (bytes, nome, content_type). Owner ou admin do tenant."""
    ponto_svc.exigir_acesso_ponto(viewer)
    row = (
        db.query(PontoSolicitacaoAjuste)
        .filter(
            PontoSolicitacaoAjuste.id == solicitacao_id,
            PontoSolicitacaoAjuste.tenant_id == viewer.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if viewer.role != "admin" and row.atendente_id != viewer.id:
        raise HTTPException(status_code=403, detail="Sem permissão para este anexo")
    if not row.anexo_storage_key:
        raise HTTPException(status_code=404, detail="Esta solicitação não tem anexo")

    from app.services import ponto_justificativa_storage as storage

    path = storage.caminho_absoluto(row.anexo_storage_key)
    if path is None:
        raise HTTPException(status_code=404, detail="Arquivo do anexo não encontrado")
    data = path.read_bytes()
    nome = row.anexo_nome or path.name
    ctype = row.anexo_content_type or "application/octet-stream"
    return data, nome, ctype
