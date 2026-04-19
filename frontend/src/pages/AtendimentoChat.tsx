import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { tickets, whatsapp, type Tickets, type WhatsApp } from '../api/client'
import { Button } from '../components/ui/Button'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'

function formatPhone(phone?: string | null) {
  if (!phone) return 'Sem telefone'
  const digits = phone.replace(/\D+/g, '')
  if (digits.length === 13) {
    return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 9)}-${digits.slice(9)}`
  }
  if (digits.length === 12) {
    return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 8)}-${digits.slice(8)}`
  }
  return phone
}

function formatDateTime(value?: string | null) {
  if (!value) return 'Sem atividade'
  return new Date(value).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusLabel(status: string) {
  if (status === 'pending') return 'Aguardando'
  if (status === 'resolved') return 'Resolvido'
  return 'Aberto'
}

function statusClass(status: string) {
  if (status === 'resolved') return 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200'
  if (status === 'pending') return 'bg-amber-100 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200'
  return 'bg-sky-100 text-sky-900 dark:bg-sky-950/40 dark:text-sky-200'
}

function messageTypeLabel(message: WhatsApp.Message) {
  if (message.direction === 'outbound') return 'Equipe'
  if (message.message_type === 'image') return 'Imagem'
  if (message.message_type === 'document') return 'Documento'
  if (message.message_type === 'audio') return 'Audio'
  return 'Cliente'
}

export function AtendimentoChat() {
  const toast = useToast()
  const navigate = useNavigate()
  const [ticketOptions, setTicketOptions] = useState<Tickets.Ticket[]>([])
  const [conversations, setConversations] = useState<WhatsApp.Conversation[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [activeConversation, setActiveConversation] = useState<WhatsApp.Conversation | null>(null)
  const [search, setSearch] = useState('')
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [assisting, setAssisting] = useState(false)

  async function loadConversationList() {
    setLoadingList(true)
    try {
      const [{ items: convs }, { items: ticketList }] = await Promise.all([
        whatsapp.listConversations({ limit: 100 }),
        tickets.list({ limit: 100 }),
      ])
      setConversations(convs)
      setTicketOptions(ticketList)
      setActiveId((current) => current ?? convs[0]?.id ?? null)
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Nao foi possivel carregar a inbox do WhatsApp.')
    } finally {
      setLoadingList(false)
    }
  }

  async function loadConversation(id: number) {
    setLoadingDetail(true)
    try {
      const conv = await whatsapp.getConversation(id)
      setActiveConversation(conv)
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Nao foi possivel abrir a conversa.')
    } finally {
      setLoadingDetail(false)
    }
  }

  useEffect(() => {
    loadConversationList()
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      loadConversationList()
      if (activeId) {
        loadConversation(activeId)
      }
    }, 10000)
    return () => window.clearInterval(interval)
  }, [activeId])

  useEffect(() => {
    if (!activeId) {
      setActiveConversation(null)
      return
    }
    loadConversation(activeId)
  }, [activeId])

  const filteredConversations = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return conversations
    return conversations.filter((conversation) =>
      [
        conversation.profile_name,
        conversation.phone_number,
        conversation.linked_ticket_protocolo,
        conversation.linked_ticket_assunto,
        conversation.linked_ticket_empresa_nome,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term)),
    )
  }, [conversations, search])

  const totalOpen = conversations.filter((item) => item.status === 'open').length
  const totalAi = conversations.filter((item) => item.ai_enabled).length
  const linkedCount = conversations.filter((item) => item.linked_ticket_id).length

  async function handleLinkTicket(ticketId: number | '') {
    if (!activeConversation) return
    try {
      const updated = await whatsapp.updateConversation(activeConversation.id, {
        linked_ticket_id: ticketId === '' ? null : Number(ticketId),
      })
      setActiveConversation(updated)
      setConversations((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      toast.showSuccess(ticketId === '' ? 'Conversa desvinculada do ticket.' : 'Conversa vinculada ao ticket.')
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Nao foi possivel atualizar o vinculo.')
    }
  }

  async function handleUpdateConversation(patch: WhatsApp.ConversationUpdate) {
    if (!activeConversation) return
    try {
      const updated = await whatsapp.updateConversation(activeConversation.id, patch)
      setActiveConversation(updated)
      setConversations((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Nao foi possivel atualizar a conversa.')
    }
  }

  async function handleAssist(autoSend = false) {
    if (!activeConversation) return
    setAssisting(true)
    try {
      const response = await whatsapp.assist(activeConversation.id, {
        auto_send: autoSend,
        objective: activeConversation.linked_ticket_id
          ? 'Responder o cliente com base no ticket vinculado e pedir apenas o que falta para avancar.'
          : 'Fazer triagem inicial, identificar unidade, problema e impacto na operacao.',
      })
      if (response.sent) {
        await loadConversation(activeConversation.id)
        await loadConversationList()
        setDraft('')
        toast.showSuccess('IA respondeu o cliente no WhatsApp.')
      } else {
        setDraft(response.reply)
        toast.showSuccess(response.source === 'openai' ? 'Rascunho gerado com OpenAI.' : 'Rascunho gerado pelo fallback local.')
      }
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Nao foi possivel gerar resposta com IA.')
    } finally {
      setAssisting(false)
    }
  }

  async function handleSend() {
    if (!activeConversation) return
    const body = draft.trim()
    if (!body) {
      toast.showWarning('Escreva uma resposta antes de enviar.')
      return
    }
    setSending(true)
    try {
      const updated = await whatsapp.sendMessage(activeConversation.id, { body })
      setActiveConversation(updated)
      setConversations((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setDraft('')
      toast.showSuccess('Mensagem enviada para o WhatsApp.')
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Nao foi possivel enviar a mensagem.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Atendimento WhatsApp</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Inbox operacional do numero de suporte. As mensagens recebidas entram aqui em tempo real, podem ser vinculadas a tickets e contam com IA para triagem e apoio de resposta.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link to="/tickets">
            <Button type="button" variant="secondary">Ver tickets</Button>
          </Link>
          <Button type="button" onClick={() => navigate('/tickets/novo')}>Novo ticket</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-3xl border border-slate-200/90 bg-white px-5 py-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400 dark:text-slate-500">Conversas</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">{conversations.length}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Contatos ativos no numero do suporte.</p>
        </div>
        <div className="rounded-3xl border border-slate-200/90 bg-white px-5 py-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400 dark:text-slate-500">Abertas</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">{totalOpen}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Conversas aguardando tratativa da equipe.</p>
        </div>
        <div className="rounded-3xl border border-slate-200/90 bg-white px-5 py-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400 dark:text-slate-500">IA ativa</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">{totalAi}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{linkedCount} conversas ja vinculadas a tickets.</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="overflow-hidden rounded-[28px] border border-slate-200/90 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50">
          <div className="border-b border-slate-200/80 px-5 py-4 dark:border-slate-700/70">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Inbox do numero</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Selecione uma conversa recebida no WhatsApp.</p>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar nome, telefone ou ticket..."
              className="mt-4 w-full rounded-xl border-0 bg-slate-50 px-3 py-2 text-sm text-slate-900 shadow-inner ring-1 ring-slate-200/80 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-300/60 dark:bg-slate-950 dark:text-slate-100 dark:ring-slate-700"
            />
          </div>

          <div className="max-h-[calc(100vh-17rem)] overflow-y-auto">
            {loadingList ? (
              <div className="px-5 py-10 text-sm text-slate-500 dark:text-slate-400">Carregando conversas...</div>
            ) : filteredConversations.length === 0 ? (
              <div className="px-5 py-10 text-sm text-slate-500 dark:text-slate-400">Nenhuma conversa encontrada.</div>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredConversations.map((conversation) => {
                  const active = conversation.id === activeId
                  const lastMessage = conversation.messages[conversation.messages.length - 1]
                  return (
                    <li key={conversation.id}>
                      <button
                        type="button"
                        onClick={() => setActiveId(conversation.id)}
                        className={`w-full px-5 py-4 text-left transition-colors ${
                          active ? 'bg-sky-50/80 dark:bg-sky-950/20' : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] ${statusClass(conversation.status)}`}>
                                {statusLabel(conversation.status)}
                              </span>
                              {conversation.ai_enabled ? (
                                <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-white dark:bg-slate-100 dark:text-slate-900">
                                  IA
                                </span>
                              ) : null}
                            </div>
                            <p className="mt-2 truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                              {conversation.profile_name || formatPhone(conversation.phone_number)}
                            </p>
                            <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
                              {formatPhone(conversation.phone_number)}
                            </p>
                            <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">
                              {lastMessage?.body || 'Sem mensagem textual'}
                            </p>
                            <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
                              {conversation.linked_ticket_protocolo
                                ? `Ticket #${conversation.linked_ticket_protocolo} · ${conversation.linked_ticket_assunto || 'Vinculado'}`
                                : 'Sem ticket vinculado'}
                            </p>
                          </div>
                          <span className="text-[11px] text-slate-400 dark:text-slate-500">
                            {formatDateTime(conversation.last_message_at)}
                          </span>
                        </div>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </aside>

        <div>
          {loadingDetail ? (
            <div className="flex min-h-[40vh] items-center justify-center rounded-[28px] border border-slate-200/90 bg-white text-sm text-slate-500 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50 dark:text-slate-400">
              Carregando conversa selecionada...
            </div>
          ) : activeConversation ? (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_360px]">
              <section className="overflow-hidden rounded-[28px] border border-slate-200/90 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50">
                <div className="border-b border-slate-200/80 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.14),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.14),_transparent_35%),linear-gradient(135deg,rgba(255,255,255,0.98),rgba(240,249,255,0.88))] px-5 py-5 dark:border-slate-700/70 dark:bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.16),_transparent_30%),linear-gradient(135deg,rgba(15,23,42,0.92),rgba(12,74,110,0.3))] sm:px-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${statusClass(activeConversation.status)}`}>
                          {statusLabel(activeConversation.status)}
                        </span>
                        <span className="rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-white dark:bg-slate-100 dark:text-slate-900">
                          WhatsApp
                        </span>
                        {activeConversation.ai_enabled ? (
                          <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
                            IA automatica
                          </span>
                        ) : null}
                      </div>
                      <h2 className="mt-3 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
                        {activeConversation.profile_name || 'Contato sem nome'}
                      </h2>
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                        {formatPhone(activeConversation.phone_number)} · ultima atividade em {formatDateTime(activeConversation.last_message_at)}
                      </p>
                      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                        {activeConversation.linked_ticket_protocolo
                          ? `Vinculado ao ticket #${activeConversation.linked_ticket_protocolo} (${activeConversation.linked_ticket_empresa_nome || 'cliente'})`
                          : 'Conversa ainda sem ticket vinculado. Use o painel lateral para anexar ao chamado correto.'}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {activeConversation.linked_ticket_id ? (
                        <Link to={`/tickets/${activeConversation.linked_ticket_id}`}>
                          <Button type="button" variant="secondary">Abrir ticket</Button>
                        </Link>
                      ) : null}
                      <Button type="button" variant="secondary" onClick={() => handleAssist(false)} loading={assisting}>
                        Sugerir IA
                      </Button>
                      <Button type="button" onClick={() => handleAssist(true)} loading={assisting}>
                        IA responder
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 px-5 py-5 sm:px-6">
                  {activeConversation.messages.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-300 px-5 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                      Nenhuma mensagem recebida ainda.
                    </div>
                  ) : (
                    activeConversation.messages.map((message) => {
                      const inbound = message.direction === 'inbound'
                      return (
                        <article key={message.id} className={`flex ${inbound ? 'justify-start' : 'justify-end'}`}>
                          <div
                            className={`max-w-[88%] rounded-[24px] px-4 py-3 shadow-sm ring-1 ${
                              inbound
                                ? 'bg-slate-100 text-slate-900 ring-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700'
                                : 'bg-[linear-gradient(135deg,rgba(5,150,105,1),rgba(37,99,235,1))] text-white ring-emerald-500/25'
                            }`}
                          >
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div>
                                <p className={`text-xs font-semibold uppercase tracking-[0.12em] ${inbound ? 'text-slate-500 dark:text-slate-400' : 'text-emerald-50/90'}`}>
                                  {messageTypeLabel(message)}
                                </p>
                                <p className={`text-xs ${inbound ? 'text-slate-400 dark:text-slate-500' : 'text-blue-50/85'}`}>
                                  {message.message_type} {message.status ? `· ${message.status}` : ''}
                                </p>
                              </div>
                              <time className={`text-[11px] ${inbound ? 'text-slate-400 dark:text-slate-500' : 'text-white/70'}`}>
                                {formatDateTime(message.created_at)}
                              </time>
                            </div>
                            <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{message.body || 'Mensagem sem corpo textual.'}</p>
                            {message.filename || message.mime_type ? (
                              <p className={`mt-3 text-xs ${inbound ? 'text-slate-500 dark:text-slate-400' : 'text-white/75'}`}>
                                {message.filename || message.mime_type}
                              </p>
                            ) : null}
                          </div>
                        </article>
                      )
                    })
                  )}
                </div>

                <div className="border-t border-slate-200/80 bg-slate-50/70 px-5 py-5 dark:border-slate-700/70 dark:bg-slate-950/35 sm:px-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Responder no WhatsApp</h3>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        O envio sai pelo numero configurado na Cloud API e fica registrado aqui e no ticket vinculado.
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 space-y-3">
                    <textarea
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      rows={5}
                      placeholder="Escreva a resposta ao cliente..."
                      className="w-full rounded-[24px] border-0 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm ring-1 ring-slate-200/90 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-300/50 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700"
                    />
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Use "Sugerir IA" para rascunho ou "IA responder" para envio automatico.
                      </p>
                      <Button type="button" onClick={handleSend} loading={sending}>
                        Enviar mensagem
                      </Button>
                    </div>
                  </div>
                </div>
              </section>

              <aside className="space-y-6">
                <div className="rounded-[28px] border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Vinculo e automacao</h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Anexe a conversa a um ticket existente e defina como a IA deve apoiar esse cliente.
                  </p>
                  <div className="mt-4 space-y-4">
                    <Select
                      label="Ticket vinculado"
                      value={activeConversation.linked_ticket_id ?? ''}
                      onChange={(value) => handleLinkTicket(value === '' ? '' : Number(value))}
                      options={ticketOptions.map((ticket) => ({
                        value: ticket.id,
                        label: `#${ticket.protocolo} · ${ticket.assunto}`,
                      }))}
                      includeEmpty
                      emptyLabel="Sem vinculo"
                      placeholder="Escolha um ticket"
                    />
                    <Select
                      label="Status da conversa"
                      value={activeConversation.status}
                      onChange={(value) => handleUpdateConversation({ status: value as WhatsApp.ConversationUpdate['status'] })}
                      options={[
                        { value: 'open', label: 'Aberto' },
                        { value: 'pending', label: 'Aguardando cliente' },
                        { value: 'resolved', label: 'Resolvido' },
                      ]}
                    />
                    <Select
                      label="Modo de IA"
                      value={activeConversation.ai_mode}
                      onChange={(value) => handleUpdateConversation({ ai_mode: value as WhatsApp.ConversationUpdate['ai_mode'] })}
                      options={[
                        { value: 'assist', label: 'Assistente de triagem' },
                        { value: 'copilot', label: 'Copiloto humano' },
                      ]}
                    />
                    <button
                      type="button"
                      onClick={() => handleUpdateConversation({ ai_enabled: !activeConversation.ai_enabled })}
                      className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left text-sm transition-colors ${
                        activeConversation.ai_enabled
                          ? 'border-emerald-300 bg-emerald-50 text-emerald-950 dark:border-emerald-800/60 dark:bg-emerald-950/30 dark:text-emerald-100'
                          : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-950/30 dark:text-slate-200'
                      }`}
                    >
                      <span>
                        <span className="block font-semibold">IA automatica</span>
                        <span className="mt-1 block text-xs opacity-80">
                          Quando ativa, respostas automaticas podem ser disparadas ao receber novas mensagens.
                        </span>
                      </span>
                      <span className="text-xs font-semibold uppercase tracking-[0.12em]">
                        {activeConversation.ai_enabled ? 'Ativa' : 'Desligada'}
                      </span>
                    </button>
                  </div>
                </div>

                <div className="rounded-[28px] border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/50">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Propriedades do contato</h3>
                  <div className="mt-4 space-y-3 text-sm">
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 ring-1 ring-slate-200 dark:bg-slate-950/50 dark:ring-slate-700">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Nome</p>
                      <p className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{activeConversation.profile_name || 'Nao informado pelo WhatsApp'}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 ring-1 ring-slate-200 dark:bg-slate-950/50 dark:ring-slate-700">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Telefone</p>
                      <p className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{formatPhone(activeConversation.phone_number)}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 px-4 py-3 ring-1 ring-slate-200 dark:bg-slate-950/50 dark:ring-slate-700">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500">Ligacao com ticket</p>
                      <p className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
                        {activeConversation.linked_ticket_protocolo
                          ? `#${activeConversation.linked_ticket_protocolo}`
                          : 'Ainda sem ticket'}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {activeConversation.linked_ticket_assunto || 'Ao vincular, as mensagens do cliente tambem entram no ticket.'}
                      </p>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          ) : (
            <div className="flex min-h-[40vh] items-center justify-center rounded-[28px] border border-dashed border-slate-300 bg-white text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
              Assim que chegar uma mensagem no numero conectado, ela aparecera aqui.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
