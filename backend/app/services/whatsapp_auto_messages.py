"""Textos padrão das mensagens automáticas WhatsApp (espelham o frontend ConfigWhatsapp)."""

from sqlalchemy.orm import Session

from app.models.empresa_sistema import EmpresaSistema
from app.models.whatsapp_chat import WhatsappSettings

DEFAULT_AUTO_MSG_ESPERA = (
    "Olá, {{nome_cliente}}, Seja Bem-Vindo(a) a {{nome_empresa}}.\n\n"
    "✅protocolo de atendimento: *{{protocolo}}*\n\n"
    "Abertura: *{{data_abertura}}*\n"
)
DEFAULT_AUTO_MSG_ASSUMIDO = (
    "Olá, {nome}! Sou o {atendente} atendente responsável pelo seu atendimento. Como posso ajudar?"
)
DEFAULT_AUTO_MSG_ENCERRADO = (
    "Atendimento encerrado. Se precisar de algo mais, é só enviar uma nova mensagem por aqui."
)
DEFAULT_AUTO_MSG_FORA_HORARIO = (
    "Olá, {nome}! No momento estamos fora do horário de atendimento. "
    "Assim que voltarmos, responderemos por aqui."
)
DEFAULT_AUTO_MSG_INATIV_AVISO = (
    "Olá, {{nome_cliente}}! Você está há um tempo sem responder. "
    "Se não houver retorno, encerraremos este atendimento em breve. "
    "Responda aqui se ainda precisar de ajuda."
)
DEFAULT_AUTO_MSG_AVALIACAO = (
    "Como você avalia o atendimento?\n\n"
    "Responda com uma nota de *1* a *5*:\n"
    "1 — Péssimo\n2 — Ruim\n3 — Regular\n4 — Bom\n5 — Excelente"
)
DEFAULT_AUTO_MSG_AVALIACAO_OBRIGADO = (
    "Obrigado pela sua avaliação! Atendimento encerrado."
)
DEFAULT_AUTO_MSG_AVALIACAO_SEM_NOTA = (
    "Não foi possível registrar sua avaliação. O atendimento foi encerrado. "
    "Se precisar de algo mais, envie uma nova mensagem por aqui."
)
DEFAULT_AUTO_MSG_AVALIACAO_PULAR = (
    "Sem problema! Vamos abrir um novo atendimento com a sua mensagem."
)
DEFAULT_AUTO_MSG_AVALIACAO_TIMEOUT = (
    "O período para avaliar o atendimento encerrou. "
    "Se precisar de ajuda, envie uma nova mensagem por aqui."
)

# Mensagens desta fase não aparecem na conversa do atendente (só no WhatsApp do cliente).
EVENTOS_MENSAGEM_OCULTA_CONVERSA = frozenset(
    {
        "auto_avaliacao_solicitacao",
        "auto_avaliacao_obrigado",
        "auto_avaliacao_sem_nota",
        "auto_avaliacao_pular",
        "auto_avaliacao_timeout",
        "avaliacao_cliente_nota",
        "avaliacao_cliente_invalida",
    }
)


def resolver_nome_empresa_para_template(db: Session) -> str:
    """
    Nome da empresa para templates WhatsApp ({{nome_empresa}}).

    Prioridade: override em whatsapp_settings → nome fantasia → razão social → nome (empresa_sistema).
    Sempre relê whatsapp_settings do banco (evita objeto stale na sessão do webhook).
    """
    st = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if st:
        override = (getattr(st, "nome_empresa_exibicao", None) or "").strip()
        if override:
            return override
    row = db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()
    if row:
        for attr in ("nome_fantasia", "razao_social", "nome"):
            val = (getattr(row, attr, None) or "").strip()
            if val:
                return val
    return "nossa empresa"
