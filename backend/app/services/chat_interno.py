from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.setor_scope import atendente_atende_algum_id_setor, ids_setores_visiveis_atendente
from app.models import Atendente, Setor
from app.models.chat_interno import (
    TIPO_CONVERSA_DIRETA,
    TIPO_CONVERSA_GRUPO,
    TIPO_CONVERSA_SETOR,
    PAPEL_PARTICIPANTE_ADMIN,
    PAPEL_PARTICIPANTE_MEMBRO,
    TIPO_MENSAGEM_AUDIO,
    TIPO_MENSAGEM_DOCUMENTO,
    TIPO_MENSAGEM_IMAGEM,
    TIPO_MENSAGEM_TEXTO,
    TIPO_MENSAGEM_VIDEO,
    TIPOS_MENSAGEM_MIDIA,
    ConversaInterna,
    ConversaInternaLeitura,
    ConversaInternaParticipante,
    MensagemInterna,
    MensagemInternaOculta,
    MensagemInternaReacao,
)
from app.services import chat_interno_media_storage as media_storage
from app.services.mensagem_status import STATUS_ENVIADA, STATUS_LIDA


class ChatInternoErro(ValueError):
    """Erro de validação de domínio do chat interno."""


CORPO_MENSAGEM_APAGADA = "Mensagem apagada"
_EMOJIS_REACAO_PERMITIDOS = frozenset({"👍", "❤️", "😂", "😮", "😢", "🙏"})
JANELA_EDICAO_MINUTOS = 5
MENSAGENS_POR_PAGINA = 50
MAX_PARTICIPANTES_GRUPO = 50


@dataclass
class ConversaInboxResumo:
    conversa: ConversaInterna
    titulo: str
    ultima_mensagem_corpo: str | None
    ultima_mensagem_em: datetime | None
    nao_lidas_count: int
    silenciado: bool = False


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
    if conversa.tipo in (TIPO_CONVERSA_DIRETA, TIPO_CONVERSA_GRUPO):
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


def is_admin_grupo(db: Session, conversa_id: int, atendente_id: int) -> bool:
    return (
        db.query(ConversaInternaParticipante)
        .filter(
            ConversaInternaParticipante.conversa_id == conversa_id,
            ConversaInternaParticipante.atendente_id == atendente_id,
            ConversaInternaParticipante.papel == PAPEL_PARTICIPANTE_ADMIN,
        )
        .first()
        is not None
    )


def conversa_esta_silenciada(db: Session, conversa_id: int, atendente_id: int) -> bool:
    row = (
        db.query(ConversaInternaParticipante.silenciado_em)
        .filter(
            ConversaInternaParticipante.conversa_id == conversa_id,
            ConversaInternaParticipante.atendente_id == atendente_id,
        )
        .first()
    )
    return row is not None and row[0] is not None


def definir_silenciado_conversa(
    db: Session,
    conversa: ConversaInterna,
    atendente: Atendente,
    *,
    silenciado: bool,
) -> ConversaInterna:
    """Silencia/dessilencia notificações sonoras para o participante atual (grupos e diretas)."""
    if conversa.tipo == TIPO_CONVERSA_SETOR:
        raise ChatInternoErro("Silenciar não está disponível para canais de setor.")
    if not is_participante(db, conversa.id, atendente.id):
        raise ChatInternoErro("Sem permissão para esta conversa.")

    participante = (
        db.query(ConversaInternaParticipante)
        .filter(
            ConversaInternaParticipante.conversa_id == conversa.id,
            ConversaInternaParticipante.atendente_id == atendente.id,
        )
        .first()
    )
    if participante is None:
        raise ChatInternoErro("Sem permissão para esta conversa.")

    participante.silenciado_em = datetime.now(timezone.utc) if silenciado else None
    db.flush()
    return conversa


def _validar_atendentes_grupo(db: Session, tenant_id: int, atendente_ids: set[int]) -> None:
    if not atendente_ids:
        raise ChatInternoErro("Informe pelo menos um participante.")
    count = (
        db.query(Atendente)
        .filter(
            Atendente.id.in_(atendente_ids),
            Atendente.tenant_id == tenant_id,
            Atendente.ativo.is_(True),
        )
        .count()
    )
    if count != len(atendente_ids):
        raise ChatInternoErro("Um ou mais atendentes são inválidos ou inativos.")


