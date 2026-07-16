import { useCallback, useEffect, useRef, useState, type MouseEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, atendentes, chatInterno, type ChatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ChatInternoComposerBar } from '../../components/chat-interno/ChatInternoComposerBar'
import { ChatInternoGrupoMembrosModal } from '../../components/chat-interno/ChatInternoGrupoMembrosModal'
import { ChatInternoConteudoMensagem } from '../../components/chat-interno/ChatInternoConteudoMensagem'
import { ChatInternoMensagemAcoes } from '../../components/chat-interno/ChatInternoMensagemAcoes'
import { ChatInternoReacoesBar } from '../../components/chat-interno/ChatInternoReacoesBar'
import { MensagemRodapeMeta } from '../../components/chat/MensagemRodapeMeta'
import { useChatInterno } from '../../contexts/ChatInternoContext'
import { useToast } from '../../components/ui/Toast'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useAuth } from '../../contexts/AuthContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'
import {
  clearChatInternoScroll,
  isNearBottom,
  preserveScrollOnContentChange,
  restoreChatInternoScroll,
  saveChatInternoScroll,
  scrollChatToBottom,
} from '../../lib/chatInternoScrollMemory'
import { mergeMensagensChatInterno, prependMensagensChatInterno } from '../../lib/chatInternoMensagensMerge'
import {
  corAvatarRemetenteChat,
  corNomeRemetenteChat,
  inicialNomeRemetente,
} from '../../lib/chatInternoRemetenteCor'
import { montarMencoesDoCorpo, type MencaoCandidato } from '../../lib/chatInternoMencoes'
import { SemPermissao } from '../SemPermissao'

