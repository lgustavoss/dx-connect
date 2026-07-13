import { portalChats, whatsappChats, type PortalChats, type WhatsappChats } from '../api/client'
export type ChatDemanda = {
  id: number
  chat_id?: number
  natureza_id: number
  natureza_nome?: string | null
  motivo_id?: number | null
  motivo_nome?: string | null
  desfecho: string
  ticket_id?: number | null
  descricao_curta?: string | null
  atendente_id?: number | null
  atendente_nome?: string | null
  created_at?: string | null
}

export type ChatMensagemTimeline = {
  id: number
  direcao?: string
  corpo?: string | null
  evento_sistema?: string | null
  created_at?: string | null
  atendente_nome?: string | null
}

export type DemandaFormPayload = {
  natureza_id: number
  motivo_id?: number | null
  descricao_curta?: string | null
}

export type ChatDemandasApi = {
  listarDemandas: (chatId: number) => Promise<ChatDemanda[]>
  registrarDemanda: (chatId: number, data: DemandaFormPayload) => Promise<ChatDemanda>
  atualizarDemanda: (chatId: number, demandaId: number, data: DemandaFormPayload) => Promise<ChatDemanda>
  excluirDemanda: (chatId: number, demandaId: number) => Promise<void>
}

export type ChatEncerrarApi<TChat extends { estado: string } = { estado: string }> = ChatDemandasApi & {
  encerrar: (chatId: number) => Promise<TChat>
}

export const portalDemandasApi: ChatEncerrarApi<PortalChats.Chat> = {
  listarDemandas: (id) => portalChats.demandas(id),
  registrarDemanda: (id, data) => portalChats.registrarDemanda(id, data),
  atualizarDemanda: (id, demandaId, data) => portalChats.atualizarDemanda(id, demandaId, data),
  excluirDemanda: (id, demandaId) => portalChats.excluirDemanda(id, demandaId),
  encerrar: (id) => portalChats.encerrar(id),
}

export const whatsappDemandasApi: ChatEncerrarApi<WhatsappChats.Chat> = {
  listarDemandas: (id) => whatsappChats.demandas(id),
  registrarDemanda: (id, data) => whatsappChats.registrarDemanda(id, data),
  atualizarDemanda: (id, demandaId, data) => whatsappChats.atualizarDemanda(id, demandaId, data),
  excluirDemanda: (id, demandaId) => whatsappChats.excluirDemanda(id, demandaId),
  encerrar: (id) => whatsappChats.encerrar(id),
}

export type WhatsappDemanda = WhatsappChats.Demanda
export type PortalDemanda = PortalChats.Demanda
