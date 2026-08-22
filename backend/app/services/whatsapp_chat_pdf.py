"""Exportação de conversa WhatsApp em PDF (#837)."""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session, joinedload

from app.models.empresa_sistema import EmpresaSistema
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.services.comercial_proposta import html_para_pdf
from app.services.whatsapp_avaliacao import mensagem_oculta_na_conversa

logger = logging.getLogger(__name__)

# Chats muito longos: exporta as primeiras N mensagens visíveis (ordem cronológica).
MAX_MENSAGENS_PDF = 3000

_ESTADO_ROTULO = {
    "em_atendimento": "Em atendimento",
    "aguardando_atendente": "Aguardando atendimento",
    "aguardando_avaliacao": "Aguardando avaliação",
    "encerrado": "Encerrado",
}

_EVENTO_ROTULO = {
    "auto_espera": "Aviso automático (espera)",
    "auto_assumido": "Atendimento assumido",
    "auto_encerrado": "Encerrado automaticamente",
    "auto_fora_horario": "Fora do horário",
    "auto_inativ_aviso": "Aviso de inatividade",
    "auto_encerrado_inatividade": "Encerrado por inatividade",
    "transferencia": "Chat transferido",
    "demanda_registrada": "Demanda registada",
    "demanda_escalada": "Demanda escalada",
}

_TIPO_MIDIA_ROTULO = {
    "imagem": "[Imagem]",
    "audio": "[Áudio]",
    "video": "[Vídeo]",
    "documento": "[Documento]",
    "figurinha": "[Figurinha]",
}


def _esc(value: object | None) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is not None:
        local = value.astimezone()
    else:
        local = value
    return local.strftime("%d/%m/%Y %H:%M")


def _rotulo_estado(estado: str | None) -> str:
    if not estado:
        return "—"
    return _ESTADO_ROTULO.get(estado, estado.replace("_", " "))


def _autor(m: WhatsappMensagem) -> str:
    evento = getattr(m, "evento_sistema", None)
    if evento:
        return "Sistema"
    if m.direcao == "inbound":
        return "Cliente"
    nome = (getattr(m.atendente, "nome", None) if m.atendente else None) or getattr(m, "atendente_nome", None)
    if nome:
        return f"Atendente ({nome})"
    return "Atendente"


def _corpo_export(m: WhatsappMensagem) -> str:
    if getattr(m, "apagada", False) or getattr(m, "apagada_em", None):
        return "Mensagem apagada"
    evento = getattr(m, "evento_sistema", None)
    if evento:
        rotulo = _EVENTO_ROTULO.get(evento, evento.replace("_", " "))
        corpo = (m.corpo or "").strip()
        return f"{rotulo}" + (f" — {corpo}" if corpo else "")
    tipo = (getattr(m, "tipo_midia", None) or "texto").lower()
    if tipo in _TIPO_MIDIA_ROTULO:
        nome = (getattr(m, "midia_nome_original", None) or "").strip()
        base = _TIPO_MIDIA_ROTULO[tipo]
        if tipo == "documento" and nome:
            base = f"[Documento: {nome}]"
        corpo = (m.corpo or "").strip()
        return f"{base}" + (f"\n{corpo}" if corpo else "")
    return (m.corpo or "").strip() or "—"


def _nome_ficheiro(protocolo: str | None, chat_id: int) -> str:
    raw = (protocolo or "").strip() or str(chat_id)
    safe = re.sub(r"[^\w.\-]+", "-", raw, flags=re.UNICODE).strip("-") or str(chat_id)
    return f"chat-{safe}.pdf"


def _mensagens_para_export(db: Session, chat_id: int) -> tuple[list[WhatsappMensagem], int]:
    rows = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.chat_id == chat_id)
        .order_by(WhatsappMensagem.created_at.asc(), WhatsappMensagem.id.asc())
        .all()
    )
    visiveis: list[WhatsappMensagem] = []
    for m in rows:
        evento = getattr(m, "evento_sistema", None)
        if mensagem_oculta_na_conversa(evento):
            continue
        # Comentários internos não vão para o PDF (uso típico: enviar ao cliente).
        if evento == "comentario_interno":
            continue
        visiveis.append(m)
    total = len(visiveis)
    return visiveis[:MAX_MENSAGENS_PDF], total


def _empresa_sistema_nome(db: Session) -> str:
    row = db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()
    if not row:
        return "DeskRudder"
    return (row.nome_fantasia or row.nome or row.razao_social or "DeskRudder").strip()


