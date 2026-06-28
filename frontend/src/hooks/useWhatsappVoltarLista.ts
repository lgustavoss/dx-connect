import { useCallback } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { resolveWhatsappListFallback, WHATSAPP_LIST_PATHS } from '../lib/whatsappListReturn'

/**
 * Volta à lista WhatsApp de origem (#449): history.back() no SPA quando possível;
 * senão state whatsappListReturn, query ?from= ou atendimento.
 */
export function useWhatsappVoltarLista(fallbackPath = WHATSAPP_LIST_PATHS.atendendo) {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  return useCallback(() => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      navigate(-1)
      return
    }
    navigate(
      resolveWhatsappListFallback(location.state, searchParams.get('from'), fallbackPath),
    )
  }, [navigate, location.state, searchParams, fallbackPath])
}
