import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, fetchPortalMidiaBlob, portalChats, type PortalChats } from '../../api/client'
import { ChatCanalBadge } from '../../components/chat/ChatCanalBadge'
import { ChatDemandasPanel } from '../../components/chat/ChatDemandasPanel'
import { ChatEncerrarModal } from '../../components/chat/ChatEncerrarModal'
import { ChatFilaAguardandoSheet } from '../../components/chat/ChatFilaAguardandoSheet'
import { ChatFilaSomToggle } from '../../components/chat/ChatFilaSomToggle'
import { ChatMensagemMidia } from '../../components/chat/ChatMensagemMidia'
import { ChatTransferModal } from '../../components/chat/ChatTransferModal'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'
import { useChatHub } from '../../contexts/ChatHubContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'
import { portalDemandasApi, type ChatDemanda } from '../../lib/chatDemandasApi'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { CHAT_HUB_PATHS, chatPortalLink } from '../../lib/chatHubPaths'
import {
  classeCorEstadoChat,
  mensagemTransferenciaSucesso,
  rotuloEstadoChat,
  rotuloResponsavelChat,
} from '../../lib/whatsappChatMeta'
import { mergeTimelineChat, textoMarcoDemanda } from '../../lib/whatsappDemandaUtils'
import { WhatsappDemandaTimelineMarco } from '../whatsapp/WhatsappDemandaTimelineMarco'
import { ACCEPT_ANEXO, type TipoAnexoPicker } from '../whatsapp/WhatsappBarraAnexos'
import { WhatsappComposerBar } from '../whatsapp/WhatsappComposerBar'
import { WhatsappPreviaAnexo } from '../whatsapp/WhatsappPreviaAnexo'

function TextoComLinks({ texto }: { texto: string }) {
  const partes = texto.split(/(https?:\/\/\S+)/g)
  return (
    <>
      {partes.map((parte, i) =>
        /^https?:\/\//.test(parte) ? (
          <a
            key={i}
            href={parte}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all underline opacity-90 hover:opacity-100"
          >
            {parte}
          </a>
        ) : (
          <span key={i}>{parte}</span>
        ),
      )}
    </>
  )
}

function formatarHora(iso?: string | null) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

type PortalConversaProps = {
  /** Conversa aberta pelo hub (sem id na URL) (#654). */
  chatIdProp?: number
}

