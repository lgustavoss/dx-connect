import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services import evolution_api
from app.services.whatsapp_contato_match import (
    chat_aberto_por_wa_id,
    chat_aguardando_avaliacao_por_wa_id,
    funcionario_por_wa_id,
    variantes_wa_id,
)
from app.services.protocolo_mensal import gerar_protocolo_chat
from app.services.evolution_inbound import (
    iter_inbound_edits,
    iter_inbound_reactions,
    iter_inbound_revokes,
    iter_inbound_whatsapp_messages,
    iter_message_status_updates,
)
from app.services import whatsapp_reacoes as wpp_reacoes
from app.services import whatsapp_edicao as wpp_edicao
from app.services.realtime_emit import emit_chat_mensagem_from_models
from app.services.whatsapp_media_storage import gravar_base64_em_disco
from app.services.whatsapp_wa_id_lock import lock_wa_id_para_chat, unlock_wa_id_para_chat
from app.services.whatsapp_auto_messages import (
    DEFAULT_AUTO_MSG_ESPERA,
    DEFAULT_AUTO_MSG_FORA_HORARIO,
    resolver_nome_empresa_para_template,
)
from app.core.business_calendar import is_feriado_nacional_br as _is_feriado_nacional_br
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _webhook_autorizado(request: Request, secret: str | None) -> bool:
    if not secret or not str(secret).strip():
        return True
    s = str(secret).strip()
    h = request.headers.get("X-Dx-Webhook-Secret") or request.headers.get("x-dx-webhook-secret")
    if h and h.strip() == s:
        return True
    api = request.headers.get("apikey") or request.headers.get("Apikey")
    return bool(api and api.strip() == s)


def _get_settings(db: Session) -> WhatsappSettings | None:
    return db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()


def _baixar_midia_inbound(
    *,
    item: dict,
    st_media: WhatsappSettings | None,
    tipo: str,
    wa_id: str,
    wa_mid: str | None,
) -> str | None:
    """Obtém base64 na Evolution e grava em disco. Devolve basename ou None."""
    if tipo == "texto":
        return None
    raw_env = item.get("raw_envelope")
    if not (
        isinstance(raw_env, dict)
        and st_media
        and st_media.evolution_base_url
        and st_media.evolution_instance_name
        and st_media.evolution_api_key
    ):
        logger.warning(
            "Webhook Evolution: integração incompleta para obter mídia (wa_id=%s wa_message_id=%s tipo=%s)",
            wa_id,
            wa_mid,
            tipo,
        )
        return None
    mimetype_val = item.get("mimetype")
    ok, b64, err = evolution_api.evolution_get_base64_from_media_message(
        st_media.evolution_base_url,
        st_media.evolution_instance_name,
        st_media.evolution_api_key,
        raw_env,
        convert_to_mp4=(tipo in ("video", "audio")),
    )
    if ok and b64:
        nome = gravar_base64_em_disco(b64, mimetype_val)
        if nome:
            return nome
    logger.warning(
        "Webhook Evolution: mídia não gravada (wa_id=%s wa_message_id=%s tipo=%s): %s",
        wa_id,
        wa_mid,
        tipo,
        err or "sem ficheiro",
    )
    return None


def _chat_aberto_por_wa_id(db: Session, wa_id: str) -> WhatsappChat | None:
    """Chat ativo para conversa (fila ou em atendimento). Não inclui pós-inatividade a classificar."""
    return chat_aberto_por_wa_id(db, wa_id, excluir_classificacao_pendente=True)


def _chat_aguardando_avaliacao_por_wa_id(db: Session, wa_id: str) -> WhatsappChat | None:
    return chat_aguardando_avaliacao_por_wa_id(db, wa_id)


def _fmt_data_abertura(dt: datetime | None, tz: ZoneInfo) -> str:
    if not dt:
        dt = datetime.now(tz)
    try:
        local = dt.astimezone(tz)
    except Exception:
        local = dt
    return local.strftime("%d/%m/%Y %H:%M")


