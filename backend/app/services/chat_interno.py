from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.setor_scope import atendente_atende_algum_id_setor, ids_setores_visiveis_atendente
from app.models import Atendente, Setor
from app.models.chat_interno import (
    TIPO_CONVERSA_DIRETA,
    TIPO_CONVERSA_SETOR,
    ConversaInterna,
    ConversaInternaLeitura,
    ConversaInternaParticipante,
    MensagemInterna,
)


class ChatInternoErro(ValueError):
    """Erro de validação de domínio do chat interno."""


@dataclass
class ConversaInboxResumo:
    conversa: ConversaInterna
    titulo: str
    ultima_mensagem_corpo: str | None
    ultima_mensagem_em: datetime | None
    nao_lidas_count: int


def is_participante(db: Session, conversa_id: int, atendente_id: int) -> bool:
    return (
        db.query(ConversaInternaParticipante.conversa_id)
        .filter(
            ConversaInternaParticipante.conversa_id == conversa_id,
            ConversaInternaParticipante.atendente_id == atendente_id,
        )
        .first()
        is not None
    )


def pode_acessar_conversa(db: Session, atendente: Atendente, conversa: ConversaInterna) -> bool:
    if conversa.tenant_id != atendente.tenant_id:
        return False
    if conversa.tipo == TIPO_CONVERSA_DIRETA:
        return is_participante(db, conversa.id, atendente.id)
    if conversa.tipo == TIPO_CONVERSA_SETOR:
        if atendente.role == "admin":
            return True
        if conversa.setor_id is None:
            return False
        return atendente_atende_algum_id_setor(db, atendente.id, conversa.setor_id)
    return False


def pode_publicar_no_canal(db: Session, atendente: Atendente, setor_id: int) -> bool:
    if atendente.role == "admin":
        return True
    return atendente_atende_algum_id_setor(db, atendente.id, setor_id)


def _find_conversa_direta_existente(
    db: Session,
    tenant_id: int,
    atendente_a_id: int,
    atendente_b_id: int,
) -> ConversaInterna | None:
    par = {atendente_a_id, atendente_b_id}
    candidatas = (
        db.query(ConversaInterna)
        .join(ConversaInternaParticipante)
        .options(joinedload(ConversaInterna.participantes))
        .filter(
            ConversaInterna.tenant_id == tenant_id,
            ConversaInterna.tipo == TIPO_CONVERSA_DIRETA,
            ConversaInternaParticipante.atendente_id == atendente_a_id,
        )
        .all()
    )
    for conversa in candidatas:
        ids = {p.atendente_id for p in conversa.participantes}
        if ids == par:
            return conversa
    return None


def obter_ou_criar_conversa_direta(
    db: Session,
    tenant_id: int,
    atendente_origem_id: int,
    atendente_destino_id: int,
) -> ConversaInterna:
    if atendente_origem_id == atendente_destino_id:
        raise ChatInternoErro("Não é possível iniciar conversa consigo mesmo.")

    existente = _find_conversa_direta_existente(db, tenant_id, atendente_origem_id, atendente_destino_id)
    if existente:
        return existente

    conversa = ConversaInterna(
        tenant_id=tenant_id,
        tipo=TIPO_CONVERSA_DIRETA,
        setor_id=None,
    )
    db.add(conversa)
    db.flush()
    db.add_all(
        [
            ConversaInternaParticipante(conversa_id=conversa.id, atendente_id=atendente_origem_id),
            ConversaInternaParticipante(conversa_id=conversa.id, atendente_id=atendente_destino_id),
        ]
    )
    db.flush()
    return conversa


def obter_ou_criar_canal_setor(db: Session, tenant_id: int, setor_id: int) -> ConversaInterna:
    setor = (
        db.query(Setor)
        .filter(Setor.id == setor_id, Setor.tenant_id == tenant_id, Setor.ativo.is_(True))
        .first()
    )
    if not setor:
        raise ChatInternoErro("Setor inválido.")

    existente = (
        db.query(ConversaInterna)
        .filter(
            ConversaInterna.tenant_id == tenant_id,
            ConversaInterna.tipo == TIPO_CONVERSA_SETOR,
            ConversaInterna.setor_id == setor_id,
        )
        .first()
    )
    if existente:
        return existente

    conversa = ConversaInterna(
        tenant_id=tenant_id,
        tipo=TIPO_CONVERSA_SETOR,
        setor_id=setor_id,
    )
    db.add(conversa)
    db.flush()
    return conversa


def contar_nao_lidas(
    db: Session,
    conversa: ConversaInterna,
    atendente_id: int,
) -> int:
    last_seen = (
        db.query(ConversaInternaLeitura.last_seen_at)
        .filter(
            ConversaInternaLeitura.conversa_id == conversa.id,
            ConversaInternaLeitura.atendente_id == atendente_id,
        )
        .scalar()
    )
    q = db.query(func.count(MensagemInterna.id)).filter(
        MensagemInterna.conversa_id == conversa.id,
        MensagemInterna.atendente_id != atendente_id,
    )
    if last_seen is not None:
        q = q.filter(MensagemInterna.created_at > last_seen)
    return int(q.scalar() or 0)


def obter_ultima_mensagem(db: Session, conversa_id: int) -> MensagemInterna | None:
    return (
        db.query(MensagemInterna)
        .filter(MensagemInterna.conversa_id == conversa_id)
        .order_by(MensagemInterna.created_at.desc(), MensagemInterna.id.desc())
        .first()
    )


