from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class WhatsappSettings(Base):
    """Configuração singleton da integração Evolution (uma linha)."""

    __tablename__ = "whatsapp_settings"

    id = Column(Integer, primary_key=True, index=True)
    evolution_base_url = Column(String(500), nullable=True)
    evolution_instance_name = Column(String(120), nullable=True)
    evolution_api_key = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    # Templates de mensagens automáticas (opcional; texto vazio = não envia).
    auto_msg_espera_ativa = Column(Boolean, nullable=False, default=True)
    auto_msg_espera_texto = Column(Text, nullable=True)
    auto_msg_assumido_ativa = Column(Boolean, nullable=False, default=True)
    auto_msg_assumido_texto = Column(Text, nullable=True)
    auto_msg_encerrado_ativa = Column(Boolean, nullable=False, default=True)
    auto_msg_encerrado_texto = Column(Text, nullable=True)
    # Fora do horário
    auto_msg_fora_horario_ativa = Column(Boolean, nullable=False, default=True)
    auto_msg_fora_horario_texto = Column(Text, nullable=True)
    # Horário de atendimento: HH:MM (local timezone)
    horario_inicio = Column(String(5), nullable=True)
    horario_fim = Column(String(5), nullable=True)
    horario_timezone = Column(String(64), nullable=False, default="America/Sao_Paulo")
    # Horário por dia da semana (JSON): substitui horario_inicio/horario_fim quando presente.
    horario_semana_json = Column(Text, nullable=True)
    # Se True, considera feriados nacionais (Brasil) como "fechado o dia todo".
    usar_feriados_nacionais = Column(Boolean, nullable=False, default=False)
    # Nome amigável da empresa para templates (ex.: "DX Connect" ou nome do cliente/negócio).
    nome_empresa_exibicao = Column(String(255), nullable=True)
    # Encerramento automático por inatividade do cliente (chat em atendimento).
    inativ_encerramento_ativa = Column(Boolean, nullable=False, default=False)
    inativ_aviso_minutos = Column(Integer, nullable=True)
    inativ_encerramento_apos_aviso_minutos = Column(Integer, nullable=True)
    auto_msg_inativ_aviso_ativa = Column(Boolean, nullable=False, default=True)
    auto_msg_inativ_aviso_texto = Column(Text, nullable=True)
    avaliacao_ativa = Column(Boolean, nullable=False, default=False)
    # Janela após encerrar para o cliente enviar nota 1–5 (depois finaliza sozinho).
    avaliacao_janela_minutos = Column(Integer, nullable=False, default=30)
    auto_msg_avaliacao_ativa = Column(Boolean, nullable=False, default=True)
    auto_msg_avaliacao_texto = Column(Text, nullable=True)
    auto_msg_avaliacao_obrigado_texto = Column(Text, nullable=True)
    auto_msg_avaliacao_timeout_texto = Column(Text, nullable=True)
    auto_msg_avaliacao_pular_texto = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class WhatsappChat(Base):
    __tablename__ = "whatsapp_chats"

    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String(32), unique=True, nullable=False, index=True)
    wa_id = Column(String(64), nullable=False, index=True)
    cliente_nome = Column(String(255), nullable=True)
    estado = Column(String(40), nullable=False, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="SET NULL"), nullable=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    atendimento_inicio_at = Column(DateTime(timezone=True), nullable=True)
    encerramento_at = Column(DateTime(timezone=True), nullable=True)
    avaliacao_nota = Column(Integer, nullable=True)
    avaliacao_respondida_at = Column(DateTime(timezone=True), nullable=True)
    avaliacao_solicitada = Column(Boolean, nullable=False, default=False)
    funcionario_rede_id = Column(
        Integer, ForeignKey("funcionarios_rede.id", ondelete="SET NULL"), nullable=True, index=True
    )
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True, index=True)
    inatividade_pausada = Column(Boolean, nullable=False, default=False, server_default="false")
    inatividade_retomada_em = Column(DateTime(timezone=True), nullable=True)
    # Após encerramento por inatividade: responsável deve registar (ou confirmar sem) demanda.
    classificacao_demanda_pendente = Column(Boolean, nullable=False, default=False, server_default="false")
    # Cache da foto de perfil WhatsApp do contacto (#630 lote 1).
    foto_perfil_url = Column(Text, nullable=True)
    foto_perfil_atualizada_em = Column(DateTime(timezone=True), nullable=True)

    atendente = relationship("Atendente", backref="whatsapp_chats_atendidos")
    setor = relationship("Setor", backref="whatsapp_chats")
    funcionario_rede = relationship("FuncionarioRede", backref="whatsapp_chats")
    empresa = relationship("Empresa", backref="whatsapp_chats")
    mensagens = relationship(
        "WhatsappMensagem",
        back_populates="chat",
        order_by="WhatsappMensagem.created_at",
    )
    vinculos_tickets = relationship("WhatsappChatTicket", back_populates="chat")
    demandas = relationship(
        "WhatsappChatDemanda",
        back_populates="chat",
        order_by="WhatsappChatDemanda.created_at",
    )