def _render_template(
    template: str,
    *,
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings | None,
    atendente_nome: str | None = None,
) -> str:
    t = (template or "").strip()
    if not t:
        return ""
    nome = (chat.cliente_nome or "").strip() or "Cliente"
    # Para mensagens automáticas (webhook), por padrão assina como BOT
    nome_atendente = (atendente_nome or "").strip() or "BOT"
    nome_empresa = resolver_nome_empresa_para_template(db)
    tzname = (getattr(st, "horario_timezone", None) or "America/Sao_Paulo").strip() or "America/Sao_Paulo"
    try:
        tz = ZoneInfo(tzname)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("America/Sao_Paulo")
    data_abertura = _fmt_data_abertura(getattr(chat, "created_at", None), tz)
    return (
        # compat {var}
        t.replace("{nome}", nome)
        .replace("{atendente}", nome_atendente)
        .replace("{protocolo}", chat.protocolo)
        .replace("{telefone}", chat.wa_id)
        # novo padrão {{var}}
        .replace("{{nome_cliente}}", nome)
        .replace("{{atendente}}", nome_atendente)
        .replace("{{protocolo}}", chat.protocolo)
        .replace("{{telefone}}", chat.wa_id)
        .replace("{{nome_empresa}}", nome_empresa)
        .replace("{{data_abertura}}", data_abertura)
    )


def _try_auto_msg_espera(db: Session, st: WhatsappSettings | None, chat: WhatsappChat) -> None:
    if not st:
        return
    if not bool(getattr(st, "auto_msg_espera_ativa", True)):
        return
    txt = _render_template(
        (getattr(st, "auto_msg_espera_texto", "") or "").strip() or DEFAULT_AUTO_MSG_ESPERA,
        db=db,
        chat=chat,
        st=st,
    )
    if not txt:
        return
    if not txt.startswith("["):
        txt = f"[ BOT ]: {txt}"
    exist = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.evento_sistema == "auto_espera")
        .first()
    )
    if exist:
        return
    if not st.evolution_base_url or not st.evolution_instance_name or not st.evolution_api_key:
        logger.warning("Auto-msg espera ignorada: integração Evolution incompleta (wa_id=%s)", chat.wa_id)
        return
    ok, err, sent_wa_id = evolution_api.evolution_send_text(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        chat.wa_id,
        txt,
    )
    if not ok:
        logger.warning("Auto-msg espera falhou (wa_id=%s): %s", chat.wa_id, err)
        return
    db.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo=txt,
            tipo_midia="texto",
            mimetype=None,
            midia_nome_arquivo=None,
            wa_message_id=sent_wa_id,
            atendente_id=None,
            evento_sistema="auto_espera",
        )
    )
    # Flush apenas: commit fica no webhook. commit/rollback aqui apagava chat novo se a auto-msg falhasse.
    db.flush()


def _parse_hhmm(v: str | None) -> tuple[int, int] | None:
    if not v:
        return None
    s = str(v).strip()
    if not s or ":" not in s:
        return None
    try:
        hh_s, mm_s = s.split(":", 1)
        hh = int(hh_s)
        mm = int(mm_s)
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None
        return hh, mm
    except Exception:
        return None


