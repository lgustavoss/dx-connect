import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { pushMesaPanelState, type MesaHistoryKind } from '../lib/mesaHistory'

/**
 * Garante `history.state` enquanto o painel está aberto e fecha no Voltar do browser (#699).
 * `onFecharPorBrowser` deve só limpar o item activo — sem `history.back()` (já ocorreu).
 */
export function useMesaPanelHistory(
  kind: MesaHistoryKind,
  aberto: boolean,
  onFecharPorBrowser: () => void,
): void {
  const { pathname } = useLocation()
  const onFecharRef = useRef(onFecharPorBrowser)
  onFecharRef.current = onFecharPorBrowser
  const abertoRef = useRef(aberto)
  abertoRef.current = aberto

  useEffect(() => {
    if (aberto) pushMesaPanelState(kind)
  }, [aberto, kind, pathname])

  useEffect(() => {
    const onPop = () => {
      if (abertoRef.current) onFecharRef.current()
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
}
