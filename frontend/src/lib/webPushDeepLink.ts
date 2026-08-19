import { marcarTicketAtivo } from './ticketAtivo'
import { gravarChatAtivoSession } from './chatAtivo'

export type WebPushOpenPayload = {
  tipo?: string
  id?: number
  url_path?: string
}

/** Abre o chat/ticket certo a partir do clique na notificação (#694). */
export function aplicarAberturaWebPush(data: WebPushOpenPayload): string {
  const tipo = data.tipo || ''
  const id = Number(data.id)
  if (tipo.startsWith('chat.') && Number.isFinite(id) && id > 0) {
    gravarChatAtivoSession({ canal: 'whatsapp', id })
    return data.url_path || (tipo === 'chat.fila' ? '/chat/espera' : '/chat/atendendo')
  }
  if (tipo.startsWith('portal.chat.') && Number.isFinite(id) && id > 0) {
    gravarChatAtivoSession({ canal: 'portal', id })
    return data.url_path || '/chat/espera'
  }
  if (tipo.startsWith('ticket.') && Number.isFinite(id) && id > 0) {
    marcarTicketAtivo(id)
    return data.url_path || '/tickets'
  }
  return data.url_path || '/'
}
