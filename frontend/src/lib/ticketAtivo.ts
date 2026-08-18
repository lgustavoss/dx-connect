/** Ticket aberto na listagem — sem id na URL do browser (#655). */

import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

export const TICKETS_PATH = '/tickets'

export const TICKET_ATIVO_SESSION_KEY = 'deskrudder-ticket-ativo'

export function lerTicketAtivoSession(): number | null {
  try {
    const raw = sessionStorage.getItem(TICKET_ATIVO_SESSION_KEY)
    if (!raw) return null
    const id = Number(raw)
    return Number.isFinite(id) && id > 0 ? id : null
  } catch {
    return null
  }
}

export function gravarTicketAtivoSession(id: number | null): void {
  try {
    if (id == null || !Number.isFinite(id) || id <= 0) {
      sessionStorage.removeItem(TICKET_ATIVO_SESSION_KEY)
    } else {
      sessionStorage.setItem(TICKET_ATIVO_SESSION_KEY, String(id))
    }
  } catch {
    /* quota / modo privado */
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(TICKET_ATIVO_EVENT))
  }
}

export const TICKET_ATIVO_EVENT = 'deskrudder-ticket-ativo'

/**
 * Marca o ticket como aberto antes de navegar. Usar no `onClick` do link —
 * nunca no render da lista.
 */
export function marcarTicketAtivo(id: number): void {
  gravarTicketAtivoSession(id)
}

/** Abre o ticket na listagem: guarda o id e mantém a URL em `/tickets`. */
export function useAbrirTicket() {
  const navigate = useNavigate()
  return useCallback(
    (id: number) => {
      gravarTicketAtivoSession(id)
      navigate(TICKETS_PATH)
    },
    [navigate],
  )
}
