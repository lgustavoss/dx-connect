import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, chatInterno, type ChatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ChatInternoComposerBar } from '../../components/chat-interno/ChatInternoComposerBar'
import { ChatInternoConteudoMensagem } from '../../components/chat-interno/ChatInternoConteudoMensagem'
import { MensagemRodapeMeta } from '../../components/chat/MensagemRodapeMeta'
import { useChatInterno } from '../../contexts/ChatInternoContext'
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
  const { obterConversa, carregar: refreshInbox } = useChatInterno()

  const meta = obterConversa(conversaId)
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
      await chatInterno.marcarVisto(conversaId)
      void refetchPendenciasResumo()
      void refreshInbox(true)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
      }
    }
  }, [conversaId, refreshInbox])

  const carregar = useCallback(async () => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) return
    setErro(false)
    setForbidden(false)
    try {
      const pagina = await chatInterno.mensagens(conversaId, { offset: 0, limit: 100 })
      setMensagens(pagina.items)
      await chatInterno.marcarVisto(conversaId)
      void refetchPendenciasResumo()
      void refreshInbox(true)
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
  }, [conversaId, toast, refreshInbox])

  useEffect(() => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) {
      navigate('/chat/interno', { replace: true })
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
    const unsubMsg = subscribe('chat.interno.mensagem', (payload) => {
      const id = Number(payload.conversa_id)
      void refreshInbox(true)
      if (id !== conversaId) return
      void carregarMensagens()
    })
    const unsubLido = subscribe('chat.interno.lido', (payload) => {
      if (Number(payload.conversa_id) !== conversaId) return
      void carregarMensagens()
    })
    return () => {
      unsubMsg()
      unsubLido()
    }
  }, [subscribe, conversaId, carregarMensagens, refreshInbox])

  useEffect(() => {
    const intervalMs = useFallback ? 10_000 : 6_000
    const timer = setInterval(() => void carregarMensagens(), intervalMs)
    return () => clearInterval(timer)
  }, [carregarMensagens, useFallback])

  async function enviarMidia(file: File, caption?: string) {
    if (enviando) return
    setEnviando(true)
    try {
      const msg = await chatInterno.enviarMidia(conversaId, file, caption)
      setTexto('')
      setMensagens((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]))
      void refreshInbox(true)
      void refetchPendenciasResumo()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar o arquivo.'))
    } finally {
      setEnviando(false)
    }
  }

  async function enviar() {
    const corpo = texto.trim()
    if (!corpo || enviando) return
    setEnviando(true)
    try {
      const msg = await chatInterno.enviar(conversaId, corpo)
      setTexto('')
      setMensagens((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]))
      void refreshInbox(true)
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
      <div className="flex h-full items-center justify-center p-4">
        <SemPermissao
          title="Sem permissão para esta conversa"
          detail="Você não participa deste chat ou não tem acesso ao canal do setor."
          voltarPara="/chat/interno"
          voltarLabel="Voltar à lista"
        />
      </div>
    )
  }

  const titulo = meta?.titulo ?? 'Conversa'
  const isSetor = meta?.tipo === 'setor'

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden">
      <header className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 md:px-6 lg:px-8">
        <Link
          to="/chat/interno"
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 md:hidden"
          aria-label="Voltar à lista"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </Link>
        <div
          className={`hidden h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white md:flex ${
            isSetor ? 'bg-amber-500' : 'bg-cyan-600'
          }`}
        >
          {isSetor ? 'S' : titulo.slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-bold text-slate-900 dark:text-white">{titulo}</h2>
          <p className="truncate text-sm text-slate-500">
            {isSetor ? 'Canal do setor — comunicados' : 'Conversa direta'}
          </p>
        </div>
      </header>

      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto bg-slate-100/90 px-4 py-5 dark:bg-slate-900/60 md:px-6 lg:px-8"
      >
        <div className="w-full min-w-0 space-y-4">
        {loading ? (
          <p className="text-center text-base text-slate-400 animate-pulse">Carregando mensagens…</p>
        ) : erro ? (
          <p className="text-center text-base text-rose-600">Erro ao carregar mensagens.</p>
        ) : mensagens.length === 0 ? (
          <p className="text-center text-base text-slate-400">
            {isSetor ? 'Nenhum comunicado ainda. Publique o primeiro aviso.' : 'Nenhuma mensagem. Diga olá!'}
          </p>
        ) : (
          mensagens.map((m) => {
            const propria = m.atendente_id === user?.id
            if (isSetor) {
              return (
                <article
                  key={m.id}
                  className="w-full min-w-0 overflow-hidden rounded-2xl border border-amber-200/80 bg-amber-50/95 p-5 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/40"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-200">
                    <span>Comunicado</span>
                    <span className="font-normal normal-case text-slate-500">
                      {m.atendente_nome ?? 'Atendente'}
                    </span>
                  </div>
                  <ChatInternoConteudoMensagem conversaId={conversaId} mensagem={m} />
                  {m.atendente_id === user?.id ? (
                    <MensagemRodapeMeta
                      hora={m.created_at}
                      status={m.status_entrega}
                      direcao="outbound"
                      variant="escuro"
                      className="mt-2"
                    />
                  ) : (
                    <p className="mt-2 text-xs text-slate-500">{formatarHoraMensagem(m.created_at)}</p>
                  )}
                </article>
              )
            }
            return (
              <div key={m.id} className={`flex min-w-0 w-full ${propria ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`min-w-0 max-w-[min(42rem,78%)] overflow-hidden rounded-2xl px-4 py-3 text-base leading-relaxed shadow-sm ${
                    propria
                      ? 'rounded-tr-md bg-cyan-600 text-white'
                      : 'rounded-tl-md bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100'
                  }`}
                >
                  {!propria && (
                    <p className="mb-1.5 text-xs font-semibold opacity-80">{m.atendente_nome ?? 'Atendente'}</p>
                  )}
                  <ChatInternoConteudoMensagem conversaId={conversaId} mensagem={m} textoClaro={propria} />
                  <MensagemRodapeMeta
                    hora={m.created_at}
                    status={propria ? m.status_entrega : null}
                    direcao={propria ? 'outbound' : 'inbound'}
                    variant={propria ? 'claro' : 'escuro'}
                  />
                </div>
              </div>
            )
          })
        )}
        </div>
      </div>

      <ChatInternoComposerBar
        texto={texto}
        onTextoChange={setTexto}
        onEnviar={() => void enviar()}
        onEnviarMidia={(file, caption) => void enviarMidia(file, caption)}
        enviando={enviando}
        placeholder={isSetor ? 'Novo comunicado para o setor…' : 'Escreva uma mensagem…'}
        labelEnviar={isSetor ? 'Publicar' : 'Enviar'}
      />
    </div>
  )
}
