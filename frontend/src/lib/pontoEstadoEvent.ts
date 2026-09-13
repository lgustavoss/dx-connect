import type { Ponto } from '../api/client'

/** Chip do header e Meu ponto partilham o mesmo estado após batida (#1066). */
export const PONTO_ESTADO_EVENT = 'deskrudder-ponto-estado'

export function avisarPontoEstadoMudou(estado?: Ponto.EstadoMe | null): void {
  window.dispatchEvent(new CustomEvent(PONTO_ESTADO_EVENT, { detail: estado ?? undefined }))
}