def criar_conversa_grupo(
    db: Session,
    tenant_id: int,
    criador: Atendente,
    titulo: str,
    atendente_ids: list[int],
) -> ConversaInterna:
    nome = titulo.strip()
    if not nome:
        raise ChatInternoErro("Informe o nome do grupo.")
    if len(nome) > 120:
        raise ChatInternoErro("Nome do grupo muito longo (máx. 120 caracteres).")

    ids = {int(i) for i in atendente_ids}
    ids.add(criador.id)
    if len(ids) < 2:
        raise ChatInternoErro("Grupo precisa de pelo menos 2 participantes.")
    if len(ids) > MAX_PARTICIPANTES_GRUPO:
        raise ChatInternoErro(f"Máximo de {MAX_PARTICIPANTES_GRUPO} participantes por grupo.")

    _validar_atendentes_grupo(db, tenant_id, ids)

    conversa = ConversaInterna(
        tenant_id=tenant_id,
        tipo=TIPO_CONVERSA_GRUPO,
        titulo=nome,
        setor_id=None,
    )
    db.add(conversa)
    db.flush()
    db.add_all(
        [
            ConversaInternaParticipante(
                conversa_id=conversa.id,
                atendente_id=aid,
                papel=PAPEL_PARTICIPANTE_ADMIN if aid == criador.id else PAPEL_PARTICIPANTE_MEMBRO,
            )
            for aid in ids
        ]
    )
    db.flush()
    return conversa


def _contar_admins_grupo(participantes: list[ConversaInternaParticipante]) -> int:
    return sum(1 for p in participantes if p.papel == PAPEL_PARTICIPANTE_ADMIN)


def atualizar_participantes_grupo(
    db: Session,
    conversa: ConversaInterna,
    atendente: Atendente,
    *,
    adicionar: list[int] | None = None,
    remover: list[int] | None = None,
    promover_admin: list[int] | None = None,
    rebaixar_admin: list[int] | None = None,
) -> ConversaInterna:
    if conversa.tipo != TIPO_CONVERSA_GRUPO:
        raise ChatInternoErro("Operação válida apenas para grupos.")
    if not is_admin_grupo(db, conversa.id, atendente.id):
        raise ChatInternoErro("Sem permissão para gerenciar membros deste grupo.")

    add_ids = list({int(x) for x in (adicionar or [])})
    rem_ids = list({int(x) for x in (remover or [])})
    promove_ids = list({int(x) for x in (promover_admin or [])})
    rebaixa_ids = list({int(x) for x in (rebaixar_admin or [])})

    participantes = (
        db.query(ConversaInternaParticipante)
        .filter(ConversaInternaParticipante.conversa_id == conversa.id)
        .all()
    )
    por_id = {p.atendente_id: p for p in participantes}

    for rid in rem_ids:
        participante = por_id.get(rid)
        if participante is None:
            continue
        if participante.papel == PAPEL_PARTICIPANTE_ADMIN and _contar_admins_grupo(list(por_id.values())) <= 1:
            raise ChatInternoErro("O grupo precisa de pelo menos um administrador.")
        db.delete(participante)
        del por_id[rid]

    prospective_add = [aid for aid in add_ids if aid not in por_id]
    if prospective_add:
        _validar_atendentes_grupo(db, conversa.tenant_id, set(prospective_add))
    for aid in prospective_add:
        por_id[aid] = ConversaInternaParticipante(
            conversa_id=conversa.id,
            atendente_id=aid,
            papel=PAPEL_PARTICIPANTE_MEMBRO,
        )
        db.add(por_id[aid])

    if len(por_id) < 2:
        raise ChatInternoErro("Grupo precisa de pelo menos 2 participantes.")
    if len(por_id) > MAX_PARTICIPANTES_GRUPO:
        raise ChatInternoErro(f"Máximo de {MAX_PARTICIPANTES_GRUPO} participantes por grupo.")

    for aid in promove_ids:
        if aid in por_id:
            por_id[aid].papel = PAPEL_PARTICIPANTE_ADMIN

    for aid in rebaixa_ids:
        participante = por_id.get(aid)
        if participante is None or participante.papel != PAPEL_PARTICIPANTE_ADMIN:
            continue
        if _contar_admins_grupo(list(por_id.values())) <= 1:
            raise ChatInternoErro("O grupo precisa de pelo menos um administrador.")
        participante.papel = PAPEL_PARTICIPANTE_MEMBRO

    db.flush()
    return conversa


def listar_participantes_grupo(
    db: Session,
    conversa_id: int,
) -> list[tuple[Atendente, str]]:
    rows = (
        db.query(ConversaInternaParticipante, Atendente)
        .join(Atendente, Atendente.id == ConversaInternaParticipante.atendente_id)
        .filter(ConversaInternaParticipante.conversa_id == conversa_id)
        .order_by(Atendente.nome.asc())
        .all()
    )
    return [(atendente, participante.papel) for participante, atendente in rows]


