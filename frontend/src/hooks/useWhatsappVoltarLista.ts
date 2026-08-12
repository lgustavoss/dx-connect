import { useCallback } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { resolveWhatsappListFallback, WHATSAPP_LIST_PATHS } from '../lib/whatsappListReturn'

type VoltarListaApi = {
  /** Botão Voltar (#449): history.back no SPA quando possível; senão lista segura. */
  voltarLista: () => void
  /**
   * Esc / sair sem percorrer pilha de chats (#653): sempre lista de origem
   * (state / ?from= / Atendendo) — nunca navigate(-1).
   */
  sairParaListaSegura: () => void
}

/**
 * Navegação de saída da conversa WhatsApp.
 * Voltar UI pode usar histórico; Esc deve ir à lista segura (#653).
 */
export function useWhatsappVoltarLista(fallbackPath = WHATSAPP_LIST_PATHS.atendendo): VoltarListaApi {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  const sairParaListaSegura = useCallback(() => {
    navigate(
      resolveWhatsappListFallback(location.state, searchParams.get('from'), fallbackPath),
    )
  }, [navigate, location.state, searchParams, fallbackPath])

  const voltarLista = useCallback(() => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      navigate(-1)
      return
    }
    sairParaListaSegura()
  }, [navigate, sairParaListaSegura])

  return { voltarLista, sairParaListaSegura }
}
