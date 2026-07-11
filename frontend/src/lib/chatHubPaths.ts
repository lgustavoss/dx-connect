export const CHAT_HUB_PATHS = {
  atendendo: '/chat/atendendo',
  espera: '/chat/espera',
  interno: '/chat/interno',
} as const

export type ChatHubModo = keyof typeof CHAT_HUB_PATHS

export function chatHubModoDePath(pathname: string): ChatHubModo {
  if (pathname.startsWith('/chat/interno') || pathname === CHAT_HUB_PATHS.interno) return 'interno'
  if (pathname.startsWith('/chat/espera')) return 'espera'
  if (pathname.startsWith('/chat/c/')) return 'atendendo'
  return 'atendendo'
}

export function chatWhatsappLink(chatId: number, from?: ChatHubModo) {
  return {
    pathname: `/chat/c/${chatId}`,
    search: from ? `?from=${from}` : '',
  }
}

export function chatInternoLink(conversaId: number) {
  return `/chat/interno/${conversaId}`
}