def listar_mencionaveis(
    db: Session,
    conversa: ConversaInterna,
    *,
    excluir_atendente_id: int | None = None,
) -> list[Atendente]:
    """Atendentes que podem ser mencionados na conversa (grupo / setor / direta)."""
    if conversa.tipo == TIPO_CONVERSA_GRUPO:
        rows = listar_participantes_grupo(db, conversa.id)
        atendentes = [a for a, _ in rows if a.ativo]
    elif conversa.tipo == TIPO_CONVERSA_SETOR and conversa.setor_id is not None:
        from app.models.atendente import atendente_setor

        atendentes = (
            db.query(Atendente)
            .join(atendente_setor, atendente_setor.c.atendente_id == Atendente.id)
            .filter(
                atendente_setor.c.setor_id == conversa.setor_id,
                Atendente.tenant_id == conversa.tenant_id,
                Atendente.ativo.is_(True),
            )
            .order_by(Atendente.nome.asc())
            .all()
        )
    elif conversa.tipo == TIPO_CONVERSA_DIRETA:
        rows = listar_participantes_grupo(db, conversa.id)
        atendentes = [a for a, _ in rows if a.ativo]
    else:
        atendentes = []

    if excluir_atendente_id is not None:
        atendentes = [a for a in atendentes if a.id != excluir_atendente_id]
    return atendentes


def _token_mencao_no_corpo(corpo: str, token: str) -> bool:
    """True se `@token` aparece como menção (não no meio de palavra)."""
    return re.search(rf"(?<!\w)@{re.escape(token)}(?!\w)", corpo, flags=re.IGNORECASE) is not None


def normalizar_mencoes(
    db: Session,
    conversa: ConversaInterna,
    remetente: Atendente,
    corpo: str,
    mencoes_in: list[dict] | None,
) -> list[dict] | None:
    """Valida menções enviadas pelo cliente (ou deriva do texto) e devolve JSON persistível."""
    if conversa.tipo == TIPO_CONVERSA_DIRETA:
        # Menções em DM não fazem sentido operacional — ignora.
        return None

    candidatos = {a.id: a for a in listar_mencionaveis(db, conversa)}
    out: list[dict] = []
    visto_ids: set[int] = set()
    tem_all = False

    raw = mencoes_in or []
    if not raw:
        # Deriva do corpo: @all / @todos e @Nome dos participantes.
        if _token_mencao_no_corpo(corpo, "all") or _token_mencao_no_corpo(corpo, "todos"):
            tem_all = True
        for a in sorted(candidatos.values(), key=lambda x: len(x.nome or ""), reverse=True):
            if a.id == remetente.id:
                continue
            if _token_mencao_no_corpo(corpo, a.nome):
                visto_ids.add(a.id)
                out.append({"tipo": "user", "atendente_id": a.id, "rotulo": a.nome})
    else:
        for item in raw:
            tipo = (item.get("tipo") or "").strip().lower()
            if tipo == "all":
                tem_all = True
                continue
            if tipo != "user":
                raise ChatInternoErro("Tipo de menção inválido.")
            aid = item.get("atendente_id")
            if aid is None:
                raise ChatInternoErro("Menção de usuário exige atendente_id.")
            aid = int(aid)
            if aid == remetente.id:
                continue
            alvo = candidatos.get(aid)
            if alvo is None:
                raise ChatInternoErro("Só é possível mencionar participantes desta conversa.")
            if aid in visto_ids:
                continue
            visto_ids.add(aid)
            out.append({"tipo": "user", "atendente_id": aid, "rotulo": alvo.nome})

    if tem_all:
        out.insert(0, {"tipo": "all"})

    return out or None


def mencoes_para_leitura(raw) -> list[dict]:
    if not raw or not isinstance(raw, list):
        return []
    itens: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tipo = item.get("tipo")
        if tipo == "all":
            itens.append({"tipo": "all", "atendente_id": None, "rotulo": "all"})
        elif tipo == "user":
            itens.append(
                {
                    "tipo": "user",
                    "atendente_id": item.get("atendente_id"),
                    "rotulo": item.get("rotulo"),
                }
            )
    return itens


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
        titulo=setor.nome,
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
    historico = obter_historico_oculto_ate(db, conversa.id, atendente_id)
    ocultas = ids_mensagens_ocultas_para_atendente(db, conversa.id, atendente_id)
    q = db.query(func.count(MensagemInterna.id)).filter(
        MensagemInterna.conversa_id == conversa.id,
        MensagemInterna.atendente_id != atendente_id,
    )
    if last_seen is not None:
        q = q.filter(MensagemInterna.created_at > last_seen)
    if historico is not None:
        q = q.filter(MensagemInterna.created_at > historico)
    if ocultas:
        q = q.filter(~MensagemInterna.id.in_(ocultas))
    return int(q.scalar() or 0)


