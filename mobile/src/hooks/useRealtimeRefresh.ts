import { useEffect } from 'react'

import { consumeEventStream } from '../api/eventStream'

const POLL_MS = 6000

/** Polling de segurança + SSE quando a tela está em foco. */
export function useRealtimeRefresh(refresh: () => void, enabled: boolean) {
  useEffect(() => {
    if (!enabled) return
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh, enabled])

  useEffect(() => {
    if (!enabled) return
    const ac = new AbortController()
    void consumeEventStream(() => {
      refresh()
    }, ac.signal).catch(() => {
      /* polling cobre */
    })
    return () => ac.abort()
  }, [refresh, enabled])
}
