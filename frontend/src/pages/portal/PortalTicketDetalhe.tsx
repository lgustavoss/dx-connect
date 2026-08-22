import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { portalCliente, type PortalCliente } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { VoltarButton } from '../../components/ui/VoltarButton'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

function formatData(iso?: string | null) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

type PortalTicketDetalheProps = {
  ticketIdProp?: number
  onVoltar?: () => void
}

export function PortalTicketDetalhe({ ticketIdProp, onVoltar }: PortalTicketDetalheProps = {}) {
  const { id } = useParams<{ id: string }>()
  const ticketId = ticketIdProp ?? Number(id)
  const [ticket, setTicket] = useState<PortalCliente.TicketDetail | null>(null)
  const [mensagens, setMensagens] = useState<PortalCliente.Mensagem[]>([])
  const [loading, setLoading] = useState(true)
  const [corpo, setCorpo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const toast = useToast()
  const navigate = useNavigate()

  const voltarLista = useCallback(() => {
    if (onVoltar) {
      onVoltar()
      return
    }
    navigate('/portal/tickets')
  }, [onVoltar, navigate])

  const carregar = useCallback(async () => {
    if (!Number.isFinite(ticketId)) return
    const [t, msgs] = await Promise.all([
      portalCliente.getTicket(ticketId),
      portalCliente.listMensagens(ticketId),
    ])
    setTicket(t)
    setMensagens(msgs)
  }, [ticketId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    carregar()
      .catch((err) => {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Chamado não encontrado.'))
          voltarLista()
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [carregar, voltarLista, toast])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [mensagens.length])

  // Polling leve para novas respostas da equipe
  useEffect(() => {
    if (!ticket?.pode_responder) return
    const t = window.setInterval(() => {
      carregar().catch(() => undefined)
    }, 15000)
    return () => window.clearInterval(t)
  }, [carregar, ticket?.pode_responder])

  async function handleEnviar(e: React.FormEvent) {
    e.preventDefault()
    if (!ticket || !ticket.pode_responder) return
    const texto = corpo.trim()
    if (!texto && !file) {
      toast.showError('Escreva uma mensagem ou anexe um ficheiro.')
      return
    }
    setEnviando(true)
    try {
      let msg: PortalCliente.Mensagem | null = null
      if (texto) {
        msg = await portalCliente.sendMensagem(ticket.id, texto)
      }
      if (file) {
        await portalCliente.uploadAnexo(ticket.id, file, msg?.id)
      }
      setCorpo('')
      setFile(null)
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar.'))
    } finally {
      setEnviando(false)
    }
  }

  async function baixarAnexo(anexo: PortalCliente.Anexo) {
    if (!ticket) return
    try {
      const blob = await portalCliente.fetchAnexoBlob(ticket.id, anexo.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = anexo.nome_original
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao baixar anexo.'))
    }
  }

  async function abrirCsat() {
    if (!ticket) return
    try {
      const { link } = await portalCliente.csatLink(ticket.id)
      window.location.href = link
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Avaliação indisponível no momento.'))
    }
  }

  if (loading || !ticket) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-lg bg-slate-100" />
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
      </div>
    )
  }

  return (
    <div className="flex min-h-[70dvh] flex-col gap-4">
      <div>
        <VoltarButton onClick={voltarLista} className="mb-2" />
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="font-mono text-xs font-semibold text-teal-700">{ticket.protocolo}</p>
          <h1 className="mt-1 text-lg font-semibold text-slate-900">{ticket.assunto}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {ticket.status_nome} · {ticket.empresa_nome} · {ticket.setor_nome}
          </p>
        </div>
      </div>

      {ticket.csat_pendente ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="font-medium">Como foi o atendimento?</p>
          <p className="mt-0.5 text-amber-900/80">Sua avaliação ajuda a melhorar o suporte.</p>
          <button
            type="button"
            onClick={abrirCsat}
            className="mt-2 text-sm font-semibold text-amber-900 underline underline-offset-2"
          >
            Avaliar agora
          </button>
        </div>
      ) : null}

      {!ticket.pode_responder ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          Este chamado está encerrado.{' '}
          <Link to="/portal/tickets/novo" className="font-semibold text-teal-700 underline-offset-2 hover:underline">
            Abrir um novo chamado
          </Link>{' '}
          se ainda precisar de ajuda.
        </div>
      ) : null}

      <div className="flex-1 space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        {mensagens.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">Ainda sem mensagens nesta conversa.</p>
        ) : (
          mensagens.map((m) => {
            const mine = m.autor_papel === 'voce'
            return (
              <div key={m.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={[
                    'max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm shadow-sm sm:max-w-[80%]',
                    mine
                      ? 'rounded-br-md bg-teal-600 text-white'
                      : 'rounded-bl-md border border-slate-200 bg-slate-50 text-slate-800',
                  ].join(' ')}
                >
                  <p className={`text-[11px] font-medium ${mine ? 'text-teal-100' : 'text-slate-500'}`}>
                    {m.autor_nome || (mine ? 'Você' : 'Equipe')} · {formatData(m.created_at)}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap break-words">{m.corpo}</p>
                  {m.anexos?.length ? (
                    <ul className="mt-2 space-y-1">
                      {m.anexos.map((a) => (
                        <li key={a.id}>
                          <button
                            type="button"
                            onClick={() => baixarAnexo(a)}
                            className={`text-xs underline underline-offset-2 ${mine ? 'text-teal-50' : 'text-teal-700'}`}
                          >
                            {a.nome_original}
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>

      {ticket.pode_responder ? (
        <form
          onSubmit={handleEnviar}
          className="sticky bottom-20 z-10 space-y-2 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-lg backdrop-blur sm:static sm:bottom-auto"
        >
          <textarea
            value={corpo}
            onChange={(e) => setCorpo(e.target.value)}
            rows={3}
            placeholder="Escreva sua mensagem…"
            className="w-full resize-none rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/25"
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="cursor-pointer text-xs font-medium text-teal-700 hover:underline">
              <input
                type="file"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              {file ? `Anexo: ${file.name}` : 'Anexar ficheiro'}
            </label>
            <Button type="submit" disabled={enviando}>
              {enviando ? 'Enviando…' : 'Enviar'}
            </Button>
          </div>
        </form>
      ) : null}
    </div>
  )
}
