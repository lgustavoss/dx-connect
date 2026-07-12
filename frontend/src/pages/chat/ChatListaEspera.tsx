import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, whatsappChats, type WhatsappChats } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useChatHub } from '../../contexts/ChatHubContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { chatWhatsappLink } from '../../lib/chatHubPaths'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'

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

function TempoEspera({ data }: { data?: string | null }) {
  const [minutos, setMinutos] = useState(0)
  useEffect(() => {
    if (!data) return
    const tick = () => setMinutos(Math.floor((Date.now() - new Date(data).getTime()) / 60_000))
    tick()
    const t = setInterval(tick, 30_000)
    return () => clearInterval(t)
  }, [data])
  return (
    <span
      className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${
        minutos > 10 ? 'bg-red-100 text-red-600 dark:bg-red-950/50' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/40'
      }`}
    >
      {minutos <= 0 ? 'Agora' : `${minutos} min`}
    </span>
  )
}

type Props = {
  /** Drawer mobile: não aplica busca global do hub */
  ignorarBusca?: boolean
  /** Após assumir com sucesso (ex.: navegar e fechar drawer) */
  onChatAssumido?: (chatId: number) => void
  /** Ao abrir um chat da lista (link Ver) */
  onVerChat?: () => void
}

export function ChatListaEspera({ ignorarBusca = false, onChatAssumido, onVerChat }: Props = {}) {
  const toast = useToast()
  const { busca, refreshContagens } = useChatHub()
  const { subscribe, useFallback } = useEventStream()
  const [fila, setFila] = useState<WhatsappChats.Chat[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const rows = await whatsappChats.fila()
      setFila(rows)
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
    const u = subscribe('chat.fila', refresh)
    return u
  }, [subscribe, load])

  async function assumir(id: number) {
    try {
      await whatsappChats.assumir(id)
      toast.showSuccess('Chat assumido.')
      await load()
      void refreshContagens()
      void refetchPendenciasResumo()
      onChatAssumido?.(id)
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 400
          ? (err.body as { detail?: string })?.detail || 'Erro ao assumir.'
          : mensagemFalhaParaToast(err)
      toast.showWarning(msg)
    }
  }

  const lista = ignorarBusca ? fila : filtrarPorBusca(fila, busca)

  if (loading) {
    return <p className="p-4 text-center text-sm text-slate-400 animate-pulse">Carregando fila…</p>
  }

  if (lista.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-slate-400">
        {busca.trim() ? 'Nenhum chat na fila com esse filtro.' : 'Fila vazia.'}
      </p>
    )
  }

  return (
    <ul className="divide-y divide-slate-100 dark:divide-slate-800">
      {lista.map((c) => (
        <li key={c.id} className="px-3 py-3">
          <div className="flex gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-100 text-sm font-bold text-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
              {c.cliente_nome?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                  {c.cliente_nome || 'Cliente'}
                </p>
                <TempoEspera data={c.created_at} />
              </div>
              <p className="truncate text-xs text-cyan-600 dark:text-cyan-400">{exibirProtocolo(c.protocolo)}</p>
              <p className="truncate text-xs text-slate-500">{c.wa_id}</p>
              {c.setor_nome && <p className="text-[11px] text-slate-400">Setor {c.setor_nome}</p>}
              <div className="mt-2 flex gap-2">
                <Link
                  to={chatWhatsappLink(c.id, 'espera')}
                  onClick={() => onVerChat?.()}
                  className="flex-1 rounded-lg border border-slate-200 py-1.5 text-center text-xs font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Ver
                </Link>
                <Button type="button" className="flex-1 py-1.5 text-xs" onClick={() => void assumir(c.id)}>
                  Atender
                </Button>
              </div>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}
