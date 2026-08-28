import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../api/client'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from './ui/BarraBuscaPaginacao'
import { Card } from './ui/Card'
import { Button } from './ui/Button'
import { AvaliacaoEstrelas } from './ui/AvaliacaoEstrelas'
import { useToast } from './ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { exibirProtocolo } from '../lib/exibirProtocolo'
import { rotuloEstadoChat } from '../lib/whatsappChatMeta'
import { marcarWhatsappChatAtivo, whatsappConversaLink } from '../lib/whatsappListReturn'
import { ChatIniciarConversaModal } from './chat/ChatIniciarConversaModal'

type Props = {
  empresaId?: number
  funcionarioRedeId?: number
  returnPath: string
  intro?: string
  emptyTitle?: string
  emptyDescription?: string
}

function formatDuration(chat: WhatsappChats.Chat) {
  if (!chat.atendimento_inicio_at) return '—'
  if (!chat.encerramento_at) return 'Em curso'
  const start = new Date(chat.atendimento_inicio_at)
  const end = new Date(chat.encerramento_at)
  const diff = Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000))
  const minutes = Math.floor(diff / 60)
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remain = minutes % 60
  return `${hours}h ${remain}m`
}

function formatDateTime(iso?: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function EmpresaChatsPanel({
  empresaId,
  funcionarioRedeId,
  returnPath,
  intro,
  emptyTitle,
  emptyDescription,
}: Props) {
  const toast = useToast()
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [items, setItems] = useState<WhatsappChats.Chat[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [retomarChat, setRetomarChat] = useState<WhatsappChats.Chat | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const params: Record<string, string | number | undefined> = {
      estado: 'todos',
      offset: (page - 1) * PAGE_SIZE_PADRAO,
      limit: PAGE_SIZE_PADRAO,
      busca: debouncedBusca || undefined,
    }
    if (empresaId != null) params.empresa_id = empresaId
    if (funcionarioRedeId != null) params.funcionario_rede_id = funcionarioRedeId
    whatsappChats
      .encerrados(params)
      .then(({ items: rows, total: t }) => {
        if (!cancelled) {
          setItems(rows)
          setTotal(t)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          toast.showError(
            mensagemFalhaParaToast(err, 'Falha ao carregar chats.'),
          )
          setItems([])
          setTotal(0)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [empresaId, funcionarioRedeId, page, debouncedBusca, toast])

  const textoIntro =
    intro ??
    (funcionarioRedeId != null
      ? 'Conversas WhatsApp vinculadas a este contato.'
      : 'Chats e atendimentos WhatsApp vinculados a esta empresa.')
  const tituloVazio = emptyTitle ?? (funcionarioRedeId != null ? 'Nenhum chat encontrado' : 'Nenhum chat nesta empresa')
  const descVazio =
    emptyDescription ??
    (funcionarioRedeId != null
      ? 'Quando houver atendimentos com este contato, eles aparecem aqui.'
      : 'Quando houver atendimentos com esta empresa de contexto, eles aparecem aqui.')

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500 dark:text-slate-400">{textoIntro}</p>
      <BarraBuscaPaginacao
        busca={busca}
        onBuscaChange={(v) => {
          setBusca(v)
          setPage(1)
        }}
        placeholder="Protocolo, telefone ou nome…"
        page={page}
        total={total}
        onPageChange={setPage}
        disabled={loading}
      />

      {loading && items.length === 0 ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card className="flex flex-col items-center justify-center border-dashed border-2 py-14 text-center">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">{tituloVazio}</h3>
          <p className="mt-1 text-sm text-slate-500">{descVazio}</p>
        </Card>
      ) : (
        <div className="grid gap-3">
          {items.map((c) => (
            <Card
              key={c.id}
              className="group border-none p-4 shadow-sm ring-1 ring-slate-200 transition-all hover:ring-cyan-500/50 dark:ring-slate-800"
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex min-w-[220px] flex-1 items-center gap-4">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-50 text-slate-400 transition-colors group-hover:bg-cyan-50 group-hover:text-cyan-600 dark:bg-slate-900 dark:group-hover:bg-cyan-900/20">
                    <span className="text-sm font-bold">{c.cliente_nome?.charAt(0).toUpperCase() || 'C'}</span>
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="truncate font-bold text-slate-900 dark:text-slate-100">
                        {c.cliente_nome || 'Cliente'}
                      </h3>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        {rotuloEstadoChat(c.estado)}
                      </span>
                      <span className="font-mono text-[10px] font-bold text-slate-400">{c.wa_id}</span>
                    </div>
                    <p
                      className="truncate font-mono text-xs font-bold text-cyan-600 dark:text-cyan-400"
                      title={exibirProtocolo(c.protocolo)}
                    >
                      {exibirProtocolo(c.protocolo)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <div className="hidden text-right sm:block">
                    <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Atendido por</p>
                    <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      {c.atendente_nome || 'Sistema'}
                    </p>
                  </div>
                  <div className="grid gap-1.5 text-right">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Início</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        {formatDateTime(c.atendimento_inicio_at)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Finalizado em</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        {formatDateTime(c.encerramento_at)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Duração</p>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">{formatDuration(c)}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-tight text-slate-400">Avaliação</p>
                      <div className="flex justify-end">
                        <AvaliacaoEstrelas chat={c} size="sm" />
                      </div>
                    </div>
                  </div>
                  <Link
                    to={whatsappConversaLink(returnPath)}
                    onClick={() => marcarWhatsappChatAtivo(c.id)}
                    className="rounded-full bg-slate-100 p-2 text-slate-400 transition-all hover:bg-cyan-600 hover:text-white dark:bg-slate-800 dark:hover:bg-cyan-700"
                    title="Ver conversa"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 12h14" />
                      <path d="m12 5 7 7-7 7" />
                    </svg>
                  </Link>
                  {(c.estado === 'encerrado' || c.estado === 'aguardando_avaliacao') && (
                    <Button
                      type="button"
                      variant="secondary"
                      className="h-9 px-3 text-xs"
                      onClick={() => setRetomarChat(c)}
                    >
                      Retomar contacto
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <ChatIniciarConversaModal
        open={retomarChat != null}
        onClose={() => setRetomarChat(null)}
        telefoneInicial={retomarChat?.wa_id}
        funcionarioId={retomarChat?.funcionario_rede_id}
        empresas={retomarChat?.empresas_opcoes}
        titulo={retomarChat ? `Retomar ${retomarChat.cliente_nome || retomarChat.wa_id}` : undefined}
      />
    </div>
  )
}