def _horario_semana(st: WhatsappSettings) -> dict[str, dict] | None:
    raw = getattr(st, "horario_semana_json", None)
    if not raw or not str(raw).strip():
        return None
    try:
        v = json.loads(str(raw))
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def _esta_no_horario(st: WhatsappSettings) -> bool:
    tzname = (getattr(st, "horario_timezone", None) or "America/Sao_Paulo").strip() or "America/Sao_Paulo"
    try:
        tz = ZoneInfo(tzname)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    today = now.date()

    if bool(getattr(st, "usar_feriados_nacionais", False)) and _is_feriado_nacional_br(today):
        return False

    hs = _horario_semana(st)
    if hs:
        # Python weekday: 0=segunda ... 6=domingo
        keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
        k = keys[now.weekday()]
        cfg = hs.get(k) if isinstance(hs, dict) else None
        if isinstance(cfg, dict):
            if not bool(cfg.get("ativo", True)):
                return False
            ini = _parse_hhmm(cfg.get("inicio"))
            fim = _parse_hhmm(cfg.get("fim"))
            if not ini or not fim:
                return True
            m = now.hour * 60 + now.minute
            a = ini[0] * 60 + ini[1]
            b = fim[0] * 60 + fim[1]
            if a == b:
                return True
            if a < b:
                return a <= m < b
            return m >= a or m < b

    ini = _parse_hhmm(getattr(st, "horario_inicio", None))
    fim = _parse_hhmm(getattr(st, "horario_fim", None))
    if not ini or not fim:
        return True  # sem horário configurado => sempre dentro
    m = now.hour * 60 + now.minute
    a = ini[0] * 60 + ini[1]
    b = fim[0] * 60 + fim[1]
    if a == b:
        return True
    if a < b:
        return a <= m < b
    # janela atravessa meia-noite (ex.: 22:00-06:00)
    return m >= a or m < b


def _try_auto_msg_fora_horario(db: Session, st: WhatsappSettings | None, chat: WhatsappChat) -> None:
    if not st:
        return
    if not bool(getattr(st, "auto_msg_fora_horario_ativa", True)):
        return
    if _esta_no_horario(st):
        return
    txt = _render_template(
        (getattr(st, "auto_msg_fora_horario_texto", "") or "").strip() or DEFAULT_AUTO_MSG_FORA_HORARIO,
        db=db,
        chat=chat,
        st=st,
    )
    if not txt:
        return
    if not txt.startswith("["):
        txt = f"[ BOT ]: {txt}"
    exist = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.evento_sistema == "auto_fora_horario")
        .first()
    )
    if exist:
        return
    if not st.evolution_base_url or not st.evolution_instance_name or not st.evolution_api_key:
        logger.warning("Auto-msg fora do horário ignorada: integração Evolution incompleta (wa_id=%s)", chat.wa_id)
        return
    ok, err, sent_wa_id = evolution_api.evolution_send_text(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        chat.wa_id,
        txt,
    )
    if not ok:
        logger.warning("Auto-msg fora do horário falhou (wa_id=%s): %s", chat.wa_id, err)
        return
    db.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo=txt,
            tipo_midia="texto",
            mimetype=None,
            midia_nome_arquivo=None,
            wa_message_id=sent_wa_id,
            atendente_id=None,
            evento_sistema="auto_fora_horario",
        )
    )
    # Flush apenas: commit fica no webhook (evita rollback apagar chat recém-criado).
    db.flush()


def _processar_atualizacoes_status_mensagem(db: Session, body: dict) -> int:
    from app.services.mensagem_status import status_deve_atualizar
    from app.services.realtime_emit import emit_chat_mensagem_from_models

    atualizados = 0
    for item in iter_message_status_updates(body):
        wa_mid = item.get("wa_message_id")
        novo_status = item.get("status_entrega")
        if not wa_mid or not novo_status:
            continue
        msg = (
            db.query(WhatsappMensagem)
            .options(joinedload(WhatsappMensagem.atendente), joinedload(WhatsappMensagem.chat))
            .filter(
                WhatsappMensagem.wa_message_id == wa_mid,
                WhatsappMensagem.direcao == "outbound",
            )
            .first()
        )
        if not msg or not status_deve_atualizar(msg.status_entrega, novo_status):
            continue
        msg.status_entrega = novo_status
        try:
            db.commit()
            emit_chat_mensagem_from_models(db, msg.chat, msg)
            atualizados += 1
        except Exception:
            db.rollback()
    return atualizados


