import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { portalChats, whatsappChats } from '../../api/client'
import { ChatCanalBadge } from '../../components/chat/ChatCanalBadge'
import { WhatsappAvatar } from '../../components/chat/WhatsappAvatar'
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
  separarAtendendoPorResponsavel,
  type ChatHubItem,
} from '../../lib/chatHubLista'

type ItemVariant = 'proprio' | 'outro' | 'neutro'

function SecaoAtendendo({
  titulo,
  contagem,
  children,
}: {
  titulo: string
  contagem: number
  children: ReactNode
}) {
  return (
    <section>
      <h3 className="sticky top-0 z-10 border-b border-slate-100 bg-white/95 px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/95">
        {titulo} ({contagem})
      </h3>
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">{children}</ul>
    </section>
  )
}

function ChatAtendendoItem({
  item,
  ativo,
  variant,
  usuarioId,
}: {
  item: ChatHubItem
  ativo: boolean
  variant: ItemVariant
  usuarioId?: number | null
}) {
  const { abrirChat } = useChatHub()
  const key = chatHubItemKey(item)
  const responsavel =
    item.atendente_nome?.trim() || (item.atendente_id != null ? `Atendente #${item.atendente_id}` : 'Sem responsável')

  return (
    <li key={key}>
      <Link
        to={chatHubItemLink('atendendo')}
        onClick={() => abrirChat(item.canal, item.id)}
        className={`flex gap-3 px-3 py-3 transition-colors hover:bg-slate-50 dark:hover:bg-slate-900/50 ${
          ativo ? 'bg-cyan-50/80 dark:bg-cyan-950/30' : ''
        } ${variant === 'proprio' ? 'border-l-2 border-cyan-500 pl-[10px]' : ''} ${
          variant === 'outro' ? 'border-l-2 border-slate-300 pl-[10px] dark:border-slate-600' : ''
        }`}
      >
        <WhatsappAvatar
          nome={item.nome}
          fotoUrl={item.canal === 'whatsapp' ? item.foto_perfil_url : null}
          fallbackClassName={
            ativo ? 'bg-cyan-600 text-white' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200'
          }
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 flex-1 items-center gap-1.5">
              <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{item.nome}</p>
              {variant === 'proprio' && (
                <span className="shrink-0 rounded-full bg-cyan-100 px-1.5 py-0.5 text-[9px] font-bold uppercase text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-200">
                  Você
                </span>
              )}
            </div>
            {item.estado === 'aguardando_atendente' && (
              <span className="h-2 w-2 shrink-0 rounded-full bg-amber-500" title="Aguardando" />
            )}
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
            <ChatCanalBadge canal={item.canal} />
            {variant === 'outro' && (
              <span
                className="max-w-[9rem] truncate rounded-full bg-slate-100 px-1.5 py-0.5 text-[9px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                title={responsavel}
              >
                {responsavel}
              </span>
            )}
            <p className="truncate text-xs text-cyan-600 dark:text-cyan-400" title={exibirProtocolo(item.protocolo)}>
              {exibirProtocolo(item.protocolo)}
            </p>
          </div>
          {item.ultima_mensagem_preview ? (
            <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{item.ultima_mensagem_preview}</p>
          ) : variant === 'neutro' ? (
            <p className="truncate text-xs text-slate-500">{rotuloResponsavelItem(item, usuarioId)}</p>
          ) : variant === 'outro' ? (
            <p className="truncate text-xs text-slate-500">{item.setor_nome ? `Setor • ${item.setor_nome}` : 'Em atendimento'}</p>
          ) : null}
        </div>
      </Link>
    </li>
  )
}

export function ChatListaAtendendo() {
  const { user } = useAuth()
  const { busca, chatAtivo } = useChatHub()
  const { subscribe, useFallback } = useEventStream()
  const [meus, setMeus] = useState<ChatHubItem[]>([])
  const [loading, setLoading] = useState(true)
  const chatAtivoKey = chatAtivo ? `${chatAtivo.canal}-${chatAtivo.id}` : null

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
  const { comigo, outros, mostrarSecoes } = separarAtendendoPorResponsavel(lista, user?.id)

  const renderItem = (item: ChatHubItem, variant: ItemVariant) => (
    <ChatAtendendoItem
      key={chatHubItemKey(item)}
      item={item}
      ativo={chatAtivoKey === chatHubItemKey(item)}
      variant={variant}
      usuarioId={user?.id}
    />
  )

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

  if (!mostrarSecoes) {
    return (
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {comigo.map((item) => renderItem(item, 'neutro'))}
      </ul>
    )
  }

  return (
    <div>
      {comigo.length > 0 && (
        <SecaoAtendendo titulo="Comigo" contagem={comigo.length}>
          {comigo.map((item) => renderItem(item, 'proprio'))}
        </SecaoAtendendo>
      )}
      {outros.length > 0 && (
        <SecaoAtendendo titulo="Outros atendentes" contagem={outros.length}>
          {outros.map((item) => renderItem(item, 'outro'))}
        </SecaoAtendendo>
      )}
    </div>
  )
}
