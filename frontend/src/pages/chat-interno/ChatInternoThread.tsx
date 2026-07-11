import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, chatInterno, type ChatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ChatInternoComposer } from '../../components/chat-interno/ChatInternoComposer'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../contexts/AuthContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'
import { SemPermissao } from '../SemPermissao'

function formatarHoraMensagem(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function ChatInternoThread() {
  const { conversaId: conversaIdParam } = useParams()
  const conversaId = Number(conversaIdParam)
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const { subscribe, useFallback } = useEventStream()

  const [meta, setMeta] = useState<ChatInterno.ConversaInbox | null>(null)
  const [mensagens, setMensagens] = useState<ChatInterno.Mensagem[]>([])
  const [texto, setTexto] = useState('')
  const [loading, setLoading] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [erro, setErro] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const carregarMensagens = useCallback(async () => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) return
    try {
      const pagina = await chatInterno.mensagens(conversaId, { offset: 0, limit: 100 })
      setMensagens(pagina.items)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
      }
    }
  }, [conversaId])

  const carregar = useCallback(async () => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) return
    setErro(false)
    setForbidden(false)
    try {
      const inbox = await chatInterno.listarConversas()
      const encontrada = inbox.find((c) => c.id === conversaId) ?? null
      setMeta(encontrada)
      const pagina = await chatInterno.mensagens(conversaId, { offset: 0, limit: 100 })
      setMensagens(pagina.items)
      await chatInterno.marcarVisto(conversaId)
      void refetchPendenciasResumo()
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
        return
      }
      setErro(true)
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar a conversa.'))
    } finally {
      setLoading(false)
    }
  }, [conversaId, toast])

  useEffect(() => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) {
      navigate('/chat-interno', { replace: true })
      return
    }
    setLoading(true)
    void carregar()
  }, [conversaId, carregar, navigate])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [mensagens])

  useEffect(() => {
    const unsub = subscribe('chat.interno.mensagem', (payload) => {
      if (Number(payload.conversa_id) !== conversaId) return
      void carregarMensagens()
      void refetchPendenciasResumo()
    })
    return unsub
  }, [subscribe, conversaId, carregarMensagens])

  useEffect(() => {
    const intervalMs = useFallback ? 10_000 : 6_000
    const timer = setInterval(() => void carregarMensagens(), intervalMs)
    return () => clearInterval(timer)
  }, [carregarMensagens, useFallback])

  async function enviar() {
    const corpo = texto.trim()
    if (!corpo || enviando) return
    setEnviando(true)
    try {
      const msg = await chatInterno.enviar(conversaId, corpo)
      setTexto('')
      setMensagens((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]))
      void refetchPendenciasResumo()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a mensagem.'))
    } finally {
      setEnviando(false)
    }
  }

  if (!Number.isFinite(conversaId) || conversaId <= 0) return null

  if (forbidden) {
    return (
      <div className="mx-auto max-w-3xl p-4">
        <SemPermissao
          title="Sem permissão para esta conversa"
          detail="Você não participa deste chat ou não tem acesso ao canal do setor."
          voltarPara="/chat-interno"
          voltarLabel="Voltar ao inbox"
        />
      </div>
    )
  }

  const titulo = meta?.titulo ?? 'Conversa'
  const isSetor = meta?.tipo === 'setor'

  return (
    <div className="flex h-[calc(100vh-140px)] min-h-[500px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
      <header className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
        <Link
          to="/chat-interno"
          className="rounded-lg px-2 py-1 text-sm font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          ← Inbox
        </Link>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-bold text-slate-900 dark:text-white">{titulo}</h1>
          <p className="text-xs text-slate-500">
            {isSetor ? 'Canal do setor — comunicados' : 'Conversa direta'}
          </p>
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {loading ? (
          <p className="text-center text-sm text-slate-400 animate-pulse">Carregando mensagens…</p>
        ) : erro ? (
          <p className="text-center text-sm text-rose-600">Erro ao carregar. Tente voltar ao inbox.</p>
        ) : mensagens.length === 0 ? (
          <p className="text-center text-sm text-slate-400">
            {isSetor ? 'Nenhum comunicado ainda. Publique o primeiro aviso.' : 'Nenhuma mensagem. Diga olá!'}
          </p>
        ) : (
          mensagens.map((m) => {
            const propria = m.atendente_id === user?.id
            if (isSetor) {
              return (
                <article
                  key={m.id}
                  className="rounded-xl border border-amber-200/80 bg-amber-50/90 p-4 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/30"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-200">
                    <span>Comunicado</span>
                    <span className="font-normal normal-case text-slate-500">
                      {m.atendente_nome ?? 'Atendente'} · {formatarHoraMensagem(m.created_at)}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-100">{m.corpo}</p>
                </article>
              )
            }
            return (
              <div key={m.id} className={`flex ${propria ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                    propria
                      ? 'rounded-tr-none bg-violet-600 text-white'
                      : 'rounded-tl-none bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                  }`}
                >
                  {!propria && (
                    <p className="mb-1 text-[11px] font-semibold opacity-80">{m.atendente_nome ?? 'Atendente'}</p>
                  )}
                  <p className="whitespace-pre-wrap">{m.corpo}</p>
                  <p className={`mt-1 text-[10px] ${propria ? 'text-violet-100' : 'text-slate-400'}`}>
                    {formatarHoraMensagem(m.created_at)}
                  </p>
                </div>
              </div>
            )
          })
        )}
      </div>

      <ChatInternoComposer
        texto={texto}
        onTextoChange={setTexto}
        onEnviar={() => void enviar()}
        enviando={enviando}
        placeholder={isSetor ? 'Novo comunicado para o setor…' : 'Escreva uma mensagem…'}
        labelEnviar={isSetor ? 'Publicar' : 'Enviar'}
      />
    </div>
  )
}