def obter_ultima_mensagem(db: Session, conversa_id: int) -> MensagemInterna | None:
    return (
        db.query(MensagemInterna)
        .filter(MensagemInterna.conversa_id == conversa_id)
        .order_by(MensagemInterna.created_at.desc(), MensagemInterna.id.desc())
        .first()
    )


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def dentro_janela_edicao_apagar_todos(mensagem: MensagemInterna, agora: datetime | None = None) -> bool:
    agora = _as_utc(agora or datetime.now(timezone.utc))
    created = _as_utc(mensagem.created_at)
    limite = agora - timedelta(minutes=JANELA_EDICAO_MINUTOS)
    return created >= limite


def obter_historico_oculto_ate(db: Session, conversa_id: int, atendente_id: int) -> datetime | None:
    return (
        db.query(ConversaInternaLeitura.historico_oculto_ate)
        .filter(
            ConversaInternaLeitura.conversa_id == conversa_id,
            ConversaInternaLeitura.atendente_id == atendente_id,
        )
        .scalar()
    )


def ids_mensagens_ocultas_para_atendente(db: Session, conversa_id: int, atendente_id: int) -> set[int]:
    rows = (
        db.query(MensagemInternaOculta.mensagem_id)
        .join(MensagemInterna, MensagemInterna.id == MensagemInternaOculta.mensagem_id)
        .filter(
            MensagemInterna.conversa_id == conversa_id,
            MensagemInternaOculta.atendente_id == atendente_id,
        )
        .all()
    )
    return {int(mid) for (mid,) in rows}


def mensagem_visivel_para_atendente(
    db: Session,
    mensagem: MensagemInterna,
    atendente_id: int,
    *,
    historico_oculto_ate: datetime | None = None,
    ocultas_ids: set[int] | None = None,
) -> bool:
    if historico_oculto_ate is None:
        historico_oculto_ate = obter_historico_oculto_ate(db, mensagem.conversa_id, atendente_id)
    if historico_oculto_ate is not None and _as_utc(mensagem.created_at) <= _as_utc(historico_oculto_ate):
        return False
    if ocultas_ids is None:
        ocultas_ids = ids_mensagens_ocultas_para_atendente(db, mensagem.conversa_id, atendente_id)
    return mensagem.id not in ocultas_ids


def obter_ultima_mensagem_visivel(db: Session, conversa_id: int, atendente_id: int) -> MensagemInterna | None:
    historico = obter_historico_oculto_ate(db, conversa_id, atendente_id)
    ocultas = ids_mensagens_ocultas_para_atendente(db, conversa_id, atendente_id)
    candidatas = (
        db.query(MensagemInterna)
        .filter(MensagemInterna.conversa_id == conversa_id)
        .order_by(MensagemInterna.created_at.desc(), MensagemInterna.id.desc())
        .limit(80)
        .all()
    )
    for mensagem in candidatas:
        if mensagem_visivel_para_atendente(
            db,
            mensagem,
            atendente_id,
            historico_oculto_ate=historico,
            ocultas_ids=ocultas,
        ):
            return mensagem
    return None


def conversa_tem_mensagens_visiveis(db: Session, conversa_id: int, atendente_id: int) -> bool:
    return obter_ultima_mensagem_visivel(db, conversa_id, atendente_id) is not None


