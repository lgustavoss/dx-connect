import { whatsappChats } from '../api/client'

export const whatsappService = {
  // 📥 LISTAS
  async getFila() {
    return whatsappChats.fila()
  },

  async getMeus() {
    return whatsappChats.meus()
  },

  async getChat(id: number) {
    return whatsappChats.get(id)
  },

  async getMensagens(chatId: number) {
    return whatsappChats.mensagens(chatId)
  },

  async getHistorico(params: { offset: number; limit: number }) {
    return whatsappChats.encerrados(params)
  },

  // ⚡ AÇÕES
  async assumir(chatId: number) {
    return whatsappChats.assumir(chatId)
  },

  async enviar(chatId: number, texto: string) {
    return whatsappChats.enviar(chatId, texto)
  },

  async encerrar(chatId: number) {
    return whatsappChats.encerrar(chatId)
  },

  async marcarVisto(chatId: number) {
    return whatsappChats.marcarVisto(chatId)
  },

  async transferir(chatId: number, payload: {
    setor_id: number
    atendente_id: number | null
  }) {
    return whatsappChats.transferir(chatId, payload)
  },

  async vincularTicket(chatId: number, ticketId: number) {
    return whatsappChats.vincularTicket(chatId, ticketId)
  },

  async abrirTicket(chatId: number, payload: {
    empresa_id: number
    setor_id: number
    assunto: string
    descricao: string | null
  }) {
    return whatsappChats.abrirTicket(chatId, payload)
  },

  async comentarInterno(chatId: number, texto: string) {
    return whatsappChats.comentarInterno(chatId, texto)
  }
}