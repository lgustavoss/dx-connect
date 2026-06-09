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