def titulo_conversa(db: Session, conversa: ConversaInterna, atendente_id: int) -> str:
    if conversa.tipo == TIPO_CONVERSA_GRUPO:
        return conversa.titulo or "Grupo"
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

    grupos = (
        db.query(ConversaInterna)
        .join(ConversaInternaParticipante)
        .options(joinedload(ConversaInterna.participantes), joinedload(ConversaInterna.setor))
        .filter(
            ConversaInterna.tenant_id == atendente.tenant_id,
            ConversaInterna.tipo == TIPO_CONVERSA_GRUPO,
            ConversaInternaParticipante.atendente_id == atendente.id,
        )
        .all()
    )
    conversas.extend(grupos)

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
        nao_lidas = contar_nao_lidas(db, conversa, atendente.id)
        ultima = obter_ultima_mensagem_visivel(db, conversa.id, atendente.id)
        # Grupos e canais de setor aparecem mesmo vazios (comunicados / primeiro aviso).
        if (
            ultima is None
            and nao_lidas == 0
            and conversa.tipo not in (TIPO_CONVERSA_GRUPO, TIPO_CONVERSA_SETOR)
        ):
            continue
        resumos.append(
            ConversaInboxResumo(
                conversa=conversa,
                titulo=titulo_conversa(db, conversa, atendente.id),
                ultima_mensagem_corpo=preview_mensagem(ultima) if ultima else None,
                ultima_mensagem_em=ultima.created_at if ultima else None,
                nao_lidas_count=nao_lidas,
                silenciado=conversa_esta_silenciada(db, conversa.id, atendente.id),
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
    reply_to_message_id: int | None = None,
    mencoes: list[dict] | None = None,
) -> MensagemInterna:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    texto = corpo.strip()
    if not texto:
        raise ChatInternoErro("Corpo da mensagem não pode ser vazio.")

    reply_id, reply_preview, reply_autor = _resolver_citacao(db, conversa.id, reply_to_message_id)
    mencoes_norm = normalizar_mencoes(db, conversa, atendente, texto, mencoes)

    mensagem = MensagemInterna(
        conversa_id=conversa.id,
        atendente_id=atendente.id,
        corpo=texto,
        tipo_midia=TIPO_MENSAGEM_TEXTO,
        reply_to_message_id=reply_id,
        reply_preview=reply_preview,
        reply_autor_nome=reply_autor,
        mencoes=mencoes_norm,
    )
    db.add(mensagem)
    db.flush()
    return mensagem


_MIDIA_ROTULOS = {
    TIPO_MENSAGEM_IMAGEM: "📷 Imagem",
    TIPO_MENSAGEM_VIDEO: "🎬 Vídeo",
    TIPO_MENSAGEM_AUDIO: "🎵 Áudio",
    TIPO_MENSAGEM_DOCUMENTO: "📄 Documento",
}

_MIDIA_FORM_PARA_DB = {
    "imagem": TIPO_MENSAGEM_IMAGEM,
    "video": TIPO_MENSAGEM_VIDEO,
    "audio": TIPO_MENSAGEM_AUDIO,
    "documento": TIPO_MENSAGEM_DOCUMENTO,
}


def normalizar_tipo_midia(mediatipo: str) -> str:
    tipo = (mediatipo or "").strip().lower()
    if tipo not in _MIDIA_FORM_PARA_DB:
        raise ChatInternoErro("Tipo de mídia inválido.")
    return _MIDIA_FORM_PARA_DB[tipo]


def rotulo_midia(tipo_midia: str) -> str:
    return _MIDIA_ROTULOS.get(tipo_midia, "📎 Anexo")


def preview_mensagem(mensagem: MensagemInterna) -> str:
    if mensagem.apagada_em is not None:
        return CORPO_MENSAGEM_APAGADA
    tipo = mensagem.tipo_midia or TIPO_MENSAGEM_TEXTO
    if tipo in TIPOS_MENSAGEM_MIDIA:
        texto = (mensagem.corpo or "").strip()
        rotulo = rotulo_midia(tipo)
        if texto and texto != rotulo:
            return preview_corpo(texto)
        return rotulo
    return preview_corpo(mensagem.corpo or "")


def _resolver_citacao(
    db: Session,
    conversa_id: int,
    reply_to_message_id: int | None,
) -> tuple[int | None, str | None, str | None]:
    if reply_to_message_id is None:
        return None, None, None
    citada = obter_mensagem_por_id(db, conversa_id, int(reply_to_message_id))
    if not citada:
        raise ChatInternoErro("Mensagem citada não encontrada nesta conversa.")
    autor = citada.atendente.nome if citada.atendente else "Atendente"
    preview = (preview_mensagem(citada) or "")[:500] or None
    return citada.id, preview, autor


def enviar_mensagem_midia(
    db: Session,
    conversa: ConversaInterna,
    atendente: Atendente,
    *,
    tipo_midia: str,
    data: bytes,
    mimetype: str | None,
    nome_original: str | None,
    caption: str = "",
    reply_to_message_id: int | None = None,
) -> MensagemInterna:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    if not data:
        raise ChatInternoErro("Arquivo vazio.")

    tipo_db = normalizar_tipo_midia(tipo_midia)

    try:
        storage_key, nome_sanitizado, mime_norm = media_storage.gravar_bytes_em_disco(
            data,
            mimetype=mimetype,
            nome_original=nome_original or "arquivo",
        )
    except ValueError as exc:
        raise ChatInternoErro(str(exc)) from exc

    cap = (caption or "").strip()
    corpo_eff = cap if cap else rotulo_midia(tipo_db)
    reply_id, reply_preview, reply_autor = _resolver_citacao(db, conversa.id, reply_to_message_id)

    mensagem = MensagemInterna(
        conversa_id=conversa.id,
        atendente_id=atendente.id,
        corpo=corpo_eff,
        tipo_midia=tipo_db,
        mimetype=mime_norm,
        nome_arquivo=nome_sanitizado,
        storage_key=storage_key,
        tamanho_bytes=len(data),
        reply_to_message_id=reply_id,
        reply_preview=reply_preview,
        reply_autor_nome=reply_autor,
    )
    db.add(mensagem)
    db.flush()
    return mensagem


def obter_mensagem_por_id(db: Session, conversa_id: int, mensagem_id: int) -> MensagemInterna | None:
    return (
        db.query(MensagemInterna)
        .options(joinedload(MensagemInterna.atendente))
        .filter(
            MensagemInterna.id == mensagem_id,
            MensagemInterna.conversa_id == conversa_id,
        )
        .first()
    )


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


def _last_seen_atendente(db: Session, conversa_id: int, atendente_id: int) -> datetime | None:
    return (
        db.query(ConversaInternaLeitura.last_seen_at)
        .filter(
            ConversaInternaLeitura.conversa_id == conversa_id,
            ConversaInternaLeitura.atendente_id == atendente_id,
        )
        .scalar()
    )


def status_entrega_mensagem(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    viewer_id: int,
) -> str | None:
    """Status estilo WhatsApp apenas para mensagens enviadas pelo viewer."""
    if mensagem.atendente_id != viewer_id:
        return None

    created = mensagem.created_at
    if created is None:
        return STATUS_ENVIADA

    if conversa.tipo == TIPO_CONVERSA_DIRETA:
        outro_id = None
        for p in conversa.participantes:
            if p.atendente_id != viewer_id:
                outro_id = p.atendente_id
                break
        if outro_id is None:
            rows = (
                db.query(ConversaInternaParticipante.atendente_id)
                .filter(ConversaInternaParticipante.conversa_id == conversa.id)
                .all()
            )
            for (aid,) in rows:
                if aid != viewer_id:
                    outro_id = aid
                    break
        if outro_id is None:
            return STATUS_ENVIADA
        last_seen = _last_seen_atendente(db, conversa.id, outro_id)
        if last_seen is not None and last_seen >= created:
            return STATUS_LIDA
        return STATUS_ENVIADA

    if conversa.tipo == TIPO_CONVERSA_SETOR:
        leu = (
            db.query(ConversaInternaLeitura.id)
            .filter(
                ConversaInternaLeitura.conversa_id == conversa.id,
                ConversaInternaLeitura.atendente_id != viewer_id,
                ConversaInternaLeitura.last_seen_at >= created,
            )
            .first()
        )
        if leu:
            return STATUS_LIDA
        return STATUS_ENVIADA

    return STATUS_ENVIADA


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
    atendente_id: int,
    *,
    antes_de_id: int | None = None,
) -> tuple[list[MensagemInterna], int, bool]:
    historico = obter_historico_oculto_ate(db, conversa_id, atendente_id)
    ocultas = ids_mensagens_ocultas_para_atendente(db, conversa_id, atendente_id)

    base = db.query(MensagemInterna).filter(MensagemInterna.conversa_id == conversa_id)
    if historico is not None:
        base = base.filter(MensagemInterna.created_at > historico)
    if ocultas:
        base = base.filter(~MensagemInterna.id.in_(ocultas))

    total = int(base.count())
    limit = MENSAGENS_POR_PAGINA

    if antes_de_id is not None:
        older_base = base.filter(MensagemInterna.id < antes_de_id)
        older_total = int(older_base.count())
        rows = (
            older_base.options(joinedload(MensagemInterna.atendente))
            .order_by(MensagemInterna.created_at.desc(), MensagemInterna.id.desc())
            .limit(limit)
            .all()
        )
        rows.reverse()
        tem_mais_antigas = older_total > limit
    else:
        rows = (
            base.options(joinedload(MensagemInterna.atendente))
            .order_by(MensagemInterna.created_at.desc(), MensagemInterna.id.desc())
            .limit(limit)
            .all()
        )
        rows.reverse()
        tem_mais_antigas = total > limit

    return rows, total, tem_mais_antigas


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


