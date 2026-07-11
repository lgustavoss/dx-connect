import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { chatInterno, type ChatInterno } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { useEventStream } from './EventStreamContext'
import { useToast } from '../components/ui/Toast'
import type { FiltroInboxChatInterno } from '../lib/chatInternoUtils'

type ChatInternoContextValue = {
  conversas: ChatInterno.ConversaInbox[]
  filtradas: ChatInterno.ConversaInbox[]
  filtro: FiltroInboxChatInterno
  setFiltro: (f: FiltroInboxChatInterno) => void
  loading: boolean
  erro: boolean
  carregar: (silent?: boolean) => Promise<void>
  obterConversa: (id: number) => ChatInterno.ConversaInbox | undefined
}

const ChatInternoContext = createContext<ChatInternoContextValue | null>(null)

export function ChatInternoProvider({ children }: { children: ReactNode }) {
  const toast = useToast()
  const { subscribe, useFallback } = useEventStream()
  const [conversas, setConversas] = useState<ChatInterno.ConversaInbox[]>([])
  const [filtro, setFiltro] = useState<FiltroInboxChatInterno>('todas')
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(false)

  const carregar = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      setErro(false)
      try {
        const rows = await chatInterno.listarConversas()
        setConversas(rows)
      } catch (err) {
        setErro(true)
        if (!silent) toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as conversas.'))
      } finally {
        setLoading(false)
      }
    },
    [toast],
  )

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    const refresh = () => void carregar(true)
    const unsubMsg = subscribe('chat.interno.mensagem', refresh)
    const unsubContagem = subscribe('notificacao.contagem', refresh)
    return () => {
      unsubMsg()
      unsubContagem()
    }
  }, [subscribe, carregar])

  useEffect(() => {
    const intervalMs = useFallback ? 10_000 : 8_000
    const timer = setInterval(() => void carregar(true), intervalMs)
    return () => clearInterval(timer)
  }, [carregar, useFallback])

  const filtradas = useMemo(() => {
    if (filtro === 'todas') return conversas
    return conversas.filter((c) => c.tipo === filtro)
  }, [conversas, filtro])

  const obterConversa = useCallback((id: number) => conversas.find((c) => c.id === id), [conversas])

  const value = useMemo(
    () => ({
      conversas,
      filtradas,
      filtro,
      setFiltro,
      loading,
      erro,
      carregar,
      obterConversa,
    }),
    [conversas, filtradas, filtro, loading, erro, carregar, obterConversa],
  )

  return <ChatInternoContext.Provider value={value}>{children}</ChatInternoContext.Provider>
}

export function useChatInterno() {
  const ctx = useContext(ChatInternoContext)
  if (!ctx) throw new Error('useChatInterno deve ser usado dentro de ChatInternoProvider')
  return ctx
}
