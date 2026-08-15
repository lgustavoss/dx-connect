import { gravarChatAtivoSession, type ChatAtivoCanal } from './chatAtivo'

export const CHAT_HUB_PATHS = {
  atendendo: '/chat/atendendo',
  espera: '/chat/espera',
  contatos: '/chat/contatos',
  interno: '/chat/interno',
} as const

export type ChatHubModo = keyof typeof CHAT_HUB_PATHS

/** Path da aba do hub — sem id de conversa (#654). */
export function chatHubPathParaModo(from?: ChatHubModo | null): string {
  if (from === 'espera') return CHAT_HUB_PATHS.espera
  if (from === 'contatos') return CHAT_HUB_PATHS.contatos
  if (from === 'interno') return CHAT_HUB_PATHS.interno
  return CHAT_HUB_PATHS.atendendo
}

/**
 * Modo da aba a partir do path.
 * `?from=` em rotas legadas `/chat/c/:id` ainda é lido nos redirects.
 */
export function chatHubModoDePath(pathname: string, search?: string): ChatHubModo {
  if (pathname.startsWith('/chat/interno') || pathname === CHAT_HUB_PATHS.interno) return 'interno'
  if (pathname.startsWith('/chat/espera')) return 'espera'
  if (pathname.startsWith('/chat/contatos')) return 'contatos'
  const from = search
    ? new URLSearchParams(search.startsWith('?') ? search.slice(1) : search).get('from')
    : null
  if (from === 'espera') return 'espera'
  if (from === 'contatos') return 'contatos'
  if (from === 'interno') return 'interno'
  return 'atendendo'
}

/**
 * Abre WhatsApp no hub: grava id na sessão e devolve path estável (#654).
 * Chamar no click / navigate (não em render de lista).
 */
export function chatWhatsappLink(chatId: number, from?: ChatHubModo) {
  gravarChatAtivoSession({ canal: 'whatsapp', id: chatId })
  return {
    pathname: chatHubPathParaModo(from),
    search: '',
  }
}

export function chatPortalLink(chatId: number, from?: ChatHubModo) {
  gravarChatAtivoSession({ canal: 'portal', id: chatId })
  return {
    pathname: chatHubPathParaModo(from === 'espera' ? 'espera' : 'atendendo'),
    search: '',
  }
}

export function chatInternoLink(conversaId: number) {
  gravarChatAtivoSession({ canal: 'interno', id: conversaId })
  return CHAT_HUB_PATHS.interno
}

export function chatAtivoIgual(
  ativo: { canal: ChatAtivoCanal; id: number } | null | undefined,
  canal: ChatAtivoCanal,
  id: number,
): boolean {
  return Boolean(ativo && ativo.canal === canal && ativo.id === id)
}
