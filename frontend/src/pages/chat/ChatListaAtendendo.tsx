import { useCallback, useEffect, useState } from 'react'
import { Link, useMatch } from 'react-router-dom'
import { portalChats, whatsappChats } from '../../api/client'
import { ChatCanalBadge } from '../../components/chat/ChatCanalBadge'
import { useAuth } from '../../contexts/AuthContext'
import { useChatHub } from '../../contexts/ChatHubContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import {
  chatHubItemKey,
  chatHubItemLink,
  filtrarChatHubPorBusca,
  mapPortalChat,
  mapWhatsappChat,
  ordenarAtendendo,
  rotuloResponsavelItem,
  type ChatHubItem,
} from '../../lib/chatHubLista'

export function ChatListaAtendendo() {
  const { user } = useAuth()
  const { busca } = useChatHub()
  const { subscribe, useFallback } = useEventStream()
  const [meus, setMeus] = useState<ChatHubItem[]>([])
  const [loading, setLoading] = useState(true)
  const matchWpp = useMatch('/chat/c/:chatId')
  const matchPortal = useMatch('/chat/portal/:chatId')
  const chatAtivoKey =
    matchWpp?.params.chatId != null
      ? `whatsapp-${matchWpp.params.chatId}`
      : matchPortal?.params.chatId != null
        ? `portal-${matchPortal.params.chatId}`
        : null

  const load = useCallback(async () => {
    try {
      const [wppMeus, portalMeus] = await Promise.all([whatsappChats.meus(), portalChats.meus()])
      const items = ordenarAtendendo([...wppMeus.map(mapWhatsappChat), ...portalMeus.map(mapPortalChat)])
      setMeus(items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const intervalMs = useFallback ? 10_000 : 8_000
    const timer = setInterval(() => void load(), intervalMs)
    return () => clearInterval(timer)
  }, [load, useFallback])

  useEffect(() => {
    const refresh = () => void load()
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
  }, [subscribe, load])

  const lista = filtrarChatHubPorBusca(meus, busca)

  if (loading) {
    return <p className="p-4 text-center text-sm text-slate-400 animate-pulse">Carregando…</p>
  }

  if (lista.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-slate-400">
        {busca.trim() ? 'Nenhum chat encontrado.' : 'Nenhum atendimento em curso.'}
      </p>
    )
  }

  return (
    <ul className="divide-y divide-slate-100 dark:divide-slate-800">
      {lista.map((c) => {
        const key = chatHubItemKey(c)
        const ativo = chatAtivoKey === key
        return (
          <li key={key}>
            <Link
              to={chatHubItemLink(c, 'atendendo')}
              className={`flex gap-3 px-3 py-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-900/50 ${
                ativo ? 'bg-cyan-50/80 dark:bg-cyan-950/30' : ''
              }`}
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  ativo ? 'bg-cyan-600 text-white' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200'
                }`}
              >
                {c.nome.charAt(0)?.toUpperCase() || '?'}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{c.nome}</p>
                  {c.estado === 'aguardando_atendente' && (
                    <span className="h-2 w-2 shrink-0 rounded-full bg-amber-500" title="Aguardando" />
                  )}
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                  <ChatCanalBadge canal={c.canal} />
                  <p className="truncate text-xs text-cyan-600 dark:text-cyan-400" title={exibirProtocolo(c.protocolo)}>
                    {exibirProtocolo(c.protocolo)}
                  </p>
                </div>
                {c.ultima_mensagem_preview ? (
                  <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{c.ultima_mensagem_preview}</p>
                ) : (
                  <p className="truncate text-xs text-slate-500">{rotuloResponsavelItem(c, user?.id)}</p>
                )}
              </div>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
