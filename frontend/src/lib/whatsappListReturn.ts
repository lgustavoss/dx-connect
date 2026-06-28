export const WHATSAPP_LIST_PATHS = {
  atendendo: '/whatsapp/atendendo',
  historico: '/whatsapp/historico',
  avaliacoes: '/whatsapp/avaliacoes',
} as const

export type WhatsappListOrigin = keyof typeof WHATSAPP_LIST_PATHS

export type WhatsappListReturnState = {
  whatsappListReturn?: string
}

export function whatsappConversaState(returnPath: string): WhatsappListReturnState {
  return { whatsappListReturn: returnPath }
}

export function whatsappConversaLink(chatId: number, returnPath: string, from?: WhatsappListOrigin) {
  return {
    pathname: `/whatsapp/c/${chatId}`,
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