export function PortalConversa({ chatIdProp }: PortalConversaProps = {}) {
  const { chatId: chatIdParam } = useParams()
  const chatId = chatIdProp ?? Number(chatIdParam)
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const { subscribe, useFallback } = useEventStream()
  const { refreshContagens, filaCount, fecharChat, abrirChat } = useChatHub()
  const [chat, setChat] = useState<PortalChats.Chat | null>(null)
  const [mensagens, setMensagens] = useState<PortalChats.Mensagem[]>([])
  const [demandasTimeline, setDemandasTimeline] = useState<ChatDemanda[]>([])
  const [texto, setTexto] = useState('')
  const [loading, setLoading] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const enviandoRef = useRef(false)
  const [assumindo, setAssumindo] = useState(false)
  const [modalEncerrar, setModalEncerrar] = useState(false)
  const [modalTransferir, setModalTransferir] = useState(false)
  const [transferindo, setTransferindo] = useState(false)
  const [setoresList, setSetoresList] = useState<Array<{ id: number; nome: string }>>([])
  const [filaAguardandoAberta, setFilaAguardandoAberta] = useState(false)
  const [demandasReloadKey, setDemandasReloadKey] = useState(0)
  const [pickerAnexo, setPickerAnexo] = useState<TipoAnexoPicker>('imagem')
  const [arquivoPendente, setArquivoPendente] = useState<File | null>(null)
  const [legendaMidia, setLegendaMidia] = useState('')
  const fimRef = useRef<HTMLDivElement>(null)
  const lastMsgIdRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const carregarDemandasTimeline = useCallback(async () => {
    if (!Number.isFinite(chatId)) return
    try {
      const rows = await portalChats.demandas(chatId)
      setDemandasTimeline(rows)
    } catch {
      setDemandasTimeline([])
    }
  }, [chatId])

  const carregarMensagens = useCallback(
    async (opts?: { sinceId?: number; replace?: boolean }) => {
      if (!Number.isFinite(chatId)) return
      const sinceId = opts?.sinceId
      const rows = await portalChats.mensagens(chatId, sinceId)
      if (opts?.replace || sinceId == null) {
        setMensagens(rows)
        lastMsgIdRef.current = rows.at(-1)?.id ?? 0
      } else if (rows.length > 0) {
        setMensagens((prev) => {
          const ids = new Set(prev.map((m) => m.id))
          const merged = [...prev, ...rows.filter((m) => !ids.has(m.id))]
          lastMsgIdRef.current = merged.at(-1)?.id ?? lastMsgIdRef.current
          return merged
        })
      }
      await portalChats.marcarVisto(chatId).catch(() => undefined)
      void refetchPendenciasResumo()
    },
    [chatId],
  )

  const load = useCallback(async () => {
    if (!Number.isFinite(chatId)) return
    setLoading(true)
    try {
      const c = await portalChats.get(chatId)
      setChat(c)
      await Promise.all([carregarMensagens({ replace: true }), carregarDemandasTimeline()])
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o chat.'))
    } finally {
      setLoading(false)
    }
  }, [carregarDemandasTimeline, carregarMensagens, chatId, toast])

  const pollMensagens = useCallback(async () => {
    if (!Number.isFinite(chatId)) return
    try {
      const sinceId = lastMsgIdRef.current > 0 ? lastMsgIdRef.current : undefined
      await carregarMensagens(sinceId != null ? { sinceId } : { replace: true })
    } catch {
      /* silencioso */
    }
  }, [carregarMensagens, chatId])

  useEffect(() => {
    setChat(null)
    setMensagens([])
    setDemandasTimeline([])
    setTexto('')
    lastMsgIdRef.current = 0
    void load()
  }, [chatId, load])

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensagens, demandasTimeline])

  useEffect(() => {
    const refresh = () => void load()
    const u1 = subscribe('portal.chat.mensagem', (payload) => {
      if (Number(payload?.chat_id) === chatId) {
        void pollMensagens()
        void carregarDemandasTimeline()
      }
    })
    const u2 = subscribe('portal.chat.fila', refresh)
    return () => {
      u1()
      u2()
    }
  }, [subscribe, chatId, load, pollMensagens, carregarDemandasTimeline])

  useEffect(() => {
    const intervalMs = useFallback ? 8_000 : 4_000
    const timer = setInterval(() => void pollMensagens(), intervalMs)
    return () => clearInterval(timer)
  }, [pollMensagens, useFallback])

  useEffect(() => {
    if (!modalTransferir) return
    void portalChats
      .setoresParaTransferencia()
      .then(setSetoresList)
      .catch(() => setSetoresList([]))
  }, [modalTransferir])

  async function enviar() {
    const corpo = texto.trim()
    if (!corpo || !Number.isFinite(chatId) || enviando || enviandoRef.current) return
    enviandoRef.current = true
    setEnviando(true)
    try {
      const msg = await portalChats.enviar(chatId, corpo)
      setMensagens((prev) => {
        if (prev.some((m) => m.id === msg.id)) return prev
        const next = [...prev, msg]
        lastMsgIdRef.current = msg.id
        return next
      })
      setTexto('')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a mensagem.'))
    } finally {
      enviandoRef.current = false
      setEnviando(false)
    }
  }

  function abrirPickerAnexo(tipo: TipoAnexoPicker) {
    setPickerAnexo(tipo)
    window.setTimeout(() => fileInputRef.current?.click(), 0)
  }

  function handleFileSelecionado(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    const responsavel = chat?.estado === 'em_atendimento' && chat.atendente_id === user?.id
    if (!file || !chat || !responsavel) {
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    setArquivoPendente(file)
    setLegendaMidia('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function assumirChat() {
    if (!chat || chat.estado !== 'aguardando_atendente' || assumindo) return
    setAssumindo(true)
    try {
      const atualizado = await portalChats.assumir(chat.id)
      setChat(atualizado)
      void refreshContagens()
      void refetchPendenciasResumo()
      toast.showSuccess('Chat assumido.')
      abrirChat('portal', chat.id)
      navigate(chatPortalLink(), { replace: true })
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 400
          ? (err.body as { detail?: string })?.detail || 'Erro ao assumir.'
          : mensagemFalhaParaToast(err)
      toast.showWarning(msg)
    } finally {
      setAssumindo(false)
    }
  }

  async function confirmarEnvioMidia() {
    const responsavel = chat?.estado === 'em_atendimento' && chat.atendente_id === user?.id
    if (!arquivoPendente || !Number.isFinite(chatId) || !responsavel || enviando || enviandoRef.current) return
    enviandoRef.current = true
    setEnviando(true)
    try {
      const msg = await portalChats.enviarMidia(chatId, arquivoPendente, legendaMidia.trim())
      setMensagens((prev) => {
        if (prev.some((m) => m.id === msg.id)) return prev
        const next = [...prev, msg]
        lastMsgIdRef.current = msg.id
        return next
      })
      setArquivoPendente(null)
      setLegendaMidia('')
      toast.showSuccess('Anexo enviado!')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha no envio do anexo'))
    } finally {
      enviandoRef.current = false
      setEnviando(false)
    }
  }

  async function handleGravacaoConcluida(file: File) {
    if (!Number.isFinite(chatId) || enviando) return
    setEnviando(true)
    try {
      const msg = await portalChats.enviarMidia(chatId, file, '')
      setMensagens((prev) => {
        if (prev.some((m) => m.id === msg.id)) return prev
        const next = [...prev, msg]
        lastMsgIdRef.current = msg.id
        return next
      })
      toast.showSuccess('Áudio enviado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao enviar áudio.'))
    } finally {
      setEnviando(false)
    }
  }

  async function transferirChat(setorId: number, atendenteId: number | null) {
    if (!chat) return
    setTransferindo(true)
    try {
      const atualizado = await portalChats.transferir(chat.id, {
        setor_id: setorId,
        atendente_id: atendenteId,
      })
      setModalTransferir(false)
      setChat(atualizado)
      await Promise.all([carregarMensagens({ replace: true }), carregarDemandasTimeline()])
      void refreshContagens()
      void refetchPendenciasResumo()
      toast.showSuccess(mensagemTransferenciaSucesso(atualizado))
      if (atualizado.atendente_id !== user?.id && atualizado.estado === 'em_atendimento') {
        fecharChat()
        navigate(CHAT_HUB_PATHS.atendendo)
      }
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível transferir o chat.'))
    } finally {
      setTransferindo(false)
    }
  }

  async function handleEncerrado(atualizado: PortalChats.Chat) {
    void refreshContagens()
    void refetchPendenciasResumo()
    toast.showSuccess(
      atualizado.estado === 'aguardando_avaliacao'
        ? 'Atendimento encerrado. Aguardando avaliação do visitante.'
        : 'Atendimento encerrado.',
    )
    fecharChat()
  }

  if (!Number.isFinite(chatId)) {
    return <p className="p-6 text-slate-500">Chat inválido.</p>
  }

  if (loading || !chat) {
    return (
      <div className="flex h-full min-h-0 items-center justify-center text-slate-500">
        Carregando conversa…
      </div>
    )
  }

  const encerrado = chat.estado === 'encerrado' || chat.estado === 'aguardando_avaliacao'
  const isResponsavel = chat.atendente_id === user?.id
  const isAdmin = user?.role === 'admin'
  const podeTransferir = !encerrado && (isResponsavel || isAdmin)
  const podeEnviar = chat.estado === 'em_atendimento' && isResponsavel && !encerrado
  const podeEncerrar = !encerrado && chat.estado === 'em_atendimento' && (isResponsavel || isAdmin)

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-white dark:bg-slate-950">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-950">
        <div className="min-w-0">
          <button
            type="button"
            onClick={fecharChat}
            className="text-xs text-cyan-600 hover:underline md:hidden"
          >
            ← Voltar
          </button>
          <div className="mt-0.5 flex flex-wrap items-center gap-2">
            <h1 className="truncate text-base font-semibold text-slate-900 dark:text-slate-100">
              {chat.visitante_nome}
            </h1>
            <ChatCanalBadge canal="portal" />
          </div>
          <p className="truncate text-xs text-cyan-600 dark:text-cyan-400">{exibirProtocolo(chat.protocolo)}</p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            <span className={classeCorEstadoChat(chat.estado)}>{rotuloEstadoChat(chat.estado)}</span>
            {chat.setor_nome ? ` · ${chat.setor_nome}` : ''}
            {' · '}
            {rotuloResponsavelChat(chat, user?.id)}
            {chat.visitante_email ? ` · ${chat.visitante_email}` : ''}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5 md:hidden">
            <Button
              type="button"
              variant="secondary"
              className="relative h-8 shrink-0 px-2.5 text-xs font-semibold"
              onClick={() => setFilaAguardandoAberta(true)}
              aria-label={filaCount > 0 ? `Aguardando, ${filaCount} na fila` : 'Aguardando'}
            >
              Aguardando
              {filaCount > 0 && (
                <span className="ml-1 inline-flex min-w-[1rem] justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold leading-4 text-white">
                  {filaCount > 99 ? '99+' : filaCount}
                </span>
              )}
            </Button>
            <ChatFilaSomToggle />
          </div>

          {chat.estado === 'aguardando_atendente' && (
            <Button
              type="button"
              variant="primary"
              className="h-8 shrink-0 px-3 text-xs font-semibold"
              loading={assumindo}
              onClick={() => void assumirChat()}
            >
              Atender
            </Button>
          )}

          {!encerrado && (
            <>
              {podeTransferir && (
                <Button
                  type="button"
                  variant="primary"
                  className="hidden h-8 text-xs sm:inline-flex"
                  onClick={() => setModalTransferir(true)}
                >
                  Transferir
                </Button>
              )}
              {podeEncerrar && (
                <Button type="button" variant="danger" className="h-8 px-3 text-xs" onClick={() => setModalEncerrar(true)}>
                  Encerrar
                </Button>
              )}
            </>
          )}
        </div>
      </header>

      {!encerrado && chat.estado === 'em_atendimento' && !isResponsavel && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100">
          {isAdmin ? (
            <>
              Modo acompanhamento (administrador): chat com{' '}
              <strong>{chat.atendente_nome || 'outro atendente'}</strong>. Apenas o responsável pode enviar mensagens
              ao visitante.
            </>
          ) : (
            <>
              Este chat está com <strong>{chat.atendente_nome || 'outro atendente'}</strong>. Você pode acompanhar, mas
              não enviar mensagens ao visitante.
            </>
          )}
        </div>
      )}

      {chat.estado === 'em_atendimento' && (
        <ChatDemandasPanel
          key={`${chat.id}-${demandasReloadKey}`}
          chatId={chat.id}
          api={portalDemandasApi}
          podeRegistrar={isResponsavel || isAdmin}
          onDemandasChange={() => {
            setDemandasReloadKey((k) => k + 1)
            void carregarDemandasTimeline()
            void pollMensagens()
          }}
        />
      )}

      <div
        className="min-h-0 flex-1 overflow-y-auto p-4 space-y-4 bg-[#efeae2] dark:bg-slate-900/60"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(0,0,0,0.03) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      >
        <div className="mx-auto flex min-h-full max-w-2xl flex-col gap-3">
          {mensagens.length === 0 && demandasTimeline.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">Nenhuma mensagem ainda.</p>
          ) : (
            mergeTimelineChat(mensagens, demandasTimeline).map((item) => {
              if (item.kind === 'demanda') {
                return <WhatsappDemandaTimelineMarco key={`dem-${item.demanda.id}`} demanda={item.demanda} />
              }

              const m = item.mensagem
              if (m.evento_sistema === 'demanda_registrada' || m.evento_sistema === 'demanda_escalada') {
                return (
                  <div key={m.id} className="flex w-full justify-center py-2">
                    <div className="max-w-md rounded-xl border border-violet-200 bg-violet-50/95 px-4 py-2 text-center text-xs shadow-sm dark:border-violet-900/50 dark:bg-violet-950/40">
                      <p className="font-bold uppercase tracking-wide text-violet-800 dark:text-violet-200">
                        Demanda registada
                      </p>
                      <p className="mt-0.5 font-medium text-violet-950 dark:text-violet-100">
                        {textoMarcoDemanda(m.corpo)}
                      </p>
                    </div>
                  </div>
                )
              }

              const isInbound = m.direcao === 'inbound'
              const isTransferencia = m.evento_sistema === 'transferencia'

              if (isTransferencia) {
                return (
                  <div key={m.id} className="flex w-full justify-center py-2">
                    <div className="max-w-md rounded-xl border border-amber-200 bg-amber-50/95 px-4 py-2 text-center text-xs shadow-sm dark:border-amber-900/50 dark:bg-amber-950/40">
                      <p className="font-bold uppercase tracking-wide text-amber-800 dark:text-amber-200">
                        ↪ Transferência
                      </p>
                      <p className="mt-0.5 text-amber-950 dark:text-amber-100">{m.corpo}</p>
                    </div>
                  </div>
                )
              }

              return (
                <div key={m.id} className={`flex w-full ${isInbound ? 'justify-start' : 'justify-end'}`}>
                  <div className={`max-w-[85%] space-y-1 ${isInbound ? 'items-start' : 'items-end'}`}>
                    <div
                      className={`rounded-2xl px-3 py-2 text-sm shadow-sm ${
                        isInbound
                          ? 'bg-white text-slate-800 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700'
                          : 'bg-cyan-600 text-white'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">
                        {(m.tipo_midia && m.tipo_midia !== 'texto') || m.midia_disponivel ? (
                          <ChatMensagemMidia
                            mensagem={m}
                            fetchMidia={() => fetchPortalMidiaBlob(chatId, m.id)}
                          />
                        ) : (
                          <TextoComLinks texto={m.corpo || ''} />
                        )}
                      </p>
                    </div>
                    <p className={`px-1 text-[10px] ${isInbound ? 'text-slate-400' : 'text-slate-500'}`}>
                      {m.atendente_nome || (isInbound ? chat.visitante_nome : 'Atendente')}
                      {m.created_at ? ` · ${formatarHora(m.created_at)}` : ''}
                    </p>
                  </div>
                </div>
              )
            })
          )}
          <div ref={fimRef} />
        </div>
      </div>

      {encerrado ? (
        <p className="shrink-0 border-t border-slate-200 bg-slate-50 px-4 py-3 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          {chat.estado === 'aguardando_avaliacao'
            ? 'Aguardando avaliação do visitante no portal.'
            : 'Este atendimento foi encerrado.'}
        </p>
      ) : chat.estado === 'aguardando_atendente' ? (
        <div className="flex shrink-0 flex-col items-center gap-2 border-t border-slate-200 bg-amber-50 px-4 py-3 dark:border-slate-800 dark:bg-amber-950/30">
          <p className="text-center text-sm text-amber-800 dark:text-amber-200">
            Este chat está na fila. Assuma para responder ao visitante.
          </p>
          <Button
            type="button"
            variant="primary"
            className="h-9 px-4 text-sm font-semibold"
            loading={assumindo}
            onClick={() => void assumirChat()}
          >
            Atender
          </Button>
        </div>
      ) : (
        <div className="shrink-0 border-t border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
          {arquivoPendente ? (
            <div
              className="mb-2 rounded-xl border border-cyan-200 bg-cyan-50/80 p-3 dark:border-cyan-900/40 dark:bg-cyan-950/20"
              tabIndex={arquivoPendente.type.startsWith('audio/') ? 0 : undefined}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !enviando && podeEnviar) {
                  e.preventDefault()
                  void confirmarEnvioMidia()
                }
              }}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-cyan-800 dark:text-cyan-300">Anexo selecionado</p>
                  <p className="truncate text-sm text-slate-700 dark:text-slate-200">{arquivoPendente.name}</p>
                  <WhatsappPreviaAnexo file={arquivoPendente} />
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setArquivoPendente(null)
                    setLegendaMidia('')
                  }}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  aria-label="Remover anexo"
                >
                  &times;
                </button>
              </div>
              {!arquivoPendente.type.startsWith('audio/') && (
                <input
                  type="text"
                  value={legendaMidia}
                  onChange={(e) => setLegendaMidia(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      if (!enviando && podeEnviar) void confirmarEnvioMidia()
                    }
                  }}
                  placeholder="Legenda opcional"
                  className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                />
              )}
              <div className="mt-2 flex justify-end gap-2">
                <Button variant="ghost" className="h-8 text-xs" onClick={() => setArquivoPendente(null)}>
                  Cancelar
                </Button>
                <Button className="h-8 text-xs" loading={enviando} onClick={() => void confirmarEnvioMidia()}>
                  Enviar anexo
                </Button>
              </div>
            </div>
          ) : (
            <WhatsappComposerBar
              texto={texto}
              onTextoChange={setTexto}
              onEnviar={() => void enviar()}
              onEscolherAnexo={abrirPickerAnexo}
              onAudioGravado={(file) => void handleGravacaoConcluida(file)}
              onInserirEmoji={(emoji) => setTexto((t) => t + emoji)}
              onEnviarFigurinha={() => undefined}
              enviando={enviando}
              encerrado={false}
              podeEnviar={podeEnviar}
              modoInterno={false}
              podeDigitar={podeEnviar}
            />
          )}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept={ACCEPT_ANEXO[pickerAnexo]}
            onChange={handleFileSelecionado}
          />
        </div>
      )}

      <ChatTransferModal
        open={modalTransferir}
        chat={chat}
        usuarioId={user?.id}
        setoresList={setoresList}
        loading={transferindo}
        onClose={() => setModalTransferir(false)}
        onTransferir={transferirChat}
      />

      <ChatEncerrarModal
        open={modalEncerrar}
        chatId={chat.id}
        chatEstado={chat.estado}
        msgs={mensagens}
        api={portalDemandasApi}
        mensagemIntroPadrao="Revise as demandas desta sessão antes de finalizar o atendimento do portal."
        onClose={() => setModalEncerrar(false)}
        onEncerrado={(atualizado) => void handleEncerrado(atualizado)}
        onDemandasChange={() => {
          setDemandasReloadKey((k) => k + 1)
          void carregarDemandasTimeline()
        }}
      />

      <ChatFilaAguardandoSheet open={filaAguardandoAberta} onClose={() => setFilaAguardandoAberta(false)} />
    </div>
  )
}
