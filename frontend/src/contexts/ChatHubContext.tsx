import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { portalChats, whatsappChats } from '../api/client'
import {
  CHAT_ATIVO_EVENT,
  gravarChatAtivoSession,
  lerChatAtivoSession,
  type ChatAtivo,
  type ChatAtivoCanal,
} from '../lib/chatAtivo'
import { useEventStream } from './EventStreamContext'

type ChatHubContextValue = {
  busca: string
  setBusca: (v: string) => void
  filaCount: number
  atendendoCount: number
  refreshContagens: () => Promise<void>
  /** Conversa aberta no painel (sem id na URL) (#654). */
  chatAtivo: ChatAtivo | null
  abrirChat: (canal: ChatAtivoCanal, id: number) => void
  fecharChat: () => void
}

const ChatHubContext = createContext<ChatHubContextValue | null>(null)

export function ChatHubProvider({ children }: { children: ReactNode }) {
  const { subscribe, useFallback } = useEventStream()
  const location = useLocation()
  const [busca, setBusca] = useState('')
  const [filaCount, setFilaCount] = useState(0)
  const [atendendoCount, setAtendendoCount] = useState(0)
  const [chatAtivo, setChatAtivo] = useState<ChatAtivo | null>(() => lerChatAtivoSession())

  const abrirChat = useCallback((canal: ChatAtivoCanal, id: number) => {
    if (!Number.isFinite(id) || id <= 0) return
    const next = { canal, id }
    gravarChatAtivoSession(next)
    setChatAtivo(next)
  }, [])

  const fecharChat = useCallback(() => {
    gravarChatAtivoSession(null)
    setChatAtivo(null)
  }, [])

  /** Sync após clique que grava sessão (sininho / helpers sem side-effect) (#654 / #697 / #698). */
  useEffect(() => {
    if (!location.pathname.startsWith('/chat')) return
    setChatAtivo(lerChatAtivoSession())
  }, [location.pathname, location.key])

  useEffect(() => {
    const sync = () => setChatAtivo(lerChatAtivoSession())
    window.addEventListener(CHAT_ATIVO_EVENT, sync)
    return () => window.removeEventListener(CHAT_ATIVO_EVENT, sync)
  }, [])

  const refreshContagens = useCallback(async () => {
    try {
      const [fila, meus, portalFila, portalMeus] = await Promise.all([
        whatsappChats.fila(),
        whatsappChats.meus(),
        portalChats.fila(),
        portalChats.meus(),
      ])
      setFilaCount(fila.length + portalFila.length)
      setAtendendoCount(meus.length + portalMeus.length)
    } catch {
      /* silencioso — badges são auxiliares */
    }
  }, [])

  useEffect(() => {
    void refreshContagens()
    const intervalMs = useFallback ? 12_000 : 8_000
    const timer = setInterval(() => void refreshContagens(), intervalMs)
    return () => clearInterval(timer)
  }, [refreshContagens, useFallback])

  useEffect(() => {
    const refresh = () => void refreshContagens()
    const u1 = subscribe('chat.fila', refresh)
    const u2 = subscribe('chat.mensagem', refresh)
    const u3 = subscribe('portal.chat.fila', refresh)
    const u4 = subscribe('portal.chat.mensagem', refresh)
    return () => {
      u1()
      u2()
      u3()
      u4()
    }
  }, [subscribe, refreshContagens])

  const value = useMemo(
    () => ({
      busca,
      setBusca,
      filaCount,
      atendendoCount,
      refreshContagens,
      chatAtivo,
      abrirChat,
      fecharChat,
    }),
    [busca, filaCount, atendendoCount, refreshContagens, chatAtivo, abrirChat, fecharChat],
  )

  return <ChatHubContext.Provider value={value}>{children}</ChatHubContext.Provider>
}

export function useChatHub() {
  const ctx = useContext(ChatHubContext)
  if (!ctx) throw new Error('useChatHub deve ser usado dentro de ChatHubProvider')
  return ctx
}

/** Para telas que também rodam fora do hub (ex.: histórico WhatsApp). */
export function useChatHubOpcional() {
  return useContext(ChatHubContext)
}
