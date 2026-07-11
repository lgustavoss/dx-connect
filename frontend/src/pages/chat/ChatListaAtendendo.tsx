import { useCallback, useEffect, useState } from 'react'
import { Link, useMatch } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { useChatHub } from '../../contexts/ChatHubContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { chatWhatsappLink } from '../../lib/chatHubPaths'
import { rotuloResponsavelChat } from '../../lib/whatsappChatMeta'
import { useAuth } from '../../contexts/AuthContext'

function filtrarPorBusca(items: WhatsappChats.Chat[], busca: string): WhatsappChats.Chat[] {
  const q = busca.trim().toLowerCase()
  if (!q) return items
  return items.filter((c) => {
    const nome = (c.cliente_nome || '').toLowerCase()
    const wa = (c.wa_id || '').toLowerCase()
    const proto = (c.protocolo || '').toLowerCase()
    return nome.includes(q) || wa.includes(q) || proto.includes(q)
  })
}

export function ChatListaAtendendo() {
  const { user } = useAuth()
  const { busca } = useChatHub()
  const { subscribe, useFallback } = useEventStream()
  const [meus, setMeus] = useState<WhatsappChats.Chat[]>([])
  const [loading, setLoading] = useState(true)
  const matchChat = useMatch('/chat/c/:chatId')
  const chatAtivoId = matchChat?.params.chatId ? Number(matchChat.params.chatId) : null

  const load = useCallback(async () => {
    try {
      const rows = await whatsappChats.meus()
      setMeus(rows)
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
    return () => {
      u1()
      u2()
    }
  }, [subscribe, load])

  const lista = filtrarPorBusca(meus, busca)

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
        const ativo = chatAtivoId === c.id
        return (
          <li key={c.id}>
            <Link
              to={chatWhatsappLink(c.id, 'atendendo')}
              className={`flex gap-3 px-3 py-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-900/50 ${
                ativo ? 'bg-cyan-50/80 dark:bg-cyan-950/30' : ''
              }`}
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  ativo ? 'bg-cyan-600 text-white' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200'
                }`}
              >
                {c.cliente_nome?.charAt(0)?.toUpperCase() || '?'}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                    {c.cliente_nome || 'Cliente'}
                  </p>
                  {c.estado === 'aguardando_atendente' && (
                    <span className="h-2 w-2 shrink-0 rounded-full bg-amber-500" title="Aguardando" />
                  )}
                </div>
                <p className="truncate text-xs text-cyan-600 dark:text-cyan-400" title={exibirProtocolo(c.protocolo)}>
                  {exibirProtocolo(c.protocolo)}
                </p>
                <p className="truncate text-xs text-slate-500">{rotuloResponsavelChat(c, user?.id)}</p>
              </div>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
