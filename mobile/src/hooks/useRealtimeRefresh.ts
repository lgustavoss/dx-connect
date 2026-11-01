import { useEffect } from 'react'

import { useRealtimeAssinar } from '../lib/realtime'

/** Recebe o sinal único de atualização (SSE + polling) do RealtimeProvider. */
export function useRealtimeRefresh(refresh: () => void, enabled: boolean) {
  const assinar = useRealtimeAssinar()

  useEffect(() => {
    if (!enabled || !assinar) return
    return assinar(refresh)
  }, [assinar, enabled, refresh])
}
