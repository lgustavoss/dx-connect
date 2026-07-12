export const WHATSAPP_LIST_PATHS = {
  atendendo: '/chat/atendendo',
  historico: '/whatsapp/historico',
  avaliacoes: '/whatsapp/avaliacoes',
} as const

export type WhatsappListOrigin = keyof typeof WHATSAPP_LIST_PATHS

export type WhatsappListReturnState = {
  whatsappListReturn?: string
}

const SCROLL_KEY_PREFIX = 'wpp-list-scroll:'

export function whatsappListScrollKey(origin: WhatsappListOrigin, returnPath: string): string {
  return `${SCROLL_KEY_PREFIX}${origin}:${returnPath}`
}

export function saveWhatsappListScroll(origin: WhatsappListOrigin, returnPath: string): void {
  try {
    sessionStorage.setItem(whatsappListScrollKey(origin, returnPath), String(window.scrollY))
  } catch {
    /* quota / modo privado */
  }
}

export function consumeWhatsappListScroll(origin: WhatsappListOrigin, returnPath: string): number | null {
  try {
    const key = whatsappListScrollKey(origin, returnPath)
    const raw = sessionStorage.getItem(key)
    sessionStorage.removeItem(key)
    if (!raw) return null
    const y = Number(raw)
    return Number.isFinite(y) && y >= 0 ? y : null
  } catch {
    return null
  }
}

export function whatsappConversaState(returnPath: string): WhatsappListReturnState {
  return { whatsappListReturn: returnPath }
}

export function whatsappConversaLink(chatId: number, returnPath: string, from?: WhatsappListOrigin) {
  return {
    pathname: `/chat/c/${chatId}`,
    search: from ? `?from=${from}` : '',
    state: whatsappConversaState(returnPath),
  }
}

export function resolveWhatsappListFallback(
  state: unknown,
  fromQuery: string | null,
  fallback = WHATSAPP_LIST_PATHS.atendendo,
): string {
  const st = state as WhatsappListReturnState | null
  if (st?.whatsappListReturn?.trim()) return st.whatsappListReturn.trim()
  const from = fromQuery?.trim().toLowerCase()
  if (from && from in WHATSAPP_LIST_PATHS) {
    return WHATSAPP_LIST_PATHS[from as WhatsappListOrigin]
  }
  return fallback
}

export function buildHistoricoReturnPath(filters: {
  busca: string
  atendenteId: number | ''
  desde: string
  ate: string
  estado: string
  offset: number
}): string {
  const p = new URLSearchParams()
  if (filters.busca.trim()) p.set('busca', filters.busca.trim())
  if (filters.atendenteId !== '') p.set('atendente_id', String(filters.atendenteId))
  if (filters.desde) p.set('desde', filters.desde)
  if (filters.ate) p.set('ate', filters.ate)
  if (filters.estado && filters.estado !== 'finalizados') p.set('estado', filters.estado)
  if (filters.offset > 0) p.set('offset', String(filters.offset))
  const qs = p.toString()
  return qs ? `${WHATSAPP_LIST_PATHS.historico}?${qs}` : WHATSAPP_LIST_PATHS.historico
}

export function buildAvaliacoesReturnPath(filters: {
  busca: string
  atendenteId: number | ''
  notaMin: number | ''
  desde: string
  ate: string
  incluirSemResposta: boolean
  offset: number
}): string {
  const p = new URLSearchParams()
  if (filters.busca.trim()) p.set('busca', filters.busca.trim())
  if (filters.atendenteId !== '') p.set('atendente_id', String(filters.atendenteId))
  if (filters.notaMin !== '') p.set('nota', String(filters.notaMin))
  if (filters.desde) p.set('desde', filters.desde)
  if (filters.ate) p.set('ate', filters.ate)
  if (filters.incluirSemResposta) p.set('incluir_sem_resposta', 'true')
  if (filters.offset > 0) p.set('offset', String(filters.offset))
  const qs = p.toString()
  return qs ? `${WHATSAPP_LIST_PATHS.avaliacoes}?${qs}` : WHATSAPP_LIST_PATHS.avaliacoes
}
