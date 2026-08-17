/** Chamado / chat aberto no portal — sem id na URL (#700). */

export const PORTAL_TICKETS_PATH = '/portal/tickets'
export const PORTAL_CHATS_PATH = '/portal/chats'

export const PORTAL_TICKET_ATIVO_SESSION_KEY = 'deskrudder-portal-ticket-ativo'
export const PORTAL_CHAT_ATIVO_SESSION_KEY = 'deskrudder-portal-chat-ativo'

export const PORTAL_TICKET_ATIVO_EVENT = 'deskrudder-portal-ticket-ativo'
export const PORTAL_CHAT_ATIVO_EVENT = 'deskrudder-portal-chat-ativo'

function lerId(key: string): number | null {
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return null
    const id = Number(raw)
    return Number.isFinite(id) && id > 0 ? id : null
  } catch {
    return null
  }
}

function gravarId(key: string, eventName: string, id: number | null): void {
  try {
    if (id == null || !Number.isFinite(id) || id <= 0) {
      sessionStorage.removeItem(key)
    } else {
      sessionStorage.setItem(key, String(id))
    }
  } catch {
    /* quota / modo privado */
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(eventName))
  }
}

export function lerPortalTicketAtivoSession(): number | null {
  return lerId(PORTAL_TICKET_ATIVO_SESSION_KEY)
}

export function gravarPortalTicketAtivoSession(id: number | null): void {
  gravarId(PORTAL_TICKET_ATIVO_SESSION_KEY, PORTAL_TICKET_ATIVO_EVENT, id)
}

export function lerPortalChatAtivoSession(): number | null {
  return lerId(PORTAL_CHAT_ATIVO_SESSION_KEY)
}

export function gravarPortalChatAtivoSession(id: number | null): void {
  gravarId(PORTAL_CHAT_ATIVO_SESSION_KEY, PORTAL_CHAT_ATIVO_EVENT, id)
}
