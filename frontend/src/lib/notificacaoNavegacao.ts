import type { Notificacoes } from '../api/client'
import { gravarChatAtivoSession } from './chatAtivo'
import { marcarTicketAtivo } from './ticketAtivo'

/**
 * Grava ticket/chat ativo antes de seguir o `href` estável (#697).
 * Chamar no `onClick` do sininho — nunca no render da lista.
 */
export function aplicarAtivoDaNotificacao(item: Notificacoes.Item): void {
  if (item.ticket_id != null && item.ticket_id > 0) {
    marcarTicketAtivo(item.ticket_id)
  }
  if (item.chat_id != null && item.chat_id > 0) {
    gravarChatAtivoSession({ canal: 'whatsapp', id: item.chat_id })
  }
  if (item.conversa_id != null && item.conversa_id > 0) {
    gravarChatAtivoSession({ canal: 'interno', id: item.conversa_id })
  }
}