const SCROLL_TOPO_CARREGAR_PX = 80

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
  const [msgRespondida, setMsgRespondida] = useState<ChatInterno.Mensagem | null>(null)
  const [focoComposerEm, setFocoComposerEm] = useState(0)
  const [forbidden, setForbidden] = useState(false)
  const [erro, setErro] = useState(false)
  const [temMaisAntigas, setTemMaisAntigas] = useState(false)
  const [carregandoAntigas, setCarregandoAntigas] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const stickToBottomRef = useRef(true)
  const initialScrollRestoredRef = useRef(false)
  const saveScrollRafRef = useRef<number | null>(null)
  const carregandoAntigasRef = useRef(false)
  const temMaisAntigasRef = useRef(false)
  const mensagensRef = useRef<ChatInterno.Mensagem[]>([])

  useEffect(() => {
    temMaisAntigasRef.current = temMaisAntigas
  }, [temMaisAntigas])

  useEffect(() => {
    mensagensRef.current = mensagens
  }, [mensagens])

  const marcarVistoSeNoFim = useCallback(async () => {
    const el = scrollRef.current
    if (!el || !isNearBottom(el)) return
    try {
      await chatInterno.marcarVisto(conversaId)
      void refetchPendenciasResumo()
      void refreshInbox(true)
    } catch {
      // silencioso no polling
    }
  }, [conversaId, refreshInbox])

  const carregarMaisAntigas = useCallback(async () => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) return
    if (!temMaisAntigasRef.current || carregandoAntigasRef.current) return

    const oldestId = mensagensRef.current[0]?.id
    if (oldestId == null) return

    const el = scrollRef.current
    const prevTop = el?.scrollTop ?? 0
    const prevHeight = el?.scrollHeight ?? 0

    carregandoAntigasRef.current = true
    setCarregandoAntigas(true)
    try {
      const pagina = await chatInterno.mensagens(conversaId, { antesDeId: oldestId })
      setMensagens((prev) => prependMensagensChatInterno(prev, pagina.items))
      setTemMaisAntigas(pagina.tem_mais_antigas)
      requestAnimationFrame(() => {
        const container = scrollRef.current
        if (container && el) {
          preserveScrollOnContentChange(container, prevTop, prevHeight)
        }
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
      }
    } finally {
      carregandoAntigasRef.current = false
      setCarregandoAntigas(false)
    }
  }, [conversaId])

  const sincronizarRecentes = useCallback(async () => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) return
    const el = scrollRef.current
    const stick = stickToBottomRef.current
    const prevTop = el?.scrollTop ?? 0
    const prevHeight = el?.scrollHeight ?? 0

    try {
      const pagina = await chatInterno.mensagens(conversaId)
      setMensagens((prev) => {
        const merged = mergeMensagensChatInterno(prev, pagina.items)
        setTemMaisAntigas(merged.length < pagina.total)
        return merged
      })

      requestAnimationFrame(() => {
        const container = scrollRef.current
        if (!container) return
        if (stick) {
          scrollChatToBottom(container)
        } else if (el) {
          preserveScrollOnContentChange(container, prevTop, prevHeight)
        }
      })

      await marcarVistoSeNoFim()
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
      }
    }
  }, [conversaId, marcarVistoSeNoFim])

  const carregar = useCallback(async () => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) return
    setErro(false)
    setForbidden(false)
    try {
      const pagina = await chatInterno.mensagens(conversaId)
      setMensagens(pagina.items)
      setTemMaisAntigas(pagina.tem_mais_antigas)
      await marcarVistoSeNoFim()
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
  }, [conversaId, toast, marcarVistoSeNoFim])

  useEffect(() => {
    if (!Number.isFinite(conversaId) || conversaId <= 0) {
      navigate('/chat/interno', { replace: true })
      return
    }
    initialScrollRestoredRef.current = false
    stickToBottomRef.current = true
    setTemMaisAntigas(false)
    setLoading(true)
    void carregar()
  }, [conversaId, carregar, navigate])

  useEffect(() => {
    if (loading || mensagens.length === 0 || initialScrollRestoredRef.current) return
    initialScrollRestoredRef.current = true
    requestAnimationFrame(() => {
      const el = scrollRef.current
      if (!el) return
      stickToBottomRef.current = restoreChatInternoScroll(conversaId, el)
      if (stickToBottomRef.current) {
        void marcarVistoSeNoFim()
      }
    })
  }, [loading, mensagens.length, conversaId, marcarVistoSeNoFim])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    const onScroll = () => {
      stickToBottomRef.current = isNearBottom(el)
      if (
        el.scrollTop < SCROLL_TOPO_CARREGAR_PX &&
        temMaisAntigasRef.current &&
        !carregandoAntigasRef.current
      ) {
        void carregarMaisAntigas()
      }
      if (saveScrollRafRef.current != null) cancelAnimationFrame(saveScrollRafRef.current)
      saveScrollRafRef.current = requestAnimationFrame(() => {
        saveChatInternoScroll(conversaId, el)
      })
    }

    el.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      el.removeEventListener('scroll', onScroll)
      if (saveScrollRafRef.current != null) cancelAnimationFrame(saveScrollRafRef.current)
      saveChatInternoScroll(conversaId, el)
    }
  }, [conversaId, loading, carregarMaisAntigas])

  useEffect(() => {
    if (loading || !initialScrollRestoredRef.current || !stickToBottomRef.current) return
    requestAnimationFrame(() => {
      const el = scrollRef.current
      if (el) scrollChatToBottom(el)
    })
  }, [mensagens, loading])

  useEffect(() => {
    const unsubMsg = subscribe('chat.interno.mensagem', (payload) => {
      const id = Number(payload.conversa_id)
      void refreshInbox(true)
      if (id !== conversaId) return
      void sincronizarRecentes()
    })
    const unsubLido = subscribe('chat.interno.lido', (payload) => {
      if (Number(payload.conversa_id) !== conversaId) return
      void sincronizarRecentes()
    })
    const unsubAtualizada = subscribe('chat.interno.mensagem.atualizada', (payload) => {
      if (Number(payload.conversa_id) !== conversaId) return
      void sincronizarRecentes()
    })
    return () => {
      unsubMsg()
      unsubLido()
      unsubAtualizada()
    }
  }, [subscribe, conversaId, sincronizarRecentes, refreshInbox])

  useEffect(() => {
    const intervalMs = useFallback ? 10_000 : 6_000
    const timer = setInterval(() => void sincronizarRecentes(), intervalMs)
    return () => clearInterval(timer)
  }, [sincronizarRecentes, useFallback])

  const atualizarMensagemNoEstado = useCallback((msg: ChatInterno.Mensagem) => {
    setMensagens((prev) => prev.map((m) => (m.id === msg.id ? msg : m)))
  }, [])

  const [confirmarLimpar, setConfirmarLimpar] = useState(false)
  const [limpando, setLimpando] = useState(false)
  const [grupoDetalhe, setGrupoDetalhe] = useState<ChatInterno.Conversa | null>(null)
  const [modalMembros, setModalMembros] = useState(false)
  const [mencionaveis, setMencionaveis] = useState<MencaoCandidato[]>([])

  useEffect(() => {
    if (meta?.tipo !== 'grupo') {
      setGrupoDetalhe(null)
      return
    }
    void chatInterno
      .obterConversa(conversaId)
      .then(setGrupoDetalhe)
      .catch(() => setGrupoDetalhe(null))
  }, [conversaId, meta?.tipo])

  useEffect(() => {
    if (meta?.tipo === 'grupo') {
      setMencionaveis(
        (grupoDetalhe?.participantes ?? []).map((p) => ({
          atendente_id: p.atendente_id,
          nome: p.nome,
        })),
      )
      return
    }
    if (meta?.tipo === 'setor' && meta.setor_id) {
      let cancelled = false
      void atendentes
        .listPorSetor(meta.setor_id)
        .then((lista) => {
          if (cancelled) return
          setMencionaveis(
            lista.map((a) => ({
              atendente_id: a.id,
              nome: a.nome,
            })),
          )
        })
        .catch(() => {
          if (!cancelled) setMencionaveis([])
        })
      return () => {
        cancelled = true
      }
    }
    setMencionaveis([])
  }, [meta?.tipo, meta?.setor_id, grupoDetalhe?.participantes])

  async function editarMensagem(mensagemId: number, corpo: string) {
    try {
      const msg = await chatInterno.editarMensagem(conversaId, mensagemId, corpo)
      atualizarMensagemNoEstado(msg)
      void refreshInbox(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível editar a mensagem.'))
      throw err
    }
  }

  async function apagarMensagem(mensagemId: number, escopo: 'todos' | 'para_mim') {
    try {
      const msg = await chatInterno.apagarMensagem(conversaId, mensagemId, escopo)
      if (escopo === 'para_mim' || !msg) {
        setMensagens((prev) => prev.filter((m) => m.id !== mensagemId))
      } else {
        atualizarMensagemNoEstado(msg)
      }
      void refreshInbox(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível apagar a mensagem.'))
      throw err
    }
  }

  async function limparConversa() {
    try {
      await chatInterno.limparConversa(conversaId)
      clearChatInternoScroll(conversaId)
      setMensagens([])
      setTemMaisAntigas(false)
      void refreshInbox(true)
      navigate('/chat/interno', { replace: true })
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível limpar a conversa.'))
    }
  }

  async function reagirMensagem(mensagemId: number, emoji: string) {
    try {
      const msg = await chatInterno.definirReacao(conversaId, mensagemId, emoji)
      atualizarMensagemNoEstado(msg)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível reagir à mensagem.'))
    }
  }

  function iniciarResposta(m: ChatInterno.Mensagem) {
    if (m.apagada) return
    setMsgRespondida(m)
    setFocoComposerEm((n) => n + 1)
  }

  function duploCliqueResponder(e: MouseEvent, m: ChatInterno.Mensagem) {
    const t = e.target as HTMLElement
    if (t.closest('button, a, input, textarea, [role="dialog"]')) return
    iniciarResposta(m)
  }

  async function enviarMidia(file: File, caption?: string) {
    if (enviando) return
    setEnviando(true)
    try {
      const msg = await chatInterno.enviarMidia(conversaId, file, caption, msgRespondida?.id ?? null)
      setTexto('')
      setMsgRespondida(null)
      setMensagens((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]))
      stickToBottomRef.current = true
      requestAnimationFrame(() => {
        const el = scrollRef.current
        if (el) scrollChatToBottom(el)
      })
      void refreshInbox(true)
      void refetchPendenciasResumo()
      await chatInterno.marcarVisto(conversaId)
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
      const mencoes = montarMencoesDoCorpo(corpo, mencionaveis)
      const msg = await chatInterno.enviar(
        conversaId,
        corpo,
        msgRespondida?.id ?? null,
        mencoes.length > 0 ? mencoes : null,
      )
      setTexto('')
      setMsgRespondida(null)
      setMensagens((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]))
      stickToBottomRef.current = true
      requestAnimationFrame(() => {
        const el = scrollRef.current
        if (el) scrollChatToBottom(el)
      })
      void refreshInbox(true)
      void refetchPendenciasResumo()
      await chatInterno.marcarVisto(conversaId)
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
  const isGrupo = meta?.tipo === 'grupo'
  const subtitulo = isSetor
    ? 'Canal do setor — comunicados'
    : isGrupo
      ? 'Grupo da equipe'
      : 'Conversa direta'

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
            isSetor ? 'bg-amber-500' : isGrupo ? 'bg-violet-600' : 'bg-cyan-600'
          }`}
        >
          {isSetor ? 'S' : isGrupo ? 'G' : titulo.slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-bold text-slate-900 dark:text-white">{titulo}</h2>
          <p className="truncate text-sm text-slate-500">{subtitulo}</p>
        </div>
        {isGrupo && grupoDetalhe?.sou_admin_grupo && (
          <button
            type="button"
            onClick={() => setModalMembros(true)}
            className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium text-violet-700 ring-1 ring-violet-200 hover:bg-violet-50 dark:text-violet-300 dark:ring-violet-800 dark:hover:bg-violet-950/40"
          >
            Membros
          </button>
        )}
        <button
          type="button"
          onClick={() => setConfirmarLimpar(true)}
          className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100 dark:text-slate-300 dark:ring-slate-600 dark:hover:bg-slate-800"
          title="Limpar conversa só para você"
        >
          Limpar conversa
        </button>
      </header>

      <ConfirmDialog
        open={confirmarLimpar}
        title="Limpar conversa?"
        message="O histórico será apagado apenas para você. A outra pessoa continua vendo as mensagens."
        confirmLabel="Limpar para mim"
        variant="danger"
        loading={limpando}
        onCancel={() => setConfirmarLimpar(false)}
        onConfirm={() => {
          setLimpando(true)
          void limparConversa().finally(() => {
            setLimpando(false)
            setConfirmarLimpar(false)
          })
        }}
      />

      {grupoDetalhe && (
        <ChatInternoGrupoMembrosModal
          open={modalMembros}
          conversaId={conversaId}
          participantes={grupoDetalhe.participantes ?? []}
          onClose={() => setModalMembros(false)}
          onAtualizado={(conv: ChatInterno.Conversa) => {
            setGrupoDetalhe(conv)
            void refreshInbox(true)
          }}
        />
      )}

      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto bg-slate-100/90 px-4 py-5 dark:bg-slate-900/60 md:px-6 lg:px-8"
      >
        <div className="w-full min-w-0 space-y-1">
        {carregandoAntigas && (
          <p className="py-2 text-center text-sm text-slate-400">Carregando mensagens anteriores…</p>
        )}
        {loading ? (
          <p className="text-center text-base text-slate-400 animate-pulse">Carregando mensagens…</p>
        ) : erro ? (
          <p className="text-center text-base text-rose-600">Erro ao carregar mensagens.</p>
        ) : mensagens.length === 0 ? (
          <p className="text-center text-base text-slate-400">
            {isSetor ? 'Nenhum comunicado ainda. Publique o primeiro aviso.' : 'Nenhuma mensagem. Diga olá!'}
          </p>
        ) : (
          mensagens.map((m, idx) => {
            const propria = m.atendente_id === user?.id
            const isTexto = !m.tipo_midia || m.tipo_midia === 'texto'
            const textoCompacto = isTexto && !m.apagada
            const prev = idx > 0 ? mensagens[idx - 1] : null
            const mesmoRemetenteQueAnterior = Boolean(prev && prev.atendente_id === m.atendente_id)
            const mostrarNomeRemetente = !propria && (isGrupo || isSetor) && !mesmoRemetenteQueAnterior
            const mostrarAvatarGrupo = isGrupo && !propria
            if (isSetor) {
              return (
                <div key={m.id} className="group relative w-full min-w-0" data-chat-msg-id={m.id}>
                <ChatInternoMensagemAcoes
                  mensagem={m}
                  onEditar={(corpo) => editarMensagem(m.id, corpo)}
                  onApagar={(escopo) => apagarMensagem(m.id, escopo)}
                  onResponder={() => iniciarResposta(m)}
                  alinhamento="start"
                />
                <article
                  onDoubleClick={(e) => duploCliqueResponder(e, m)}
                  className="w-full min-w-0 overflow-hidden rounded-2xl border border-amber-200/80 bg-amber-50/95 p-5 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/40"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-200">
                    <span>Comunicado</span>
                    <span className="font-normal normal-case text-slate-500">
                      {m.atendente_nome ?? 'Atendente'}
                    </span>
                    {m.editada && (
                      <span className="font-normal normal-case text-slate-400">· editada</span>
                    )}
                  </div>
                  {m.reply_to_message_id && (
                    <button
                      type="button"
                      onClick={() => {
                        const el = document.querySelector(`[data-chat-msg-id="${m.reply_to_message_id}"]`)
                        el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                      }}
                      className="mb-2 w-full rounded-md border-l-2 border-amber-500 bg-amber-100/80 px-2 py-1 text-left text-[11px] text-amber-950 dark:bg-amber-950/50 dark:text-amber-100"
                    >
                      <p className="font-semibold truncate">{m.reply_autor_nome || 'Mensagem'}</p>
                      <p className="truncate opacity-90">{m.reply_preview || '…'}</p>
                    </button>
                  )}
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
                  {!m.apagada && (
                    <ChatInternoReacoesBar
                      reacoes={m.reacoes ?? []}
                      onReagir={(emoji) => void reagirMensagem(m.id, emoji)}
                      alinhamento="start"
                    />
                  )}
                </div>
              )
            }
            return (
              <div
                key={m.id}
                data-chat-msg-id={m.id}
                onDoubleClick={(e) => duploCliqueResponder(e, m)}
                className={`group flex w-full cursor-default gap-1.5 ${
                  propria ? 'justify-end' : 'justify-start'
                } ${mesmoRemetenteQueAnterior && !propria ? 'mt-0.5' : isGrupo && !propria && !mesmoRemetenteQueAnterior ? 'mt-2' : ''}`}
              >
                {mostrarAvatarGrupo ? (
                  mesmoRemetenteQueAnterior ? (
                    <span className="w-7 shrink-0" aria-hidden />
                  ) : (
                    <span
                      className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white ${corAvatarRemetenteChat(m.atendente_id ?? 0)}`}
                      title={m.atendente_nome ?? 'Atendente'}
                      aria-hidden
                    >
                      {inicialNomeRemetente(m.atendente_nome)}
                    </span>
                  )
                ) : null}
                <div
                  className={`flex max-w-[85%] flex-col sm:max-w-[min(65%,28rem)] ${
                    propria ? 'items-end' : 'items-start'
                  }`}
                >
                  <div className="relative w-fit max-w-full">
                    <ChatInternoMensagemAcoes
                      mensagem={m}
                      onEditar={(corpo) => editarMensagem(m.id, corpo)}
                      onApagar={(escopo) => apagarMensagem(m.id, escopo)}
                      onResponder={() => iniciarResposta(m)}
                      alinhamento={propria ? 'end' : 'start'}
                    />
                    <div
                      className={`relative w-fit max-w-full rounded-lg px-[9px] py-[6px] text-sm shadow-sm ring-1 ring-inset ${
                        propria
                          ? 'rounded-tr-none bg-cyan-600 text-white ring-cyan-500/30'
                          : 'rounded-tl-none bg-white text-slate-900 ring-slate-200/80 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700'
                      }`}
                    >
                    {mostrarNomeRemetente && (
                      <p
                        className={`mb-0.5 text-[11px] font-semibold leading-none ${
                          isGrupo
                            ? corNomeRemetenteChat(m.atendente_id ?? 0)
                            : 'text-cyan-700 dark:text-cyan-300'
                        }`}
                      >
                        {m.atendente_nome ?? 'Atendente'}
                      </p>
                    )}
                    {m.reply_to_message_id && (
                      <button
                        type="button"
                        onClick={() => {
                          const el = document.querySelector(`[data-chat-msg-id="${m.reply_to_message_id}"]`)
                          el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        }}
                        className={`mb-1 w-full rounded-md border-l-2 px-2 py-1 text-left text-[11px] ${
                          propria
                            ? 'border-white/50 bg-white/15 text-white/90'
                            : 'border-cyan-500 bg-slate-100 text-slate-600 dark:bg-slate-900/60 dark:text-slate-300'
                        }`}
                      >
                        <p className="font-semibold truncate">{m.reply_autor_nome || 'Mensagem'}</p>
                        <p className="truncate opacity-90">{m.reply_preview || '…'}</p>
                      </button>
                    )}
                    <ChatInternoConteudoMensagem
                      conversaId={conversaId}
                      mensagem={m}
                      textoClaro={propria}
                      somenteTextoCompacto={textoCompacto}
                      rodape={
                        textoCompacto ? (
                          <MensagemRodapeMeta
                            hora={m.created_at}
                            status={propria ? m.status_entrega : null}
                            direcao={propria ? 'outbound' : 'inbound'}
                            variant={propria ? 'claro' : 'escuro'}
                            editada={m.editada}
                            className="!mt-0"
                          />
                        ) : undefined
                      }
                    />
                    {!textoCompacto && (
                      <MensagemRodapeMeta
                        hora={m.created_at}
                        status={propria ? m.status_entrega : null}
                        direcao={propria ? 'outbound' : 'inbound'}
                        variant={propria ? 'claro' : 'escuro'}
                        editada={m.editada}
                      />
                    )}
                  </div>
                  {!m.apagada && (
                    <ChatInternoReacoesBar
                      reacoes={m.reacoes ?? []}
                      onReagir={(emoji) => void reagirMensagem(m.id, emoji)}
                      alinhamento={propria ? 'end' : 'start'}
                    />
                  )}
                  </div>
                </div>
              </div>
            )
          })
        )}
        </div>
      </div>

      {msgRespondida && (
        <div className="flex items-start justify-between gap-3 border-t border-slate-200 bg-slate-50 px-4 py-2 dark:border-slate-800 dark:bg-slate-900/80">
          <div className="min-w-0 border-l-2 border-cyan-500 pl-2">
            <p className="text-xs font-semibold text-cyan-700 dark:text-cyan-300">
              {msgRespondida.atendente_id === user?.id ? 'Você' : msgRespondida.atendente_nome || 'Atendente'}
            </p>
            <p className="truncate text-xs text-slate-600 dark:text-slate-300">
              {msgRespondida.tipo_midia && msgRespondida.tipo_midia !== 'texto'
                ? `[${msgRespondida.tipo_midia}] ${msgRespondida.corpo}`
                : msgRespondida.corpo}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setMsgRespondida(null)}
            className="shrink-0 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            aria-label="Cancelar resposta"
          >
            ×
          </button>
        </div>
      )}

      <ChatInternoComposerBar
        texto={texto}
        onTextoChange={setTexto}
        onEnviar={() => void enviar()}
        onEnviarMidia={(file, caption) => void enviarMidia(file, caption)}
        enviando={enviando}
        placeholder={
          isSetor
            ? 'Novo comunicado… Use @ para mencionar'
            : isGrupo
              ? 'Escreva uma mensagem… Use @ para mencionar'
              : 'Escreva uma mensagem…'
        }
        labelEnviar={isSetor ? 'Publicar' : 'Enviar'}
        focoPedidoEm={focoComposerEm}
        mencionaveis={mencionaveis}
        meuAtendenteId={user?.id}
      />
    </div>
  )
}
