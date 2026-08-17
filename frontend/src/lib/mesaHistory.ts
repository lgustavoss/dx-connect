/**
 * Voltar nativo fecha o painel sem pôr id na URL (#699).
 * `pushState` no mesmo path; `popstate` limpa o item activo.
 * Não grava o id no histórico — Forward não reabre conversa encerrada (#653).
 */

export const MESA_HISTORY_FLAG = 'deskrudderMesa'

export type MesaHistoryKind = 'chat' | 'ticket' | 'portal-ticket' | 'portal-chat'

type MesaHistoryState = {
  [MESA_HISTORY_FLAG]: true
  kind: MesaHistoryKind
}

function asRecord(state: unknown): Record<string, unknown> {
  return state != null && typeof state === 'object' && !Array.isArray(state)
    ? (state as Record<string, unknown>)
    : {}
}

export function isMesaHistoryState(state: unknown): state is MesaHistoryState {
  return asRecord(state)[MESA_HISTORY_FLAG] === true
}

/** Abre o painel: uma entrada extra (mesmo URL). Trocar A→B faz replace, não empilha. */
export function pushMesaPanelState(kind: MesaHistoryKind): void {
  if (typeof window === 'undefined') return
  const current = asRecord(window.history.state)
  const next = { ...current, [MESA_HISTORY_FLAG]: true, kind }
  if (current[MESA_HISTORY_FLAG] === true) {
    window.history.replaceState(next, '')
  } else {
    window.history.pushState(next, '')
  }
}

/** Fecha via UI/Esc: consome a entrada extra. Devolve true se chamou `history.back()`. */
export function popMesaPanelState(): boolean {
  if (typeof window === 'undefined') return false
  if (!isMesaHistoryState(window.history.state)) return false
  window.history.back()
  return true
}
