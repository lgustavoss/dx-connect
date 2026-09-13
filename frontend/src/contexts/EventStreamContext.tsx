import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  EVENT_STREAM_MAX_FAILURES,
  nextReconnectDelayMs,
  runEventStreamLoop,
  sleepMs,
  type RealtimeEnvelope,
  type RealtimeEventHandler,
} from '../api/eventStream'
import { bindCapacitorAppState } from '../lib/capacitorNative'

type ListenerMap = Map<string, Set<RealtimeEventHandler>>

interface EventStreamContextValue {
  connected: boolean
  useFallback: boolean
  subscribe: (type: string, handler: RealtimeEventHandler) => () => void
  /** Força novo ciclo SSE (ex.: ao voltar do 2º plano no APK). */
  restartStream: () => void
}

const EventStreamContext = createContext<EventStreamContextValue | null>(null)

export function EventStreamProvider({
  enabled,
  children,
}: {
  enabled: boolean
  children: ReactNode
}) {
  const listenersRef = useRef<ListenerMap>(new Map())
  const [connected, setConnected] = useState(false)
  const [useFallback, setUseFallback] = useState(false)
  const [streamEpoch, setStreamEpoch] = useState(0)

  const dispatch = useCallback((event: RealtimeEnvelope) => {
    const handlers = listenersRef.current.get(event.type)
    handlers?.forEach((handler) => {
      try {
        handler(event.payload, event)
      } catch (err) {
        if (import.meta.env.DEV) {
          console.warn('[SSE] Erro em listener', event.type, err)
        }
      }
    })
    if (event.type !== 'ping') {
      const wildcard = listenersRef.current.get('*')
      wildcard?.forEach((handler) => {
        try {
          handler(event.payload, event)
        } catch {
          /* ignore */
        }
      })
    }
  }, [])

  const subscribe = useCallback((type: string, handler: RealtimeEventHandler) => {
    const map = listenersRef.current
    let set = map.get(type)
    if (!set) {
      set = new Set()
      map.set(type, set)
    }
    set.add(handler)
    return () => {
      set?.delete(handler)
      if (set && set.size === 0) {
        map.delete(type)
      }
    }
  }, [])

  const restartStream = useCallback(() => {
    setUseFallback(false)
    setStreamEpoch((n) => n + 1)
  }, [])

  useEffect(() => {
    return bindCapacitorAppState((isActive) => {
      if (isActive && enabled) {
        // Lock/unlock ou OEM matou o WebView: sai do fallback permanente e reconecta
        restartStream()
      }
    })
  }, [enabled, restartStream])

  useEffect(() => {
    if (!enabled) {
      setConnected(false)
      setUseFallback(false)
      return
    }

    const abort = new AbortController()
    let failureCount = 0
    let disposed = false

    const connectLoop = async () => {
      while (!disposed && !abort.signal.aborted) {
        try {
          await runEventStreamLoop({
            signal: abort.signal,
            onEvent: dispatch,
            onConnected: () => {
              failureCount = 0
              setConnected(true)
              setUseFallback(false)
            },
            onError: (err) => {
              if (import.meta.env.DEV) {
                console.warn('[SSE] Erro de conexão:', err.message)
              }
            },
          })
          if (disposed || abort.signal.aborted) break
          failureCount += 1
        } catch (err) {
          if (disposed || abort.signal.aborted) break
          if (err instanceof DOMException && err.name === 'AbortError') break
          failureCount += 1
          if (import.meta.env.DEV) {
            const msg = err instanceof Error ? err.message : String(err)
            console.warn('[SSE] Falha', failureCount, msg)
          }
        }

        setConnected(false)

        if (failureCount >= EVENT_STREAM_MAX_FAILURES) {
          setUseFallback(true)
          if (import.meta.env.DEV) {
            console.warn('[SSE] Fallback para polling após', failureCount, 'falhas')
          }
          break
        }

        try {
          await sleepMs(nextReconnectDelayMs(failureCount), abort.signal)
        } catch {
          break
        }
      }
    }

    void connectLoop()

    return () => {
      disposed = true
      abort.abort()
      setConnected(false)
    }
  }, [enabled, dispatch, streamEpoch])

  const value = useMemo(
    () => ({ connected, useFallback, subscribe, restartStream }),
    [connected, useFallback, subscribe, restartStream],
  )

  return <EventStreamContext.Provider value={value}>{children}</EventStreamContext.Provider>
}

/** Consome o stream SSE global (Provider no Layout). */
export function useEventStream(): EventStreamContextValue {
  const ctx = useContext(EventStreamContext)
  if (!ctx) {
    throw new Error('useEventStream deve ser usado dentro de EventStreamProvider')
  }
  return ctx
}

/** Opcional: retorna null se Provider não estiver montado (telas públicas). */
export function useEventStreamOptional(): EventStreamContextValue | null {
  return useContext(EventStreamContext)
}
