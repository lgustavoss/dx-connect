/** Chat ativo na mesa — só estado/API, sem id na URL do browser (#654). */

export type ChatAtivoCanal = 'whatsapp' | 'portal' | 'interno'

export type ChatAtivo = {
  canal: ChatAtivoCanal
  id: number
}

export const CHAT_ATIVO_SESSION_KEY = 'deskrudder-chat-ativo'

export function lerChatAtivoSession(): ChatAtivo | null {
  try {
    const raw = sessionStorage.getItem(CHAT_ATIVO_SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<ChatAtivo>
    if (
      (parsed.canal === 'whatsapp' || parsed.canal === 'portal' || parsed.canal === 'interno') &&
      typeof parsed.id === 'number' &&
      Number.isFinite(parsed.id) &&
      parsed.id > 0
    ) {
      return { canal: parsed.canal, id: parsed.id }
    }
  } catch {
    /* ignore */
  }
  return null
}

export function gravarChatAtivoSession(ativo: ChatAtivo | null): void {
  try {
    if (!ativo) {
      sessionStorage.removeItem(CHAT_ATIVO_SESSION_KEY)
      return
    }
    sessionStorage.setItem(CHAT_ATIVO_SESSION_KEY, JSON.stringify(ativo))
  } catch {
    /* ignore */
  }
}