class WhatsappMensagem(Base):
    __tablename__ = "whatsapp_mensagens"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    direcao = Column(String(20), nullable=False)
    corpo = Column(Text, nullable=False)
    # texto | imagem | audio | video | documento | figurinha — None = legado (tratar como texto)
    tipo_midia = Column(String(24), nullable=True)
    mimetype = Column(String(128), nullable=True)
    # Nome do ficheiro dentro de WHATSAPP_MEDIA_DIR (apenas inbound com mídia obtida da Evolution)
    midia_nome_arquivo = Column(String(500), nullable=True)
    # Identifica mensagens automáticas disparadas pelo sistema (evita duplicação e ajuda auditoria).
    evento_sistema = Column(String(40), nullable=True, index=True)
    wa_message_id = Column(String(128), nullable=True, index=True)
    # Mensagem citada (reply do WhatsApp): id da mensagem na origem + texto de pré-visualização
    quoted_wa_message_id = Column(String(128), nullable=True)
    quoted_corpo_preview = Column(String(500), nullable=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    # pendente | enviada | entregue | lida | erro — apenas outbound ao cliente
    status_entrega = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # #630 lote 3 — editar / apagar para todos (timestamps; corpo vira placeholder ao apagar)
    editada_em = Column(DateTime(timezone=True), nullable=True)
    apagada_em = Column(DateTime(timezone=True), nullable=True)

    chat = relationship("WhatsappChat", back_populates="mensagens")
    atendente = relationship("Atendente", backref="whatsapp_mensagens_enviadas")
    reacoes = relationship(
        "WhatsappMensagemReacao",
        back_populates="mensagem",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("wa_message_id", name="uq_whatsapp_mensagens_wa_message_id"),)


class WhatsappMensagemReacao(Base):
    """Uma reação por origem (cliente ou mesa) na mensagem alvo (#630 lote 2)."""

    __tablename__ = "whatsapp_mensagem_reacoes"
    __table_args__ = (
        UniqueConstraint("mensagem_id", "origem", name="uq_whatsapp_mensagem_reacoes_mensagem_origem"),
    )

    id = Column(Integer, primary_key=True, index=True)
    mensagem_id = Column(
        Integer, ForeignKey("whatsapp_mensagens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # cliente | atendente
    origem = Column(String(20), nullable=False)
    emoji = Column(String(16), nullable=False)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mensagem = relationship("WhatsappMensagem", back_populates="reacoes")
    atendente = relationship("Atendente", backref="whatsapp_mensagem_reacoes")


class WhatsappChatTicket(Base):
    __tablename__ = "whatsapp_chat_tickets"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("WhatsappChat", back_populates="vinculos_tickets")
    ticket = relationship("Ticket", backref="whatsapp_vinculos")
    atendente = relationship("Atendente", backref="whatsapp_vinculos_criados")

    __table_args__ = (UniqueConstraint("chat_id", "ticket_id", name="uq_whatsapp_chat_ticket_par"),)