def titulo_conversa(db: Session, conversa: ConversaInterna, atendente_id: int) -> str:
    if conversa.tipo == TIPO_CONVERSA_SETOR:
        if conversa.setor_id is None:
            return "Canal do setor"
        setor = db.query(Setor).filter(Setor.id == conversa.setor_id).first()
        return setor.nome if setor else "Canal do setor"

    outro_id = None
    for p in conversa.participantes:
        if p.atendente_id != atendente_id:
            outro_id = p.atendente_id
            break
    if outro_id is None:
        participante_ids = (
            db.query(ConversaInternaParticipante.atendente_id)
            .filter(ConversaInternaParticipante.conversa_id == conversa.id)
            .all()
        )
        for (aid,) in participante_ids:
            if aid != atendente_id:
                outro_id = aid
                break
    if outro_id is None:
        return "Conversa direta"
    outro = db.query(Atendente).filter(Atendente.id == outro_id).first()
    return outro.nome if outro else "Conversa direta"


def listar_conversas_inbox(db: Session, atendente: Atendente) -> list[ConversaInboxResumo]:
    conversas: list[ConversaInterna] = []

    diretas = (
        db.query(ConversaInterna)
        .join(ConversaInternaParticipante)
        .options(joinedload(ConversaInterna.participantes), joinedload(ConversaInterna.setor))
        .filter(
            ConversaInterna.tenant_id == atendente.tenant_id,
            ConversaInterna.tipo == TIPO_CONVERSA_DIRETA,
            ConversaInternaParticipante.atendente_id == atendente.id,
        )
        .all()
    )
    conversas.extend(diretas)

    q_setor = (
        db.query(ConversaInterna)
        .options(joinedload(ConversaInterna.setor))
        .filter(
            ConversaInterna.tenant_id == atendente.tenant_id,
            ConversaInterna.tipo == TIPO_CONVERSA_SETOR,
        )
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        if not vis:
            q_setor = q_setor.filter(False)
        else:
            q_setor = q_setor.filter(ConversaInterna.setor_id.in_(vis))
    conversas.extend(q_setor.all())

    resumos: list[ConversaInboxResumo] = []
    for conversa in conversas:
        ultima = obter_ultima_mensagem(db, conversa.id)
        resumos.append(
            ConversaInboxResumo(
                conversa=conversa,
                titulo=titulo_conversa(db, conversa, atendente.id),
                ultima_mensagem_corpo=ultima.corpo if ultima else None,
                ultima_mensagem_em=ultima.created_at if ultima else None,
                nao_lidas_count=contar_nao_lidas(db, conversa, atendente.id),
            )
        )

    resumos.sort(
        key=lambda r: (
            r.ultima_mensagem_em or r.conversa.created_at,
            r.conversa.id,
        ),
        reverse=True,
    )
    return resumos


def enviar_mensagem(
    db: Session,
    conversa: ConversaInterna,
    atendente: Atendente,
    corpo: str,
) -> MensagemInterna:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    texto = corpo.strip()
    if not texto:
        raise ChatInternoErro("Corpo da mensagem não pode ser vazio.")

    mensagem = MensagemInterna(
        conversa_id=conversa.id,
        atendente_id=atendente.id,
        corpo=texto,
    )
    db.add(mensagem)
    db.flush()
    return mensagem


def marcar_visto(db: Session, conversa: ConversaInterna, atendente: Atendente) -> None:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")

    now = datetime.now(timezone.utc)
    row = (
        db.query(ConversaInternaLeitura)
        .filter(
            ConversaInternaLeitura.conversa_id == conversa.id,
            ConversaInternaLeitura.atendente_id == atendente.id,
        )
        .first()
    )
    if row:
        row.last_seen_at = now
    else:
        db.add(
            ConversaInternaLeitura(
                conversa_id=conversa.id,
                atendente_id=atendente.id,
                last_seen_at=now,
            )
        )
    db.flush()


def validar_atendente_destino(
    db: Session,
    tenant_id: int,
    atendente_destino_id: int,
) -> Atendente:
    destino = (
        db.query(Atendente)
        .filter(
            Atendente.id == atendente_destino_id,
            Atendente.tenant_id == tenant_id,
            Atendente.ativo.is_(True),
        )
        .first()
    )
    if not destino:
        raise ChatInternoErro("Atendente inválido.")
    return destino


def obter_conversa_por_id(db: Session, conversa_id: int) -> ConversaInterna | None:
    return (
        db.query(ConversaInterna)
        .options(joinedload(ConversaInterna.participantes), joinedload(ConversaInterna.setor))
        .filter(ConversaInterna.id == conversa_id)
        .first()
    )


def listar_mensagens(
    db: Session,
    conversa_id: int,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[MensagemInterna], int]:
    base = db.query(MensagemInterna).filter(MensagemInterna.conversa_id == conversa_id)
    total = int(base.count())
    rows = (
        base.options(joinedload(MensagemInterna.atendente))
        .order_by(MensagemInterna.created_at.asc(), MensagemInterna.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def preview_corpo(corpo: str, max_len: int = 60) -> str:
    texto = corpo.strip()
    if len(texto) > max_len:
        return texto[:max_len] + "…"
    return texto


def contar_total_nao_lidas_atendente(db: Session, atendente: Atendente) -> int:
    return sum(r.nao_lidas_count for r in listar_conversas_inbox(db, atendente))


def listar_conversas_com_nao_lidas(
    db: Session,
    atendente: Atendente,
    *,
    limit: int = 15,
) -> list[ConversaInboxResumo]:
    resumos = [r for r in listar_conversas_inbox(db, atendente) if r.nao_lidas_count > 0]
    return resumos[:limit]