@router.post("/evolution")
def evolution_webhook(
    request: Request,
    db: Session = Depends(get_db),
    body: dict = Body(...),
):
    st = _get_settings(db)
    secret = st.webhook_secret if st else None
    if not _webhook_autorizado(request, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook não autorizado")

    event = str(body.get("event") or body.get("Event") or "").lower()
    if "update" in event and "message" in event:
        n = _processar_atualizacoes_status_mensagem(db, body)
        return {"ok": True, "status_updates": n}

    st_media = st
    processados = 0
    reacoes = 0
    revokes = 0
    edits = 0
    for item in iter_inbound_revokes(body):
        wa_id = item["wa_id"]
        lock_wa_id_para_chat(db, wa_id)
        try:
            revokes += _processar_revoke_inbound(db, item=item)
        finally:
            unlock_wa_id_para_chat(db, wa_id)

    for item in iter_inbound_edits(body):
        wa_id = item["wa_id"]
        lock_wa_id_para_chat(db, wa_id)
        try:
            edits += _processar_edit_inbound(db, item=item)
        finally:
            unlock_wa_id_para_chat(db, wa_id)

    for item in iter_inbound_reactions(body):
        wa_id = item["wa_id"]
        lock_wa_id_para_chat(db, wa_id)
        try:
            reacoes += _processar_reacao_inbound(db, item=item)
        finally:
            unlock_wa_id_para_chat(db, wa_id)

    for item in iter_inbound_whatsapp_messages(body):
        wa_id = item["wa_id"]
        lock_wa_id_para_chat(db, wa_id)
        try:
            processados += _processar_mensagem_inbound(
                db,
                item=item,
                st=st,
                st_media=st_media,
            )
        finally:
            unlock_wa_id_para_chat(db, wa_id)

    return {
        "ok": True,
        "processados": processados,
        "reacoes": reacoes,
        "revokes": revokes,
        "edits": edits,
    }


def _chat_recente_por_wa_id(db: Session, wa_id: str) -> WhatsappChat | None:
    targets = variantes_wa_id(wa_id)
    if not targets:
        return None
    return (
        db.query(WhatsappChat)
        .filter(
            WhatsappChat.wa_id.in_(targets),
            WhatsappChat.estado.in_(
                ("aguardando_atendente", "em_atendimento", "aguardando_avaliacao", "encerrado")
            ),
        )
        .order_by(WhatsappChat.id.desc())
        .first()
    )


def _mensagem_alvo(db: Session, chat: WhatsappChat, target_id: str) -> WhatsappMensagem | None:
    return (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.reacoes), joinedload(WhatsappMensagem.atendente))
        .filter(
            WhatsappMensagem.chat_id == chat.id,
            WhatsappMensagem.wa_message_id == str(target_id),
        )
        .first()
    )


def _emit_mensagem_atualizada(db: Session, chat: WhatsappChat, mensagem_id: int) -> None:
    alvo2 = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.reacoes), joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.id == mensagem_id)
        .first()
    )
    if alvo2:
        emit_chat_mensagem_from_models(db, chat, alvo2)


def _processar_revoke_inbound(db: Session, *, item: dict) -> int:
    """Cliente ou mesa apagou mensagem para todos (#630 lote 3)."""
    wa_id = item["wa_id"]
    target_id = item.get("target_wa_message_id")
    if not target_id:
        return 0
    chat = _chat_recente_por_wa_id(db, wa_id)
    if not chat:
        return 0
    alvo = _mensagem_alvo(db, chat, str(target_id))
    if not alvo or alvo.evento_sistema or wpp_edicao.mensagem_apagada(alvo):
        return 0
    try:
        alvo.corpo = wpp_edicao.CORPO_MENSAGEM_APAGADA
        alvo.apagada_em = datetime.now(timezone.utc)
        alvo.midia_nome_arquivo = None
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falha ao aplicar revoke inbound (chat=%s target=%s)", chat.protocolo, target_id)
        return 0
    _emit_mensagem_atualizada(db, chat, alvo.id)
    return 1


