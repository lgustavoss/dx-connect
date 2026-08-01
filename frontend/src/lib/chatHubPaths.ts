export const CHAT_HUB_PATHS = {
  atendendo: '/chat/atendendo',
  espera: '/chat/espera',
  contatos: '/chat/contatos',
  interno: '/chat/interno',
} as const

export type ChatHubModo = keyof typeof CHAT_HUB_PATHS

/** `search` opcional (ex. `?from=espera`) — ao visualizar chat da fila, mantém modo Aguardando (#625). */
export function chatHubModoDePath(pathname: string, search?: string): ChatHubModo {
  if (pathname.startsWith('/chat/interno') || pathname === CHAT_HUB_PATHS.interno) return 'interno'
  if (pathname.startsWith('/chat/espera')) return 'espera'
  if (pathname.startsWith('/chat/contatos')) return 'contatos'
  const from = search
    ? new URLSearchParams(search.startsWith('?') ? search.slice(1) : search).get('from')
    : null
  if (
    from === 'espera' &&
    (pathname.startsWith('/chat/c/') || pathname.startsWith('/chat/portal/'))
  ) {
    return 'espera'
  }
  return 'atendendo'
}

export function chatWhatsappLink(chatId: number, from?: ChatHubModo) {
  return {
    pathname: `/chat/c/${chatId}`,
    search: from ? `?from=${from}` : '',
  }
}

export function chatPortalLink(chatId: number, from?: ChatHubModo) {
  return {
    pathname: `/chat/portal/${chatId}`,
    search: from ? `?from=${from}` : '',
  }
}

export function chatInternoLink(conversaId: number) {
  return `/chat/interno/${conversaId}`
}
