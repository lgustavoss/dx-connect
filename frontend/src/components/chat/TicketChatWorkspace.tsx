import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { chatAssistant, type ChatAssistant, type Tickets } from '../../api/client'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { useToast } from '../ui/Toast'
import {
  formatFileSize,
  loadChatWorkspace,
  saveChatWorkspace,
  type ChatAttachmentMeta,
  type ChatWorkspaceState,
} from './chatStorage'

type TimelineItem = {
  id: string
  createdAt: string
  body: string
  role: 'customer' | 'agent' | 'internal'
  title: string
  subtitle: string
  attachments?: ChatAttachmentMeta[]
}

interface TicketChatWorkspaceProps {
  ticket: Tickets.Ticket
  messages: Tickets.Mensagem[]
  canSendPublicMessage: boolean
  allTickets?: Tickets.Ticket[]
  lockLinkedTicket?: boolean
  onSelectTicket?: (ticketId: number) => void
  onOpenManager?: () => void
  onSendMessage: (payload: Tickets.MensagemCreate) => Promise<void>
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusBadgeClass(status: ChatWorkspaceState['queueStatus']) {
  if (status === 'resolvido') return 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200'
  if (status === 'aguardando_cliente') return 'bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200'
  if (status === 'em_atendimento') return 'bg-sky-100 text-sky-900 dark:bg-sky-950/50 dark:text-sky-200'
  return 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200'
}

function priorityBadgeClass(priority: ChatWorkspaceState['priority']) {
  if (priority === 'critica') return 'bg-rose-100 text-rose-900 dark:bg-rose-950/50 dark:text-rose-200'
  if (priority === 'alta') return 'bg-orange-100 text-orange-900 dark:bg-orange-950/50 dark:text-orange-200'
  return 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200'
}

function channelLabel(channel: ChatWorkspaceState['channel']) {
  if (channel === 'webchat') return 'Web chat'
  if (channel === 'telefone') return 'Telefone'
  return 'WhatsApp'
}

function queueLabel(status: ChatWorkspaceState['queueStatus']) {
  if (status === 'em_atendimento') return 'Em atendimento'
  if (status === 'aguardando_cliente') return 'Aguardando cliente'
  if (status === 'resolvido') return 'Resolvido'
  return 'Novo'
}

function priorityLabel(priority: ChatWorkspaceState['priority']) {
  if (priority === 'critica') return 'Critica'
  if (priority === 'alta') return 'Alta'
  return 'Normal'
}

function timelineFromData(
  ticket: Tickets.Ticket,
  messages: Tickets.Mensagem[],
  workspace: ChatWorkspaceState,
): TimelineItem[] {
  const backendItems: TimelineItem[] = messages.map((message) => {
    if (message.tipo === 'interno') {
      return {
        id: `message-${message.id}`,
        createdAt: message.created_at,
        body: message.corpo,
        role: 'internal',
        title: 'Nota interna',
        subtitle: message.atendente_nome || 'Equipe interna',
      }
    }
    if (message.tipo === 'cliente') {
      return {
        id: `message-${message.id}`,
        createdAt: message.created_at,
        body: message.corpo,
        role: 'customer',
        title: workspace.customerName || ticket.empresa_nome || 'Cliente',
        subtitle: `${channelLabel(workspace.channel)} · cliente`,
      }
    }
    if (message.tipo === 'abertura') {
      return {
        id: `message-${message.id}`,
        createdAt: message.created_at,
        body: message.corpo,
        role: 'customer',
        title: workspace.customerName || ticket.empresa_nome || 'Cliente',
        subtitle: `${channelLabel(workspace.channel)} · abertura do ticket`,
      }
    }
    return {
      id: `message-${message.id}`,
      createdAt: message.created_at,
      body: message.corpo,
      role: 'agent',
      title: message.atendente_nome || 'Equipe DX Connect',
      subtitle: ticket.setor_nome || 'Equipe de atendimento',
    }
  })

  const incomingItems: TimelineItem[] = workspace.incomingMessages.map((message) => ({
    id: message.id,
    createdAt: message.createdAt,
    body: message.body,
    role: 'customer',
    title: workspace.customerName || ticket.empresa_nome || 'Cliente',
    subtitle: `${channelLabel(workspace.channel)} · ${message.source === 'manual' ? 'recebida manualmente' : message.source}`,
    attachments: message.attachments,
  }))

  return [...backendItems, ...incomingItems].sort((a, b) => {
    const da = new Date(a.createdAt).getTime()
    const db = new Date(b.createdAt).getTime()
    return da - db
  })
}

function buildFallbackSuggestion(
  ticket: Tickets.Ticket,
  workspace: ChatWorkspaceState,
  timeline: TimelineItem[],
): string {
  const lastCustomer = [...timeline].reverse().find((item) => item.role === 'customer')
  const greeting = workspace.customerName ? `Ola, ${workspace.customerName}.` : 'Ola.'
  const context = lastCustomer?.body
    ? ` Recebemos sua mensagem sobre "${ticket.assunto}" e estamos tratando isso pelo ticket ${ticket.protocolo}.`
    : ` Estamos acompanhando seu chamado ${ticket.protocolo}.`
  const nextStep =
    workspace.queueStatus === 'aguardando_cliente'
      ? ' Assim que voce confirmar os detalhes pendentes, seguimos com a analise.'
      : ' Nosso time esta verificando o ocorrido e retornara com a proxima atualizacao objetiva.'
  const ask =
    workspace.priority === 'critica'
      ? ' Se a operacao do posto estiver parada, envie tambem o impacto atual e desde quando iniciou.'
      : ' Se puder, envie horario da ocorrencia, bomba/caixa afetado e o que apareceu na tela.'
  return `${greeting}${context}${nextStep}${ask}`
}

export function TicketChatWorkspace({
  ticket,
  messages,
  canSendPublicMessage,
  allTickets = [],
  lockLinkedTicket = false,
  onSelectTicket,
  onOpenManager,
  onSendMessage,
}: TicketChatWorkspaceProps) {
  const toast = useToast()
  const [workspace, setWorkspace] = useState<ChatWorkspaceState>(() => loadChatWorkspace(ticket))
  const [composerType, setComposerType] = useState<'publico' | 'interno'>(
    canSendPublicMessage ? 'publico' : 'interno',
  )
  const [draft, setDraft] = useState('')
  const [draftFiles, setDraftFiles] = useState<ChatAttachmentMeta[]>([])
  const [sending, setSending] = useState(false)
  const [registerIncomingOpen, setRegisterIncomingOpen] = useState(false)
  const [incomingDraft, setIncomingDraft] = useState('')
  const [incomingFiles, setIncomingFiles] = useState<ChatAttachmentMeta[]>([])
  const [requestingSuggestion, setRequestingSuggestion] = useState(false)
  const [aiStatus, setAiStatus] = useState<'idle' | 'online' | 'fallback'>('idle')

  useEffect(() => {
    const next = loadChatWorkspace(ticket)
    setWorkspace(next)
    setDraft('')
    setDraftFiles([])
    setIncomingDraft('')
    setIncomingFiles([])
  }, [ticket])

  useEffect(() => {
    saveChatWorkspace(ticket.id, workspace)
  }, [ticket.id, workspace])

  useEffect(() => {
    if (!canSendPublicMessage && composerType === 'publico') {
      setComposerType('interno')
    }
  }, [canSendPublicMessage, composerType])

  const timeline = useMemo(() => timelineFromData(ticket, messages, workspace), [ticket, messages, workspace])
  const lastActivity = timeline[timeline.length - 1]?.createdAt || ticket.updated_at || ticket.created_at
  const internalCount = timeline.filter((item) => item.role === 'internal').length
  const customerCount = timeline.filter((item) => item.role === 'customer').length

  const ticketOptions = useMemo(
    () =>
      allTickets.map((item) => ({
        value: item.id,
        label: `#${item.protocolo} · ${item.assunto}`,
      })),
    [allTickets],
  )

  function updateWorkspace(patch: Partial<ChatWorkspaceState>) {
    setWorkspace((current) => ({ ...current, ...patch }))
  }

  function handleTagChange(value: string) {
    updateWorkspace({
      tags: value
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
    })
  }

  function extractFiles(fileList: FileList | null): ChatAttachmentMeta[] {
    if (!fileList?.length) return []
    return Array.from(fileList).map((file, index) => ({
      id: `${file.name}-${file.size}-${index}`,
      name: file.name,
      sizeLabel: formatFileSize(file.size),
    }))
  }

  async function handleSend() {
    const text = draft.trim()
    if (!text) {
      toast.showWarning('Escreva uma resposta antes de enviar.')
      return
    }
    setSending(true)
    try {
      const suffix =
        draftFiles.length > 0
          ? `\n\nAnexos referenciados: ${draftFiles.map((file) => `${file.name} (${file.sizeLabel})`).join(', ')}`
          : ''
      await onSendMessage({
        corpo: `${text}${suffix}`,
        tipo: canSendPublicMessage ? composerType : 'interno',
      })
      setDraft('')
      setDraftFiles([])
      toast.showSuccess(composerType === 'interno' ? 'Nota interna registrada.' : 'Resposta enviada no atendimento.')
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Nao foi possivel enviar a mensagem.')
    } finally {
      setSending(false)
    }
  }

  function handleRegisterIncoming() {
    const body = incomingDraft.trim()
    if (!body) {
      toast.showWarning('Descreva a mensagem recebida antes de registrar.')
      return
    }
    updateWorkspace({
      incomingMessages: [
        ...workspace.incomingMessages,
        {
          id: `incoming-${Date.now()}`,
          body,
          createdAt: new Date().toISOString(),
          source: workspace.channel === 'webchat' ? 'web' : workspace.channel === 'telefone' ? 'manual' : 'whatsapp',
          attachments: incomingFiles,
        },
      ],
    })
    setIncomingDraft('')
    setIncomingFiles([])
    setRegisterIncomingOpen(false)
    toast.showSuccess('Mensagem recebida adicionada ao chat.')
  }

  async function handleSuggestWithAi() {
    setRequestingSuggestion(true)
    try {
      const payload: ChatAssistant.SuggestRequest = {
        ticket: {
          protocolo: ticket.protocolo,
          assunto: ticket.assunto,
          empresa_nome: ticket.empresa_nome,
          setor_nome: ticket.setor_nome,
          status_nome: ticket.status_nome,
        },
        conversation: timeline.slice(-10).map((item) => ({
          role: item.role,
          content: item.body,
          created_at: item.createdAt,
        })),
        tone: workspace.tone,
        objective: 'Responder o cliente com proximo passo claro e tom apropriado para operacao de posto.',
      }
      const response = await chatAssistant.respond(payload)
      setDraft(response.reply)
      setAiStatus('online')
      toast.showSuccess(`Sugestao pronta com ${response.model}.`)
    } catch {
      setDraft(buildFallbackSuggestion(ticket, workspace, timeline))
      setAiStatus('fallback')
      toast.showWarning('Usei uma sugestao local porque a integracao com OpenAI nao estava disponivel.')
    } finally {
      setRequestingSuggestion(false)
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_360px]">
      <div className="space-y-6">
        <section className="overflow-hidden rounded-[28px] border border-slate-200/90 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900/60">
          <div className="border-b border-slate-200/80 bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_36%),linear-gradient(135deg,rgba(255,255,255,0.98),rgba(240,249,255,0.88))] px-5 py-5 dark:border-slate-700/70 dark:bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_30%),linear-gradient(135deg,rgba(15,23,42,0.9),rgba(12,74,110,0.28))] sm:px-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${statusBadgeClass(workspace.queueStatus)}`}>
                    {queueLabel(workspace.queueStatus)}
                  </span>
                  <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${priorityBadgeClass(workspace.priority)}`}>
                    Prioridade {priorityLabel(workspace.priority)}
                  </span>
                  <span className="rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-white dark:bg-slate-100 dark:text-slate-900">
                    {channelLabel(workspace.channel)}
                  </span>
                </div>
                <h2 className="mt-3 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
                  Central de atendimento do cliente
                </h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  Conversa operacional vinculada ao ticket <span className="font-semibold text-slate-900 dark:text-slate-100">#{ticket.protocolo}</span>, com controle de contexto, propriedades e sugestao de resposta.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button type="button" variant="secondary" onClick={() => setRegisterIncomingOpen((current) => !current)}>
                  Registrar recebida
                </Button>
                <Button type="button" variant="secondary" onClick={handleSuggestWithAi} loading={requestingSuggestion}>
                  Sugerir com IA
                </Button>
                {onOpenManager ? (
                  <Button type="button" variant="secondary" onClick={onOpenManager}>
                    Gerir ticket
                  </Button>
                ) : null}
                <Link to={`/tickets/${ticket.id}`}>
                  <Button type="button">Abrir ticket</Button>
                </Link>
              </div>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/70 bg-white/90 px-4 py-3 shadow-sm ring-1 ring-slate-200/70 dark:border-slate-700/70 dark:bg-slate-950/50 dark:ring-slate-700/60">
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Cliente</p>
                <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">{workspace.customerName || ticket.empresa_nome || 'Nao identificado'}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{workspace.stationName || 'Posto / unidade principal'}</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/90 px-4 py-3 shadow-sm ring-1 ring-slate-200/70 dark:border-slate-700/70 dark:bg-slate-950/50 dark:ring-slate-700/60">
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Mensagens</p>
                <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">{timeline.length} interacoes</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{customerCount} do cliente · {internalCount} internas</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/90 px-4 py-3 shadow-sm ring-1 ring-slate-200/70 dark:border-slate-700/70 dark:bg-slate-950/50 dark:ring-slate-700/60">
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Ultima atividade</p>
                <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">{lastActivity ? formatDateTime(lastActivity) : 'Sem atividade'}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  IA {aiStatus === 'online' ? 'online' : aiStatus === 'fallback' ? 'local' : workspace.aiEnabled ? 'pronta' : 'desligada'}
                </p>
              </div>
            </div>
          </div>

          {registerIncomingOpen ? (
            <div className="border-b border-slate-200/80 bg-slate-50/80 px-5 py-4 dark:border-slate-700/70 dark:bg-slate-950/40 sm:px-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Registrar mensagem recebida</h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Use este bloco para espelhar o que chegou pelo canal do cliente antes de responder.
                  </p>
                </div>
                <Button type="button" variant="ghost" onClick={() => setRegisterIncomingOpen(false)}>
                  Fechar
                </Button>
              </div>
              <div className="mt-4 space-y-3">
                <textarea
                  value={incomingDraft}
                  onChange={(event) => setIncomingDraft(event.target.value)}
                  rows={4}
                  placeholder="Ex.: Cliente informou que a bomba 04 trava ao finalizar venda no turno da noite..."
                  className="w-full rounded-2xl border-0 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm ring-1 ring-slate-200/90 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-300/50 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700"
                />
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-600 transition-colors hover:border-sky-300 hover:text-slate-900 dark:border-slate-600 dark:text-slate-300 dark:hover:border-sky-500 dark:hover:text-slate-100">
                    <input
                      type="file"
                      multiple
                      className="hidden"
                      onChange={(event) => setIncomingFiles(extractFiles(event.target.files))}
                    />
                    Anexar comprovantes
                  </label>
                  <Button type="button" onClick={handleRegisterIncoming}>
                    Salvar no chat
                  </Button>
                </div>
                {incomingFiles.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {incomingFiles.map((file) => (
                      <span key={file.id} className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700">
                        {file.name} · {file.sizeLabel}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}

          <div className="space-y-4 px-5 py-5 sm:px-6">
            {timeline.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 px-5 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                Nenhuma interacao registrada ainda neste atendimento.
              </div>
            ) : (
              <div className="space-y-3">
                {timeline.map((item) => {
                  const isCustomer = item.role === 'customer'
                  const isInternal = item.role === 'internal'
                  return (
                    <article
                      key={item.id}
                      className={`flex ${isCustomer ? 'justify-start' : 'justify-end'}`}
                    >
                      <div
                        className={`max-w-[88%] rounded-[24px] px-4 py-3 shadow-sm ring-1 ${
                          isInternal
                            ? 'bg-amber-50 text-amber-950 ring-amber-200 dark:bg-amber-950/30 dark:text-amber-100 dark:ring-amber-800/50'
                            : isCustomer
                              ? 'bg-slate-100 text-slate-900 ring-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700'
                              : 'bg-[linear-gradient(135deg,rgba(8,145,178,1),rgba(37,99,235,1))] text-white ring-cyan-500/30'
                        }`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className={`text-xs font-semibold uppercase tracking-[0.12em] ${isCustomer ? 'text-slate-500 dark:text-slate-400' : isInternal ? 'text-amber-700 dark:text-amber-300' : 'text-cyan-100/90'}`}>
                              {item.title}
                            </p>
                            <p className={`text-xs ${isCustomer ? 'text-slate-500 dark:text-slate-400' : isInternal ? 'text-amber-700/90 dark:text-amber-300/90' : 'text-blue-100/90'}`}>
                              {item.subtitle}
                            </p>
                          </div>
                          <time className={`text-[11px] ${isCustomer ? 'text-slate-400 dark:text-slate-500' : isInternal ? 'text-amber-700/80 dark:text-amber-300/80' : 'text-white/75'}`}>
                            {formatDateTime(item.createdAt)}
                          </time>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{item.body}</p>
                        {item.attachments?.length ? (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {item.attachments.map((attachment) => (
                              <span
                                key={attachment.id}
                                className={`rounded-full px-3 py-1 text-[11px] font-medium ${
                                  isCustomer
                                    ? 'bg-white text-slate-700 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700'
                                    : 'bg-white/15 text-white ring-1 ring-white/15'
                                }`}
                              >
                                {attachment.name} · {attachment.sizeLabel}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </article>
                  )
                })}
              </div>
            )}
          </div>

          <div className="border-t border-slate-200/80 bg-slate-50/70 px-5 py-5 dark:border-slate-700/70 dark:bg-slate-950/35 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Responder atendimento</h3>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Envie resposta ao cliente ou registre nota interna para o time.
                </p>
              </div>
              <div className="inline-flex rounded-2xl bg-white p-1 shadow-sm ring-1 ring-slate-200 dark:bg-slate-900 dark:ring-slate-700">
                {canSendPublicMessage ? (
                  <button
                    type="button"
                    onClick={() => setComposerType('publico')}
                    className={`rounded-xl px-3 py-2 text-xs font-semibold transition-colors ${
                      composerType === 'publico'
                        ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                        : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
                    }`}
                  >
                    Resposta ao cliente
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => setComposerType('interno')}
                  className={`rounded-xl px-3 py-2 text-xs font-semibold transition-colors ${
                    composerType === 'interno' || !canSendPublicMessage
                      ? 'bg-amber-100 text-amber-950 dark:bg-amber-950/60 dark:text-amber-100'
                      : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
                  }`}
                >
                  Nota interna
                </button>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                rows={5}
                placeholder={
                  composerType === 'interno'
                    ? 'Registre contexto, proximo passo tecnico ou alinhamento interno...'
                    : 'Escreva a resposta que sera enviada ao cliente...'
                }
                className="w-full rounded-[24px] border-0 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm ring-1 ring-slate-200/90 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-300/50 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700"
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-600 transition-colors hover:border-sky-300 hover:text-slate-900 dark:border-slate-600 dark:text-slate-300 dark:hover:border-sky-500 dark:hover:text-slate-100">
                    <input
                      type="file"
                      multiple
                      className="hidden"
                      onChange={(event) => setDraftFiles(extractFiles(event.target.files))}
                    />
                    Referenciar anexos
                  </label>
                  <Button type="button" variant="secondary" onClick={handleSuggestWithAi} loading={requestingSuggestion}>
                    Rascunho IA
                  </Button>
                </div>
                <Button type="button" onClick={handleSend} loading={sending}>
                  {composerType === 'interno' ? 'Salvar nota' : 'Enviar resposta'}
                </Button>
              </div>
              {draftFiles.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {draftFiles.map((file) => (
                    <span key={file.id} className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700">
                      {file.name} · {file.sizeLabel}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </section>
      </div>

      <div className="space-y-6">
        <Card title="Propriedades do chat">
          <div className="space-y-4">
            <Input
              label="Nome do contato"
              value={workspace.customerName}
              onChange={(event) => updateWorkspace({ customerName: event.target.value })}
              placeholder="Ex.: Gerente da pista"
            />
            <Input
              label="Unidade / posto"
              value={workspace.stationName}
              onChange={(event) => updateWorkspace({ stationName: event.target.value })}
              placeholder="Ex.: Posto Avenida Sul"
            />
            <Input
              label="Telefone / ramal"
              value={workspace.contactPhone}
              onChange={(event) => updateWorkspace({ contactPhone: event.target.value })}
              placeholder="Ex.: (11) 99999-9999"
            />
            <Select
              label="Canal"
              value={workspace.channel}
              onChange={(value) => updateWorkspace({ channel: value as ChatWorkspaceState['channel'] })}
              options={[
                { value: 'whatsapp', label: 'WhatsApp Business' },
                { value: 'webchat', label: 'Web chat' },
                { value: 'telefone', label: 'Telefone' },
              ]}
            />
            <Select
              label="Status operacional"
              value={workspace.queueStatus}
              onChange={(value) => updateWorkspace({ queueStatus: value as ChatWorkspaceState['queueStatus'] })}
              options={[
                { value: 'novo', label: 'Novo' },
                { value: 'em_atendimento', label: 'Em atendimento' },
                { value: 'aguardando_cliente', label: 'Aguardando cliente' },
                { value: 'resolvido', label: 'Resolvido' },
              ]}
            />
            <Select
              label="Prioridade"
              value={workspace.priority}
              onChange={(value) => updateWorkspace({ priority: value as ChatWorkspaceState['priority'] })}
              options={[
                { value: 'normal', label: 'Normal' },
                { value: 'alta', label: 'Alta' },
                { value: 'critica', label: 'Critica' },
              ]}
            />
            <Select
              label="Tom da IA"
              value={workspace.tone}
              onChange={(value) => updateWorkspace({ tone: value as ChatWorkspaceState['tone'] })}
              options={[
                { value: 'consultivo', label: 'Consultivo' },
                { value: 'acolhedor', label: 'Acolhedor' },
                { value: 'agil', label: 'Agil' },
              ]}
            />
            <Input
              label="Tags"
              hint="Separe por virgula para criar marcadores operacionais do atendimento."
              value={workspace.tags.join(', ')}
              onChange={(event) => handleTagChange(event.target.value)}
              placeholder="Ex.: pista, bomba, pdv"
            />
            {!lockLinkedTicket && allTickets.length > 0 ? (
              <Select
                label="Ticket vinculado"
                value={workspace.linkedTicketId ?? ''}
                onChange={(value) => {
                  const nextId = value === '' ? null : Number(value)
                  updateWorkspace({ linkedTicketId: nextId })
                  if (nextId && onSelectTicket) onSelectTicket(nextId)
                }}
                options={ticketOptions}
                includeEmpty
                emptyLabel="Sem vinculo"
                placeholder="Escolha um ticket"
              />
            ) : null}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Notas do workspace</label>
              <textarea
                value={workspace.notes}
                onChange={(event) => updateWorkspace({ notes: event.target.value })}
                rows={5}
                placeholder="Ex.: cliente prefere retorno pelo gerente da unidade, validar impressora fiscal apos ajuste..."
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-600 dark:bg-slate-900/50 dark:text-slate-100"
              />
            </div>
          </div>
        </Card>

        <Card title="Vinculo operacional">
          <div className="space-y-3 text-sm">
            <div className="rounded-2xl bg-slate-50 px-4 py-3 ring-1 ring-slate-200 dark:bg-slate-900/80 dark:ring-slate-700">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Ticket ativo</p>
              <p className="mt-1 font-semibold text-slate-900 dark:text-slate-100">#{ticket.protocolo} · {ticket.assunto}</p>
              <p className="mt-1 text-slate-500 dark:text-slate-400">
                {ticket.empresa_nome || `Empresa #${ticket.empresa_id}`} · {ticket.setor_nome || `Setor #${ticket.setor_id}`}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Mensagens</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{timeline.length}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-slate-700">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Cliente</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{customerCount}</p>
              </div>
            </div>
            <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-3 dark:border-slate-700">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Pronto para IA</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                Quando a chave do servidor estiver configurada, o botao "Sugerir com IA" usa OpenAI para montar respostas no contexto do ticket.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