def mensagem_esta_apagada(mensagem: MensagemInterna) -> bool:
    return mensagem.apagada_em is not None


@dataclass
class PermissoesMensagem:
    pode_editar: bool
    pode_apagar_para_todos: bool
    pode_apagar_para_mim: bool


def _eh_autor_mensagem(mensagem: MensagemInterna, atendente: Atendente) -> bool:
    return mensagem.atendente_id == atendente.id


def _pode_apagar_para_todos(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
) -> bool:
    if mensagem_esta_apagada(mensagem):
        return False
    if not dentro_janela_edicao_apagar_todos(mensagem):
        return False
    if _eh_autor_mensagem(mensagem, atendente):
        return True
    if atendente.role == "admin" and conversa.tipo == TIPO_CONVERSA_SETOR:
        return True
    return False


def permissoes_mensagem(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
) -> PermissoesMensagem:
    if not mensagem_visivel_para_atendente(db, mensagem, atendente.id):
        return PermissoesMensagem(False, False, False)

    tipo = mensagem.tipo_midia or TIPO_MENSAGEM_TEXTO
    in_window = dentro_janela_edicao_apagar_todos(mensagem)
    is_author = _eh_autor_mensagem(mensagem, atendente)

    pode_editar = (
        is_author
        and in_window
        and not mensagem_esta_apagada(mensagem)
        and (tipo == TIPO_MENSAGEM_TEXTO or tipo in TIPOS_MENSAGEM_MIDIA)
    )
    pode_apagar_para_todos = _pode_apagar_para_todos(db, conversa, mensagem, atendente)
    pode_apagar_para_mim = True

    return PermissoesMensagem(
        pode_editar=pode_editar,
        pode_apagar_para_todos=pode_apagar_para_todos,
        pode_apagar_para_mim=pode_apagar_para_mim,
    )


