import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react'

import { consumeEventStream } from '../api/eventStream'

const POLL_MS = 6000

type Ouvinte = () => void

type RealtimeApi = {
  /** Assina o "algo mudou": polling de segurança + uma única conexão SSE por app. */
  assinar: (fn: Ouvinte) => () => void
}

const RealtimeContext = createContext<RealtimeApi | null>(null)

export function RealtimeProvider({ ativo, children }: { ativo: boolean; children: ReactNode }) {
  const ouvintes = useRef(new Set<Ouvinte>())

  const assinar = useCallback((fn: Ouvinte) => {
    ouvintes.current.add(fn)
    return () => {
      ouvintes.current.delete(fn)
    }
  }, [])

  useEffect(() => {
    if (!ativo) return
    const id = setInterval(() => {
      ouvintes.current.forEach((fn) => fn())
    }, POLL_MS)
    return () => clearInterval(id)
  }, [ativo])

  useEffect(() => {
    if (!ativo) return
    const ac = new AbortController()
    void consumeEventStream(() => {
      ouvintes.current.forEach((fn) => fn())
    }, ac.signal).catch(() => {
      /* polling cobre */
    })
    return () => ac.abort()
  }, [ativo])

  const api = useMemo(() => ({ assinar }), [assinar])
  return <RealtimeContext.Provider value={api}>{children}</RealtimeContext.Provider>
}

export function useRealtimeAssinar(): RealtimeApi['assinar'] | null {
  return useContext(RealtimeContext)?.assinar ?? null
}
