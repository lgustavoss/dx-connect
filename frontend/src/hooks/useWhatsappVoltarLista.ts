import { useCallback } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { useChatHubOpcional } from '../contexts/ChatHubContext'
import { CHAT_HUB_PATHS } from '../lib/chatHubPaths'
import {
  resolveWhatsappListFallback,
  WHATSAPP_LIST_PATHS,
  type WhatsappListReturnState,
} from '../lib/whatsappListReturn'

type VoltarListaApi = {
  /** Botão Voltar: fecha o painel; se veio de Histórico/etc., regressa a essa lista. */
  voltarLista: () => void
  /**
   * Esc / sair sem percorrer pilha de chats (#653): sempre lista de origem
   * (state / ?from= / Atendendo) — nunca navigate(-1).
   */
  sairParaListaSegura: () => void
}

function estaNaAbaDoHub(pathname: string): boolean {
  return (Object.values(CHAT_HUB_PATHS) as string[]).some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  )
}

/**
 * Navegação de saída da conversa WhatsApp.
 * Com URL fixa (#654) o pathname já é a aba: Voltar só fecha o painel, senão
 * o history.back saía do módulo chat.
 */
export function useWhatsappVoltarLista(fallbackPath = WHATSAPP_LIST_PATHS.atendendo): VoltarListaApi {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const hub = useChatHubOpcional()
  const fecharChat = hub?.fecharChat

  const sairParaListaSegura = useCallback(() => {
    const consumiuHistorico = fecharChat?.() === true
    if (consumiuHistorico) return
    const destino = resolveWhatsappListFallback(location.state, searchParams.get('from'), fallbackPath)
    if (destino === location.pathname || (estaNaAbaDoHub(location.pathname) && destino.startsWith('/chat/'))) {
      return
    }
    navigate(destino)
  }, [fecharChat, navigate, location.state, location.pathname, searchParams, fallbackPath])

  const voltarLista = useCallback(() => {
    const consumiuHistorico = fecharChat?.() === true
    if (consumiuHistorico) return
    const returnPath = (location.state as WhatsappListReturnState | null)?.whatsappListReturn?.trim()
    if (returnPath && returnPath !== location.pathname) {
      navigate(returnPath)
      return
    }
    if (estaNaAbaDoHub(location.pathname)) return
    sairParaListaSegura()
  }, [fecharChat, location.pathname, location.state, navigate, sairParaListaSegura])

  return { voltarLista, sairParaListaSegura }
}