def pode_modificar_mensagem(atendente: Atendente, mensagem: MensagemInterna) -> bool:
    """Legado — preferir permissoes_mensagem."""
    if mensagem_esta_apagada(mensagem):
        return False
    if not dentro_janela_edicao_apagar_todos(mensagem):
        return False
    return mensagem.atendente_id == atendente.id


def editar_mensagem(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
    novo_corpo: str,
    mencoes: list[dict] | None = None,
) -> MensagemInterna:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    if mensagem.conversa_id != conversa.id:
        raise ChatInternoErro("Mensagem não pertence a esta conversa.")
    if mensagem_esta_apagada(mensagem):
        raise ChatInternoErro("Mensagem apagada não pode ser editada.")
    if not _eh_autor_mensagem(mensagem, atendente):
        raise ChatInternoErro("Sem permissão para editar esta mensagem.")
    if not dentro_janela_edicao_apagar_todos(mensagem):
        raise ChatInternoErro(
            f"Só é possível editar mensagens nos primeiros {JANELA_EDICAO_MINUTOS} minutos."
        )
    tipo = mensagem.tipo_midia or TIPO_MENSAGEM_TEXTO
    if tipo == TIPO_MENSAGEM_TEXTO:
        texto = novo_corpo.strip()
        if not texto:
            raise ChatInternoErro("Corpo da mensagem não pode ser vazio.")
        mensagem.corpo = texto
        mensagem.mencoes = normalizar_mencoes(db, conversa, atendente, texto, mencoes)
    elif tipo in TIPOS_MENSAGEM_MIDIA:
        mensagem.corpo = novo_corpo.strip()
    else:
        raise ChatInternoErro("Somente mensagens de texto ou mídia podem ser editadas.")
    mensagem.editada_em = datetime.now(timezone.utc)
    db.flush()
    return mensagem


def apagar_mensagem_para_todos(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
) -> MensagemInterna:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    if mensagem.conversa_id != conversa.id:
        raise ChatInternoErro("Mensagem não pertence a esta conversa.")
    if mensagem_esta_apagada(mensagem):
        return mensagem
    if not _pode_apagar_para_todos(db, conversa, mensagem, atendente):
        raise ChatInternoErro(
            f"Só é possível apagar para todos nos primeiros {JANELA_EDICAO_MINUTOS} minutos."
        )

    now = datetime.now(timezone.utc)
    mensagem.apagada_em = now
    mensagem.corpo = CORPO_MENSAGEM_APAGADA
    db.flush()
    return mensagem


