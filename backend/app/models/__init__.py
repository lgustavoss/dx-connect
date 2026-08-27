from app.models.rede import Rede
from app.models.empresa import Empresa
from app.models.tipo_negocio import TipoNegocio
from app.models.atendente import Atendente, AtendenteSetor
from app.models.ponto_batida import PontoBatida
from app.models.ponto_justificativa import PontoJustificativa
from app.models.ponto_hora_extra import PontoHoraExtra
from app.models.ponto_settings import PontoFeriado, PontoLocal, PontoSettings
from app.models.setor import Setor
from app.models.setor_distribuicao_round_robin import SetorDistribuicaoRoundRobin
from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketHistorico, TicketMensagem
from app.models.ticket_anexo import TicketAnexo
from app.models.ticket_read import TicketRead
from app.models.whatsapp_chat_read import WhatsappChatRead
from app.models.audit_log import AuditLog
from app.models.ibge_municipio import IbgeMunicipio
from app.models.app_cache_meta import AppCacheMeta
from app.models.whatsapp_chat import (
    WhatsappChat,
    WhatsappChatTicket,
    WhatsappMensagem,
    WhatsappMensagemReacao,
    WhatsappSettings,
)
from app.models.whatsapp_chat_demanda import WhatsappChatDemanda
from app.models.whatsapp_demanda_motivo_sugestao import WhatsappDemandaMotivoSugestao
from app.models.comercial_custo import CustoCatalogoItem, SalarioMinimoReferencia
from app.models.empresa_sistema import EmpresaSistema
from app.models.email_settings import EmailSettings
from app.models.protocol_sequence import ProtocolSequence
from app.models.email_inbound_received import EmailInboundReceived
from app.models.ticket_email_message_id import TicketEmailMessageId
from app.models.tenant import Tenant
from app.models.tenant_inbound_address import TenantInboundAddress
from app.models.password_reset_token import PasswordResetToken
from app.models.resposta_pronta import RespostaPronta
from app.models.ticket_vinculo import TicketVinculo
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.models.ticket_avaliacao import TicketAvaliacao, TicketCsatInvite
from app.models.atendente_notificacao import AtendenteNotificacaoPreferencias, NotificacaoEmailOutbox
from app.models.webhook_outbox import WebhookOutbox
from app.models.web_push import PushOutbox, PushSubscription
from app.models.routing_rule import RoutingRule
from app.models.business_calendar import BusinessCalendar
from app.models.sla_policy import SlaPolicy
from app.models.sla_alerta_emitido import SlaAlertaEmitido
from app.models.empresa_pdv import EmpresaPdv, PdvRotulo, PdvTipoAcessoRemoto
from app.models.kb import KbArticle, KbArticleFeedbackVote, KbArticleMotivoLink, KbArticleVersion, KbCategory, KbPortalSettings
from app.models.portal_chat import PortalChat, PortalChatRead as PortalChatReadRow, PortalMensagem
from app.models.portal_chat_demanda import PortalChatDemanda
from app.models.chat_interno import (
    ConversaInterna,
    ConversaInternaLeitura,
    ConversaInternaParticipante,
    MensagemInterna,
    MensagemInternaReacao,
    MensagemInternaOculta,
)
from app.models.crm import (
    CrmLead,
    CrmNegociacao,
    CrmNegociacaoAtividade,
    CrmNegociacaoCnpjLinha,
    FunilEstagio,
)
from app.models.comercial_proposta import Proposta, PropostaTemplate
from app.models.comercial_contrato import Contrato, ContratoPdf, ContratoPolitica, ContratoTemplate
from app.models.faturamento import Fatura
from app.models.implantacao_checklist import (
    ImplantacaoChecklistTemplate,
    ImplantacaoChecklistTemplateItem,
    TicketChecklistItem,
)
from app.models.cliente_saas import ClienteSaaS
from app.models.saas_setor import SaasSetor, saas_ops_setor
from app.models.saas_alerta_emitido import SaasAlertaEmitido
from app.models.lead_comercial import LeadComercial
from app.models.saas_plano import SaasModulo, SaasPlano, SaasPlanoModulo
from app.models.solicitacao_melhoria import (
    SolicitacaoMelhoria,
    SolicitacaoMelhoriaAnexo,
    SolicitacaoMelhoriaComentario,
    SolicitacaoMelhoriaHistorico,
)
from app.models.saas_solicitacao_produto import (
    SaasSolicitacaoProduto,
    SaasSolicitacaoProdutoAnexo,
    SaasSolicitacaoProdutoComentario,
)

__all__ = [
    "Rede",
    "Empresa",
    "TipoNegocio",
    "Setor",
    "SetorDistribuicaoRoundRobin",
    "Atendente",
    "AtendenteSetor",
    "SaasSetor",
    "PontoBatida",
    "PontoJustificativa",
    "PontoHoraExtra",
    "PontoSettings",
    "PontoLocal",
    "PontoFeriado",
    "FuncionarioRede",
    "FuncionarioRedeEmpresa",
    "StatusTicket",
    "Ticket",
    "TicketHistorico",
    "TicketMensagem",
    "TicketAnexo",
    "TicketRead",
    "WhatsappChatRead",
    "AuditLog",
    "IbgeMunicipio",
    "AppCacheMeta",
    "WhatsappSettings",
    "WhatsappChat",
    "WhatsappMensagem",
    "WhatsappMensagemReacao",
    "WhatsappChatTicket",
    "WhatsappChatDemanda",
    "WhatsappDemandaMotivoSugestao",
    "SalarioMinimoReferencia",
    "CustoCatalogoItem",
    "EmpresaSistema",
    "EmailSettings",
    "ProtocolSequence",
    "EmailInboundReceived",
    "TicketEmailMessageId",
    "Tenant",
    "TenantInboundAddress",
    "PasswordResetToken",
    "RespostaPronta",
    "TicketVinculo",
    "TicketNatureza",
    "TicketMotivo",
    "TicketAvaliacao",
    "TicketCsatInvite",
    "AtendenteNotificacaoPreferencias",
    "NotificacaoEmailOutbox",
    "WebhookOutbox",
    "PushSubscription",
    "PushOutbox",
    "RoutingRule",
    "BusinessCalendar",
    "SlaPolicy",
    "SlaAlertaEmitido",
    "PdvRotulo",
    "PdvTipoAcessoRemoto",
    "EmpresaPdv",
    "KbCategory",
    "KbArticle",
    "KbArticleFeedbackVote",
    "KbArticleMotivoLink",
    "KbArticleVersion",
    "KbPortalSettings",
    "PortalChat",
    "PortalMensagem",
    "PortalChatReadRow",
    "ConversaInterna",
    "ConversaInternaParticipante",
    "MensagemInterna",
    "MensagemInternaReacao",
    "MensagemInternaOculta",
    "ConversaInternaLeitura",
    "FunilEstagio",
    "CrmLead",
    "CrmNegociacao",
    "CrmNegociacaoCnpjLinha",
    "CrmNegociacaoAtividade",
    "PropostaTemplate",
    "Proposta",
    "ContratoTemplate",
    "Contrato",
    "Fatura",
    "ContratoPdf",
    "ContratoPolitica",
    "ImplantacaoChecklistTemplate",
    "ImplantacaoChecklistTemplateItem",
    "TicketChecklistItem",
    "ClienteSaaS",
    "SaasAlertaEmitido",
    "LeadComercial",
    "SaasSolicitacaoProduto",
    "SaasSolicitacaoProdutoAnexo",
    "SaasSolicitacaoProdutoComentario",
]
