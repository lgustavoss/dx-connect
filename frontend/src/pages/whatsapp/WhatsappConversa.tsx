import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { empresas, setores, tickets, whatsappChats, type Empresas, type Setores, type WhatsappChats } from '../../api/client'
import { coletarTodasPaginas } from '../../api/collectPages'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

export function WhatsappConversa() {
  const { chatId } = useParams<{ chatId: string }>()
  const id = Number(chatId)
  const toast = useToast()

  const [chat, setChat] = useState<WhatsappChats.Chat | null>(null)
  const [msgs, setMsgs] = useState<WhatsappChats.Mensagem[]>([])
  const [loading, setLoading] = useState(true)
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [encerrando, setEncerrando] = useState(false)

  const [modalVinc, setModalVinc] = useState(false)
  const [ticketVincId, setTicketVincId] = useState('')

  const [modalAbrir, setModalAbrir] = useState(false)
  const [empresasList, setEmpresasList] = useState<Empresas.EmpresaListaItem[]>([])
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [assunto, setAssunto] = useState('')
  const [descTicket, setDescTicket] = useState('')
  const [salvandoTicket, setSalvandoTicket] = useState(false)

  const carregar = useCallback(async () => {
    if (!Number.isFinite(id) || id <= 0) return
    const c = await whatsappChats.get(id)
    const m = await whatsappChats.mensagens(id)
    setChat(c)
    setMsgs(m)
  }, [id])

  useEffect(() => {
    if (!Number.isFinite(id) || id <= 0) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        await carregar()
      } catch (err) {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o chat.'))
          setChat(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, carregar])

  useEffect(() => {
    if (!chat || chat.estado === 'encerrado') return
    const t = window.setInterval(() => {
      void carregar().catch(() => {})
    }, 5000)
    return () => window.clearInterval(t)
  }, [chat, carregar])

  useEffect(() => {
    if (!modalAbrir) return
    void coletarTodasPaginas<Empresas.EmpresaListaItem>((o, l) => empresas.list({ offset: o, limit: l }))
      .then(setEmpresasList)
      .catch(() => setEmpresasList([]))
    void coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: true, offset: o, limit: l }))
      .then(setSetoresList)
      .catch(() => setSetoresList([]))
  }, [modalAbrir])

  async function enviar() {
    if (!chat) return
    const t = texto.trim()
    if (!t) {
      toast.showWarning('Escreva uma mensagem.')
      return
    }
    setEnviando(true)
    try {
      await whatsappChats.enviar(chat.id, t)
      setTexto('')
      await carregar()
      toast.showSuccess('Mensagem enviada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao enviar.'))
    } finally {
      setEnviando(false)
    }
  }

  async function encerrar() {
    if (!chat) return
    setEncerrando(true)
    try {
      await whatsappChats.encerrar(chat.id)
      await carregar()
      toast.showSuccess('Chat encerrado.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err))
    } finally {
      setEncerrando(false)
    }
  }

  async function vincular() {
    if (!chat) return
    const tid = Number(ticketVincId)
    if (!Number.isFinite(tid) || tid <= 0) {
      toast.showWarning('Informe o ID numérico do ticket.')
      return
    }
    try {
      await tickets.get(tid)
    } catch {
      toast.showWarning('Ticket não encontrado ou sem permissão.')
      return
    }
    try {
      await whatsappChats.vincularTicket(chat.id, tid)
      setModalVinc(false)
      setTicketVincId('')
      await carregar()
      toast.showSuccess('Ticket vinculado.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err))
    }
  }

  async function abrirTicket() {
    if (!chat) return
    if (!empresaId || !setorId || !assunto.trim()) {
      toast.showWarning('Preencha empresa, setor e assunto.')
      return
    }
    setSalvandoTicket(true)
    try {
      await whatsappChats.abrirTicket(chat.id, {
        empresa_id: Number(empresaId),
        setor_id: Number(setorId),
        assunto: assunto.trim(),
        descricao: descTicket.trim() || null,
      })
      setModalAbrir(false)
      setAssunto('')
      setDescTicket('')
      await carregar()
      toast.showSuccess('Ticket criado e vinculado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível abrir o ticket.'))
    } finally {
      setSalvandoTicket(false)
    }
  }

  if (!Number.isFinite(id) || id <= 0) {
    return <p className="text-red-600">Identificador de chat inválido.</p>
  }

  if (loading && !chat) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  if (!chat) {
    return <p className="text-slate-600 dark:text-slate-400">Chat não encontrado.</p>
  }

  const encerrado = chat.estado === 'encerrado'
  const podeEnviar = chat.estado === 'em_atendimento' && !encerrado

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-10">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          to="/whatsapp/atendendo"
          className="text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
        >
          ← Voltar aos chats
        </Link>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-lg font-semibold text-cyan-700 dark:text-cyan-400">{chat.protocolo}</p>
            <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
              {chat.cliente_nome || 'Cliente'} · <span className="font-mono text-xs">{chat.wa_id}</span>
            </p>
            <p className="mt-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Estado: <span className="font-semibold">{chat.estado.replace(/_/g, ' ')}</span>
              {chat.atendente_nome && <> · Atendente: {chat.atendente_nome}</>}
            </p>
          </div>
          {!encerrado && (
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalVinc(true)}>
                Vincular ticket
              </Button>
              <Button type="button" variant="secondary" onClick={() => setModalAbrir(true)}>
                Abrir ticket
              </Button>
              {podeEnviar && (
                <Button type="button" variant="danger" loading={encerrando} onClick={() => void encerrar()}>
                  Encerrar chat
                </Button>
              )}
            </div>
          )}
        </div>
        {chat.ticket_ids.length > 0 && (
          <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
            <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Tickets vinculados</p>
            <ul className="mt-1 flex flex-wrap gap-2">
              {chat.ticket_ids.map((tid) => (
                <li key={tid}>
                  <Link
                    to={`/tickets/${tid}`}
                    className="text-sm font-medium text-cyan-700 underline hover:text-cyan-800 dark:text-cyan-400"
                  >
                    Ticket #{tid}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      <Card className="p-4">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Mensagens</h2>
        <ul className="mt-3 max-h-[420px] space-y-3 overflow-y-auto pr-1">
          {msgs.map((m) => (
            <li
              key={m.id}
              className={`rounded-lg px-3 py-2 text-sm ${
                m.direcao === 'inbound'
                  ? 'ml-0 mr-8 bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                  : 'ml-8 mr-0 bg-cyan-50 text-slate-900 dark:bg-cyan-950/40 dark:text-slate-100'
              }`}
            >
              <p className="whitespace-pre-wrap">{m.corpo}</p>
              <p className="mt-1 text-[10px] text-slate-500 dark:text-slate-400">
                {m.direcao === 'outbound' ? m.atendente_nome || 'Equipe' : 'Cliente'} ·{' '}
                {m.created_at ? new Date(m.created_at).toLocaleString('pt-BR') : '—'}
              </p>
            </li>
          ))}
        </ul>

        {podeEnviar && (
          <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-700">
            <label className="sr-only" htmlFor="wa-msg">
              Nova mensagem
            </label>
            <textarea
              id="wa-msg"
              rows={3}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              placeholder="Digite a mensagem para o cliente…"
            />
            <div className="mt-2 flex justify-end">
              <Button type="button" loading={enviando} onClick={() => void enviar()}>
                Enviar
              </Button>
            </div>
          </div>
        )}
        {encerrado && (
          <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">Conversa encerrada (somente leitura).</p>
        )}
        {chat.estado === 'aguardando_atendente' && !encerrado && (
          <p className="mt-4 text-sm text-amber-800 dark:text-amber-200">
            Este chat ainda está na fila. Assuma-o em <Link to="/whatsapp/atendendo">Atendendo</Link> para poder responder.
          </p>
        )}
      </Card>

      {modalVinc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog">
          <Card className="w-full max-w-md p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Vincular a ticket existente</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Informe o ID interno do ticket (número da URL).</p>
            <Input
              className="mt-3"
              type="number"
              value={ticketVincId}
              onChange={(e) => setTicketVincId(e.target.value)}
              placeholder="Ex.: 42"
            />
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalVinc(false)}>
                Cancelar
              </Button>
              <Button type="button" onClick={() => void vincular()}>
                Vincular
              </Button>
            </div>
          </Card>
        </div>
      )}

      {modalAbrir && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog">
          <Card className="max-h-[90vh] w-full max-w-lg overflow-y-auto p-4 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Abrir ticket a partir do chat</h3>
            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Empresa</label>
                <Select
                  value={empresaId === '' ? '' : empresaId}
                  onChange={(v) => setEmpresaId(v === '' ? '' : Number(v))}
                  includeEmpty
                  emptyLabel="Selecione…"
                  options={empresasList.map((e) => ({ value: e.id, label: e.nome }))}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Setor</label>
                <Select
                  value={setorId === '' ? '' : setorId}
                  onChange={(v) => setSetorId(v === '' ? '' : Number(v))}
                  includeEmpty
                  emptyLabel="Selecione…"
                  options={setoresList.filter((s) => s.ativo).map((s) => ({ value: s.id, label: s.nome }))}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Assunto</label>
                <Input value={assunto} onChange={(e) => setAssunto(e.target.value)} placeholder="Resumo do problema" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Descrição (opcional)</label>
                <textarea
                  value={descTicket}
                  onChange={(e) => setDescTicket(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalAbrir(false)}>
                Cancelar
              </Button>
              <Button type="button" loading={salvandoTicket} onClick={() => void abrirTicket()}>
                Criar ticket
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