def _processar_edit_inbound(db: Session, *, item: dict) -> int:
    """Cliente editou mensagem (#630 lote 3)."""
    wa_id = item["wa_id"]
    target_id = item.get("target_wa_message_id")
    texto = (item.get("texto") or "").strip()
    if not target_id or not texto:
        return 0
    chat = _chat_recente_por_wa_id(db, wa_id)
    if not chat:
        return 0
    alvo = _mensagem_alvo(db, chat, str(target_id))
    if not alvo or alvo.evento_sistema or wpp_edicao.mensagem_apagada(alvo):
        return 0
    try:
        alvo.corpo = texto
        alvo.editada_em = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falha ao aplicar edit inbound (chat=%s target=%s)", chat.protocolo, target_id)
        return 0
    _emit_mensagem_atualizada(db, chat, alvo.id)
    return 1


def _processar_reacao_inbound(db: Session, *, item: dict) -> int:
    """Aplica reação do cliente (ou eco fromMe) na mensagem alvo (#630)."""
    wa_id = item["wa_id"]
    target_id = item.get("target_wa_message_id")
    if not target_id:
        return 0
    chat = _chat_recente_por_wa_id(db, wa_id)
    if not chat:
        return 0
    alvo = _mensagem_alvo(db, chat, str(target_id))
    if not alvo or alvo.evento_sistema:
        return 0

    from_me = bool(item.get("from_me"))
    origem = wpp_reacoes.ORIGEM_ATENDENTE if from_me else wpp_reacoes.ORIGEM_CLIENTE
    emoji = item.get("emoji")
    try:
        wpp_reacoes.aplicar_reacao(
            db,
            alvo,
            origem=origem,
            emoji=emoji,
            atendente_id=chat.atendente_id if from_me else None,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falha ao aplicar reação inbound (chat=%s target=%s)", chat.protocolo, target_id)
        return 0

    _emit_mensagem_atualizada(db, chat, alvo.id)
    return 1


def _processar_mensagem_inbound(
    db: Session,
    *,
    item: dict,
    st: WhatsappSettings | None,
    st_media: WhatsappSettings | None,
) -> int:
    wa_id = item["wa_id"]
    corpo = item["corpo"]
    wa_mid = item.get("wa_message_id")
    push = item.get("push_name")
    tipo = item.get("tipo") or "texto"

    tipo_midia = tipo
    mimetype_val = item.get("mimetype")
    midia_nome_original = item.get("file_name")
    if isinstance(midia_nome_original, str):
        midia_nome_original = midia_nome_original.strip()[:255] or None
    else:
        midia_nome_original = None
    midia_nome = _baixar_midia_inbound(
        item=item,
        st_media=st_media,
        tipo=tipo,
        wa_id=wa_id,
        wa_mid=wa_mid,
    )

    chat = _chat_aberto_por_wa_id(db, wa_id)
    if not chat:
        chat_aval = _chat_aguardando_avaliacao_por_wa_id(db, wa_id)
        if chat_aval is not None:
            from app.services.whatsapp_avaliacao import (
                encerrar_avaliacao_sem_nota,
                parse_nota_avaliacao,
                processar_resposta_avaliacao,
            )

            nota = parse_nota_avaliacao(corpo) if (tipo or "texto") == "texto" else None
            if nota is not None:
                chat = chat_aval
                q_prev = item.get("quoted_corpo_preview")
                if q_prev is not None and len(str(q_prev)) > 500:
                    q_prev = str(q_prev)[:500]
                msg = WhatsappMensagem(
                    chat_id=chat.id,
                    direcao="inbound",
                    corpo=corpo,
                    tipo_midia=tipo_midia,
                    mimetype=mimetype_val,
                    midia_nome_arquivo=midia_nome,
                    midia_nome_original=midia_nome_original,
                    wa_message_id=wa_mid,
                    quoted_wa_message_id=item.get("quoted_wa_message_id"),
                    quoted_corpo_preview=str(q_prev).strip()[:500] if q_prev else None,
                    atendente_id=None,
                )
                db.add(msg)
                if push and not chat.cliente_nome:
                    chat.cliente_nome = push
                try:
                    resultado = processar_resposta_avaliacao(
                        db, chat, st, corpo, tipo_midia=tipo or "texto", msg_inbound=msg
                    )
                    db.commit()
                    return 1 if resultado == "nota" else 0
                except IntegrityError:
                    db.rollback()
                    logger.info("Webhook Evolution: mensagem duplicada ignorada (wa_message_id=%s)", wa_mid)
                    return 0
                except Exception:
                    db.rollback()
                    raise
            # Não é nota: encerra avaliação sem prender o cliente e segue para chat novo
            # com esta mesma mensagem (classificação de demanda pendente permanece no chat antigo).
            if st is not None:
                try:
                    encerrar_avaliacao_sem_nota(db, chat_aval, st, motivo="pular")
                    db.flush()
                except Exception:
                    logger.exception(
                        "Falha ao encerrar avaliação sem nota (chat=%s)", chat_aval.protocolo
                    )

    if tipo == "texto":
        tipo_midia = "texto"
        mimetype_val = None
        midia_nome = None

    chat_novo = False
    if not chat:
        chat_novo = True
        func = funcionario_por_wa_id(db, wa_id)
        chat = WhatsappChat(
            protocolo=gerar_protocolo_chat(db),
            wa_id=wa_id,
            cliente_nome=push or (func.nome if func else None),
            estado="aguardando_atendente",
            setor_id=None,
            funcionario_rede_id=func.id if func else None,
            empresa_id=func.empresa_id if func and getattr(func, "empresa_id", None) else None,
        )
        db.add(chat)
        db.flush()
        try:
            _try_auto_msg_espera(db, st, chat)
        except Exception:
            logger.exception("Falha ao enviar mensagem automática de espera (chat=%s)", chat.protocolo)
        try:
            _try_auto_msg_fora_horario(db, st, chat)
        except Exception:
            logger.exception("Falha ao enviar mensagem automática fora do horário (chat=%s)", chat.protocolo)
    elif chat.estado != "em_atendimento":
        try:
            _try_auto_msg_fora_horario(db, st, chat)
        except Exception:
            logger.exception("Falha ao enviar mensagem automática fora do horário (chat=%s)", chat.protocolo)

    q_prev = item.get("quoted_corpo_preview")
    if q_prev is not None and len(str(q_prev)) > 500:
        q_prev = str(q_prev)[:500]
    msg = WhatsappMensagem(
        chat_id=chat.id,
        direcao="inbound",
        corpo=corpo,
        tipo_midia=tipo_midia,
        mimetype=mimetype_val,
        midia_nome_arquivo=midia_nome,
        midia_nome_original=midia_nome_original,
        wa_message_id=wa_mid,
        quoted_wa_message_id=item.get("quoted_wa_message_id"),
        quoted_corpo_preview=str(q_prev).strip()[:500] if q_prev else None,
        atendente_id=None,
    )
    db.add(msg)
    if push and not chat.cliente_nome:
        chat.cliente_nome = push
    if getattr(chat, "inatividade_pausada", False):
        chat.inatividade_pausada = False
        chat.inatividade_retomada_em = None
    try:
        db.commit()
        chat_emit = db.query(WhatsappChat).filter(WhatsappChat.id == chat.id).first()
        msg_emit = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.wa_message_id == wa_mid)
            .first()
        )
        if chat_emit and msg_emit:
            from app.services.realtime_emit import emit_chat_fila_from_model, emit_chat_mensagem_from_models

            emit_chat_mensagem_from_models(db, chat_emit, msg_emit)
            if chat_novo:
                emit_chat_fila_from_model(db, chat_emit, estado_anterior=None)
        return 1
    except IntegrityError:
        db.rollback()
        logger.info("Webhook Evolution: mensagem duplicada ignorada (wa_message_id=%s)", wa_mid)
        return 0
    except Exception:
        db.rollback()
        raise
