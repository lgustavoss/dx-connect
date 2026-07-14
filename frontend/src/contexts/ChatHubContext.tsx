import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { portalChats, whatsappChats } from '../api/client'

import { useEventStream } from './EventStreamContext'



type ChatHubContextValue = {

  busca: string

  setBusca: (v: string) => void

  filaCount: number

  atendendoCount: number

  refreshContagens: () => Promise<void>

}



const ChatHubContext = createContext<ChatHubContextValue | null>(null)



export function ChatHubProvider({ children }: { children: ReactNode }) {

  const { subscribe, useFallback } = useEventStream()

  const [busca, setBusca] = useState('')

  const [filaCount, setFilaCount] = useState(0)

  const [atendendoCount, setAtendendoCount] = useState(0)



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

    }),

    [busca, filaCount, atendendoCount, refreshContagens],

  )



  return <ChatHubContext.Provider value={value}>{children}</ChatHubContext.Provider>

}



export function useChatHub() {

  const ctx = useContext(ChatHubContext)

  if (!ctx) throw new Error('useChatHub deve ser usado dentro de ChatHubProvider')

  return ctx

}