def ocultar_mensagem_para_atendente(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
) -> None:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    if mensagem.conversa_id != conversa.id:
        raise ChatInternoErro("Mensagem não pertence a esta conversa.")
    if not mensagem_visivel_para_atendente(db, mensagem, atendente.id):
        raise ChatInternoErro("Mensagem não encontrada.")
    if mensagem_esta_apagada(mensagem) and _eh_autor_mensagem(mensagem, atendente):
        return

    existente = (
        db.query(MensagemInternaOculta)
        .filter(
            MensagemInternaOculta.mensagem_id == mensagem.id,
            MensagemInternaOculta.atendente_id == atendente.id,
        )
        .first()
    )
    if not existente:
        db.add(
            MensagemInternaOculta(
                mensagem_id=mensagem.id,
                atendente_id=atendente.id,
            )
        )
        db.flush()


def limpar_conversa_para_atendente(
    db: Session,
    conversa: ConversaInterna,
    atendente: Atendente,
) -> None:
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
        row.historico_oculto_ate = now
        row.last_seen_at = now
    else:
        db.add(
            ConversaInternaLeitura(
                conversa_id=conversa.id,
                atendente_id=atendente.id,
                last_seen_at=now,
                historico_oculto_ate=now,
            )
        )
    db.flush()


def apagar_mensagem(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
    *,
    escopo: str,
) -> MensagemInterna | None:
    if escopo == "todos":
        return apagar_mensagem_para_todos(db, conversa, mensagem, atendente)
    if escopo == "para_mim":
        ocultar_mensagem_para_atendente(db, conversa, mensagem, atendente)
        return None
    raise ChatInternoErro("Escopo de exclusão inválido.")


def _validar_emoji_reacao(emoji: str) -> str:
    valor = (emoji or "").strip()
    if valor not in _EMOJIS_REACAO_PERMITIDOS:
        raise ChatInternoErro("Emoji de reação inválido.")
    return valor


def definir_reacao_mensagem(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
    emoji: str,
) -> MensagemInterna:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    if mensagem.conversa_id != conversa.id:
        raise ChatInternoErro("Mensagem não pertence a esta conversa.")
    if mensagem_esta_apagada(mensagem):
        raise ChatInternoErro("Não é possível reagir a mensagem apagada.")

    emoji_ok = _validar_emoji_reacao(emoji)
    row = (
        db.query(MensagemInternaReacao)
        .filter(
            MensagemInternaReacao.mensagem_id == mensagem.id,
            MensagemInternaReacao.atendente_id == atendente.id,
        )
        .first()
    )
    if row:
        if row.emoji == emoji_ok:
            db.delete(row)
        else:
            row.emoji = emoji_ok
    else:
        db.add(
            MensagemInternaReacao(
                mensagem_id=mensagem.id,
                atendente_id=atendente.id,
                emoji=emoji_ok,
            )
        )
    db.flush()
    db.refresh(mensagem)
    return mensagem


def remover_reacao_mensagem(
    db: Session,
    conversa: ConversaInterna,
    mensagem: MensagemInterna,
    atendente: Atendente,
) -> MensagemInterna:
    if not pode_acessar_conversa(db, atendente, conversa):
        raise ChatInternoErro("Sem permissão para esta conversa.")
    if mensagem.conversa_id != conversa.id:
        raise ChatInternoErro("Mensagem não pertence a esta conversa.")

    db.query(MensagemInternaReacao).filter(
        MensagemInternaReacao.mensagem_id == mensagem.id,
        MensagemInternaReacao.atendente_id == atendente.id,
    ).delete(synchronize_session=False)
    db.flush()
    db.refresh(mensagem)
    return mensagem


@dataclass
class ReacaoAgregada:
    emoji: str
    count: int
    reagiu_eu: bool


def agregar_reacoes_mensagem(
    db: Session,
    mensagem_id: int,
    viewer_id: int,
) -> list[ReacaoAgregada]:
    rows = (
        db.query(MensagemInternaReacao.emoji, MensagemInternaReacao.atendente_id)
        .filter(MensagemInternaReacao.mensagem_id == mensagem_id)
        .all()
    )
    por_emoji: dict[str, dict[str, int | bool]] = {}
    for emoji, atendente_id in rows:
        bucket = por_emoji.setdefault(emoji, {"count": 0, "reagiu_eu": False})
        bucket["count"] = int(bucket["count"]) + 1
        if atendente_id == viewer_id:
            bucket["reagiu_eu"] = True
    return [
        ReacaoAgregada(emoji=emoji, count=int(data["count"]), reagiu_eu=bool(data["reagiu_eu"]))
        for emoji, data in sorted(por_emoji.items(), key=lambda item: (-int(item[1]["count"]), item[0]))
    ]


def corpo_mensagem_para_leitura(mensagem: MensagemInterna) -> str:
    if mensagem_esta_apagada(mensagem):
        return CORPO_MENSAGEM_APAGADA
    return mensagem.corpo
