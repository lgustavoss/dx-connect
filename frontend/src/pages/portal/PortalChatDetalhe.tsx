import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { portalCliente, type PortalCliente } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'

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

function estadoLabel(estado: string) {
  const s = (estado || '').toLowerCase()
  if (s === 'encerrado') return 'Encerrado'
  if (s === 'em_atendimento') return 'Em atendimento'
  if (s === 'aguardando_atendente') return 'Aguardando'
  return estado || '—'
}

type PortalChatDetalheProps = {
  chatIdProp?: number
  onVoltar?: () => void
}

export function PortalChatDetalhe({ chatIdProp, onVoltar }: PortalChatDetalheProps = {}) {
  const { id } = useParams<{ id: string }>()
  const chatId = chatIdProp ?? Number(id)
  const [chat, setChat] = useState<PortalCliente.WhatsappChatDetail | null>(null)
  const [mensagens, setMensagens] = useState<PortalCliente.WhatsappMensagem[]>([])
  const [loading, setLoading] = useState(true)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const toast = useToast()
  const navigate = useNavigate()
  const voltarLista = useCallback(() => {
    if (onVoltar) {
      onVoltar()
      return
    }
    navigate('/portal/chats')
  }, [onVoltar, navigate])

  const carregar = useCallback(async () => {
    if (!Number.isFinite(chatId)) return
    const [c, msgs] = await Promise.all([
      portalCliente.getChat(chatId),
      portalCliente.listChatMensagens(chatId),
    ])
    setChat(c)
    setMensagens(msgs)
  }, [chatId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    carregar()
      .catch((err) => {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Atendimento não encontrado.'))
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

  useEffect(() => {
    if (!chat || chat.encerrado) return
    const t = window.setInterval(() => {
      carregar().catch(() => undefined)
    }, 15000)
    return () => window.clearInterval(t)
  }, [carregar, chat])

  async function abrirMidia(msg: PortalCliente.WhatsappMensagem) {
    if (!chat || !msg.midia_disponivel) return
    try {
      const blob = await portalCliente.fetchChatMidiaBlob(chat.id, msg.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível abrir a mídia.'))
    }
  }

  if (loading || !chat) {
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
        <button
          type="button"
          onClick={voltarLista}
          className="mb-2 text-sm font-medium text-slate-500 hover:text-slate-800"
        >
          ← Voltar
        </button>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="font-mono text-xs font-semibold text-teal-700">{chat.protocolo}</p>
          <h1 className="mt-1 text-lg font-semibold text-slate-900">Atendimento WhatsApp</h1>
          <p className="mt-1 text-sm text-slate-500">
            {estadoLabel(chat.estado)}
            {chat.empresa_nome ? ` · ${chat.empresa_nome}` : ''}
            {chat.setor_nome ? ` · ${chat.setor_nome}` : ''}
          </p>
        </div>
      </div>

      {chat.encerrado ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          Este atendimento está encerrado. Para nova conversa, envie mensagem pelo WhatsApp ou{' '}
          <Link to="/portal/tickets/novo" className="font-semibold text-teal-700 underline-offset-2 hover:underline">
            abra um chamado
          </Link>
          .
        </div>
      ) : (
        <p className="text-xs text-slate-500">
          Visualização somente leitura. Continue a conversa pelo WhatsApp se o atendimento estiver ativo.
        </p>
      )}

      <div className="flex-1 space-y-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
        {mensagens.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">Nenhuma mensagem visível.</p>
        ) : (
          mensagens.map((m) => {
            const isVoce = m.autor_papel === 'voce'
            return (
              <div key={m.id} className={`flex ${isVoce ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={[
                    'max-w-[85%] rounded-2xl px-3 py-2 text-sm shadow-sm',
                    isVoce ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-900',
                  ].join(' ')}
                >
                  <p className={`text-[10px] font-medium ${isVoce ? 'text-teal-100' : 'text-slate-500'}`}>
                    {m.autor_nome || (isVoce ? 'Você' : 'Equipe')}
                  </p>
                  <p className="mt-0.5 whitespace-pre-wrap break-words">{m.corpo}</p>
                  {m.midia_disponivel ? (
                    <button
                      type="button"
                      onClick={() => abrirMidia(m)}
                      className={`mt-1 text-xs font-semibold underline underline-offset-2 ${
                        isVoce ? 'text-teal-100' : 'text-teal-700'
                      }`}
                    >
                      Ver {m.tipo_midia || 'anexo'}
                    </button>
                  ) : null}
                  <p className={`mt-1 text-[10px] ${isVoce ? 'text-teal-100/80' : 'text-slate-400'}`}>
                    {formatData(m.created_at)}
                  </p>
                </div>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
