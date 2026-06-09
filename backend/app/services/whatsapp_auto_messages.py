"""Textos padrão das mensagens automáticas WhatsApp (espelham o frontend ConfigWhatsapp)."""

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