def montar_html_chat_pdf(
    db: Session,
    chat: WhatsappChat,
    mensagens: Sequence[WhatsappMensagem],
    *,
    total_visiveis: int,
) -> str:
    marca = _empresa_sistema_nome(db)
    protocolo = chat.protocolo or str(chat.id)
    contacto = chat.cliente_nome or "Contacto"
    empresa_nome = getattr(chat.empresa, "nome", None) if chat.empresa else None
    setor_nome = getattr(chat.setor, "nome", None) if chat.setor else None
    atendente_nome = getattr(chat.atendente, "nome", None) if chat.atendente else None

    linhas: list[str] = []
    for m in mensagens:
        autor = _esc(_autor(m))
        quando = _esc(_fmt_dt(m.created_at))
        corpo = _esc(_corpo_export(m)).replace("\n", "<br/>")
        classe = "sistema" if getattr(m, "evento_sistema", None) else ("cliente" if m.direcao == "inbound" else "atendente")
        linhas.append(
            f'<tr class="{classe}"><td class="meta"><strong>{autor}</strong><br/><span class="hora">{quando}</span></td>'
            f'<td class="corpo">{corpo}</td></tr>'
        )

    aviso_corte = ""
    if total_visiveis > len(mensagens):
        aviso_corte = (
            f'<p class="aviso">Exportação truncada: mostram-se as primeiras {len(mensagens)} de '
            f"{total_visiveis} mensagens (limite {MAX_MENSAGENS_PDF}).</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <title>Chat { _esc(protocolo) }</title>
  <style>
    body {{ font-family: DejaVu Sans, Arial, sans-serif; font-size: 11pt; color: #1e293b; margin: 24px; }}
    h1 {{ font-size: 16pt; margin: 0 0 4px; }}
    .marca {{ color: #64748b; font-size: 9pt; margin-bottom: 16px; }}
    .meta-grid {{ width: 100%; border-collapse: collapse; margin-bottom: 18px; }}
    .meta-grid th, .meta-grid td {{ text-align: left; padding: 4px 8px 4px 0; vertical-align: top; }}
    .meta-grid th {{ color: #64748b; font-weight: 600; width: 9rem; }}
    table.msgs {{ width: 100%; border-collapse: collapse; }}
    table.msgs td {{ border-top: 1px solid #e2e8f0; padding: 8px 6px; vertical-align: top; }}
    table.msgs td.meta {{ width: 28%; color: #475569; font-size: 9pt; }}
    table.msgs td.corpo {{ white-space: pre-wrap; word-break: break-word; }}
    table.msgs tr.sistema td.corpo {{ font-style: italic; color: #64748b; }}
    .hora {{ color: #94a3b8; }}
    .aviso {{ margin-top: 16px; padding: 8px 10px; background: #fff7ed; border: 1px solid #fed7aa; font-size: 9pt; }}
    .rodape {{ margin-top: 24px; font-size: 8pt; color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="marca">{_esc(marca)} · Exportação de conversa WhatsApp</div>
  <h1>Protocolo { _esc(protocolo) }</h1>
  <table class="meta-grid">
    <tr><th>Contacto</th><td>{_esc(contacto)}</td></tr>
    <tr><th>Telefone</th><td>{_esc(chat.wa_id)}</td></tr>
    <tr><th>Empresa</th><td>{_esc(empresa_nome) or "—"}</td></tr>
    <tr><th>Setor</th><td>{_esc(setor_nome) or "—"}</td></tr>
    <tr><th>Atendente</th><td>{_esc(atendente_nome) or "—"}</td></tr>
    <tr><th>Estado</th><td>{_esc(_rotulo_estado(chat.estado))}</td></tr>
    <tr><th>Abertura</th><td>{_esc(_fmt_dt(chat.created_at))}</td></tr>
    <tr><th>Início atendimento</th><td>{_esc(_fmt_dt(chat.atendimento_inicio_at))}</td></tr>
    <tr><th>Encerramento</th><td>{_esc(_fmt_dt(chat.encerramento_at))}</td></tr>
  </table>
  <table class="msgs">
    <tbody>
      {"".join(linhas) if linhas else '<tr><td colspan="2">Sem mensagens para exportar.</td></tr>'}
    </tbody>
  </table>
  {aviso_corte}
  <p class="rodape">Gerado em {_esc(_fmt_dt(datetime.now().astimezone()))}. Comentários internos não são incluídos.</p>
</body>
</html>
"""


def gerar_pdf_chat(db: Session, chat: WhatsappChat) -> tuple[bytes, str]:
    mensagens, total = _mensagens_para_export(db, chat.id)
    html_doc = montar_html_chat_pdf(db, chat, mensagens, total_visiveis=total)
    pdf = html_para_pdf(html_doc)
    return pdf, _nome_ficheiro(chat.protocolo, chat.id)
