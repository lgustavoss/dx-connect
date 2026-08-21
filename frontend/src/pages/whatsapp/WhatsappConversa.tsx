import { useCallback, useEffect, useMemo, useState, useRef, type DragEvent, type MouseEvent } from 'react'

import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import {
  ApiError,
  atendentes,
  tickets,
  whatsappChats,
  fetchWhatsAppMidiaBlob,
  type Setores,
  type Atendentes,
  type Tickets,
  type WhatsappChats,
} from '../../api/client'

import { resolveWhatsappMidiaObjectUrl, revokeWhatsappMidiaForChat } from '../../lib/whatsappMidiaCache'
import {
  chatEncerramentoPorInatividade,
} from '../../lib/whatsappDemandaUtils'
import { mergeWhatsappChat, patchWhatsappChatLista, replaceWhatsappChatLista } from '../../lib/whatsappChatMerge'
import { whatsappMensagensUnicas } from '../../lib/whatsappMensagens'
import {
  isNearBottom,
  preserveScrollOnContentChange,
  restoreWhatsappScroll,
  saveWhatsappScroll,
  scrollWhatsappToBottom,
} from '../../lib/whatsappScrollMemory'
import { MensagemRodapeMeta } from '../../components/chat/MensagemRodapeMeta'
import { AssumirWhatsappSetorModal } from '../../components/chat/AssumirWhatsappSetorModal'
import { WhatsappAvatar } from '../../components/chat/WhatsappAvatar'
import { ImageLightboxViewer } from '../../components/chat/ImageLightboxViewer'
import { WhatsappMensagemAcoes } from '../../components/chat/WhatsappMensagemAcoes'
import { WhatsappReacoesBar } from '../../components/chat/WhatsappReacoesBar'
import { precisaEscolherSetorAoAssumir } from '../../lib/assumirWhatsappSetor'
import { formatWaIdExibicao } from '../../utils/masks'

import { Card } from '../../components/ui/Card'
import { ChatBottomSheet } from '../../components/ui/ChatBottomSheet'
import { TEXTAREA_FIELD_CLASS } from '../../components/ui/Input'

import { Button } from '../../components/ui/Button'

import { Select } from '../../components/ui/Select'
import { SelectComPesquisa } from '../../components/ui/SelectComPesquisa'

import { useToast } from '../../components/ui/Toast'

import { mensagemFalhaParaToast } from '../../api/errorMessage'

import { exibirProtocolo } from '../../lib/exibirProtocolo'

import { useAuth } from '../../contexts/AuthContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'
import { CustomAudioPlayer } from '../../components/CustomAudioPlayer'
import {
  classeCorEstadoChat,
  mensagemTransferenciaSucesso,
  rotuloEstadoChat,
  rotuloResponsavelChat,
} from '../../lib/whatsappChatMeta'
import { WhatsappTicketsModal } from './WhatsappTicketsModal'
import { WhatsappVincFuncionarioModal } from './WhatsappVincFuncionarioModal'
import { WhatsappDemandasPanel } from './WhatsappDemandasPanel'
import { WhatsappEncerrarModal } from './WhatsappEncerrarModal'
import { WhatsappDemandaTimelineMarco } from './WhatsappDemandaTimelineMarco'
import { ACCEPT_ANEXO, type TipoAnexoPicker } from './WhatsappBarraAnexos'
import { WhatsappComposerBar } from './WhatsappComposerBar'
import { WhatsappPreviaAnexo } from './WhatsappPreviaAnexo'
import { useWhatsappVoltarLista } from '../../hooks/useWhatsappVoltarLista'
import {
  marcarWhatsappChatAtivo,
  whatsappConversaLink,
  resolveWhatsappListFallback,
  WHATSAPP_LIST_PATHS,
} from '../../lib/whatsappListReturn'
import { useChatHub } from '../../contexts/ChatHubContext'
import { ChatFilaAguardandoSheet } from '../../components/chat/ChatFilaAguardandoSheet'
import { chatWhatsappLink } from '../../lib/chatHubPaths'
import { marcarTicketAtivo, TICKETS_PATH } from '../../lib/ticketAtivo'
import { WhatsappInatividadeControle } from './WhatsappInatividadeControle'
import { mergeTimelineChat, textoMarcoDemanda } from '../../lib/whatsappDemandaUtils'
import { rotuloDownloadArquivo, visualTipoArquivo } from '../../lib/fileTypeIcon'
import { CONTATO_CLIENTE } from '../../constants/contatoClienteLabels'

const ROTULO_SEM_LEGENDA =
  /^(?:\[\s*[^\]]+\s*\]:\s*)?\[(Imagem|Áudio|Vídeo|Documento|Figurinha|Contacto|Localização)(\s+enviad[oa])?\]$/i

/** Legenda real sob mídia; ignora placeholders tipo «[Imagem enviada]». */
function legendaMidiaVisivel(corpo: string | null | undefined): string | null {
  const t = (corpo || '').trim()
  if (!t || ROTULO_SEM_LEGENDA.test(t)) return null
  return t
}

function normalizarReacoesMensagem(
  msg: WhatsappChats.Mensagem,
  viewerId?: number | null,
): WhatsappChats.Mensagem {
  if (!msg.reacoes?.length || viewerId == null) return msg
  return {
    ...msg,
    reacoes: msg.reacoes.map((r) => ({
      ...r,
      reagiu_eu: Boolean(r.reagiu_eu || r.atendente_ids?.includes(viewerId)),
    })),
  }
}


// --- Subcomponente de Renderização de Mídia ---

function TextoComLinks({ texto }: { texto: string }) {
  const partes = texto.split(/(https?:\/\/\S+)/g)
  return (
    <p className="whitespace-pre-wrap">
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
    </p>
  )
}

function ConteudoMensagemWhatsApp({
  chatId,
  m,
  onImageClick,
  onVideoClick,
}: {
  chatId: number
  m: WhatsappChats.Mensagem
  onImageClick: (msgId: number) => void
  onVideoClick: (msgId: number) => void
}) {

  const tipo = (m.tipo_midia || 'texto').toLowerCase()

  const [url, setUrl] = useState<string | null>(null)

  const [loading, setLoading] = useState(false)

  const [err, setErr] = useState(false)



  useEffect(() => {

    if (m.apagada || !m.midia_disponivel || tipo === 'texto') {

      setUrl(null)

      return

    }

    let cancelled = false

    setLoading(true)

    setErr(false)

    void resolveWhatsappMidiaObjectUrl(chatId, m.id, () => fetchWhatsAppMidiaBlob(chatId, m.id))

      .then((u) => {

        if (cancelled) return

        setUrl(u)

      })

      .catch(() => { if (!cancelled) setErr(true) })

      .finally(() => { if (!cancelled) setLoading(false) })

    return () => {

      cancelled = true

    }

  }, [chatId, m.id, m.midia_disponivel, m.apagada, tipo])



  if (m.apagada) {
    return <p className="text-sm italic opacity-70">Mensagem apagada</p>
  }

  const legenda = legendaMidiaVisivel(m.corpo)

  if (tipo === 'texto' || !m.tipo_midia) return <TextoComLinks texto={m.corpo} />

  if (!m.midia_disponivel) {
    return (
      <p className="text-xs italic opacity-70" title="O ficheiro não foi obtido da Evolution API">
        {legenda || 'Mídia não disponível'}
      </p>
    )
  }

  if (loading || !url) return <p className="text-[10px] animate-pulse opacity-50">Carregando mídia...</p>

  if (err) return <p className="text-[10px] italic opacity-50">Erro ao carregar mídia</p>

  const mediaClass = 'max-h-64 max-w-full rounded-lg border border-black/5 shadow-sm'

  if (tipo === 'imagem' || tipo === 'figurinha') {
    return (
      <div className="space-y-1">
        <img
          src={url}
          alt=""
          className={`${mediaClass} cursor-zoom-in transition-transform duration-200 hover:scale-[1.02]`}
          onClick={() => onImageClick(m.id)}
        />
        {legenda ? <TextoComLinks texto={legenda} /> : null}
      </div>
    )
  }

  if (tipo === 'audio') return <CustomAudioPlayer src={url} />

  if (tipo === 'video') {
    return (
      <div className="space-y-1">
        <div className="relative inline-block max-w-full">
          <video controls src={url} className={mediaClass} />
          <button
            type="button"
            className="absolute bottom-2 right-2 rounded-md bg-black/65 px-2.5 py-1.5 text-[11px] font-semibold text-white shadow-sm backdrop-blur-sm transition hover:bg-black/80"
            onClick={() => onVideoClick(m.id)}
          >
            Expandir
          </button>
        </div>
        {legenda ? <TextoComLinks texto={legenda} /> : null}
      </div>
    )
  }

  const downloadLabel = rotuloDownloadArquivo(m.midia_nome_original, m.mimetype, tipo)
  const fileVisual = visualTipoArquivo(m.midia_nome_original, m.mimetype)
  const downloadName = (m.midia_nome_original || '').trim() || undefined

  return (
    <div className="space-y-1">
      <a href={url} download={downloadName} className="flex items-center gap-2 text-xs font-bold underline">
        <span className="text-base" aria-hidden>
          {fileVisual.emoji}
        </span>
        <span className="min-w-0 break-all">{downloadLabel.replace(/^\S+\s*/, '')}</span>
      </a>
      {legenda ? <TextoComLinks texto={legenda} /> : null}
    </div>
  )
}



/** Lightbox com galeria só de imagens (#629). */
function WhatsappZoomLightbox({
  chatId,
  msgs,
  zoomMsgId,
  onClose,
  onChangeMsgId,
}: {
  chatId: number
  msgs: WhatsappChats.Mensagem[]
  zoomMsgId: number
  onClose: () => void
  onChangeMsgId: (msgId: number) => void
}) {
  const galeria = useMemo(
    () =>
      msgs.filter(
        (m) => (m.tipo_midia || '').toLowerCase() === 'imagem' && m.midia_disponivel,
      ),
    [msgs],
  )
  const index = galeria.findIndex((m) => m.id === zoomMsgId)
  const msgAtiva = msgs.find((m) => m.id === zoomMsgId) || null
  const caption = msgAtiva ? legendaMidiaVisivel(msgAtiva.corpo) : null
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setUrl(null)
    void resolveWhatsappMidiaObjectUrl(chatId, zoomMsgId, () => fetchWhatsAppMidiaBlob(chatId, zoomMsgId))
      .then((u) => {
        if (!cancelled) setUrl(u)
      })
      .catch(() => {
        if (!cancelled) setUrl(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [chatId, zoomMsgId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      if (index < 0 || galeria.length <= 1) return
      e.preventDefault()
      e.stopPropagation()
      if (e.key === 'ArrowLeft' && index > 0) onChangeMsgId(galeria[index - 1].id)
      if (e.key === 'ArrowRight' && index < galeria.length - 1) onChangeMsgId(galeria[index + 1].id)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [galeria, index, onChangeMsgId])

  const podePrev = index > 0
  const podeNext = index >= 0 && index < galeria.length - 1

  return (
    <div
      className="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-black/90 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <button
        type="button"
        className="absolute top-4 right-4 flex h-12 w-12 cursor-pointer items-center justify-center rounded-full bg-white/10 text-3xl font-bold text-white transition-colors touch-manipulation hover:bg-white/20"
        onClick={onClose}
        aria-label="Fechar"
      >
        &times;
      </button>
      {index >= 0 && galeria.length > 1 && (
        <p className="absolute top-5 left-1/2 -translate-x-1/2 text-sm font-medium text-white/80">
          {index + 1} / {galeria.length}
        </p>
      )}
      {podePrev && (
        <button
          type="button"
          className="absolute left-3 top-1/2 z-10 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-2xl text-white hover:bg-white/20 sm:left-6"
          onClick={(e) => {
            e.stopPropagation()
            onChangeMsgId(galeria[index - 1].id)
          }}
          aria-label="Imagem anterior"
        >
          ‹
        </button>
      )}
      {podeNext && (
        <button
          type="button"
          className="absolute right-3 top-1/2 z-10 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-2xl text-white hover:bg-white/20 sm:right-6"
          onClick={(e) => {
            e.stopPropagation()
            onChangeMsgId(galeria[index + 1].id)
          }}
          aria-label="Próxima imagem"
        >
          ›
        </button>
      )}
      {loading || !url ? (
        <p className="text-sm text-white/70 animate-pulse">Carregando imagem…</p>
      ) : (
        <ImageLightboxViewer src={url} />
      )}
      {caption && (
        <p
          className="mt-4 max-w-2xl rounded-xl bg-black/40 px-4 py-2 text-center text-sm text-white backdrop-blur-md"
          onClick={(e) => e.stopPropagation()}
        >
          {caption}
        </p>
      )}
      {url && (
        <a
          href={url}
          download="whatsapp-imagem.jpg"
          className="absolute bottom-4 right-4 flex items-center gap-2 rounded-xl bg-cyan-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-cyan-600/30 transition-all hover:scale-105 hover:bg-cyan-700"
          onClick={(e) => e.stopPropagation()}
        >
          📥 Baixar Imagem
        </a>
      )}
    </div>
  )
}

/** Overlay ampliado para vídeos da mesa (#680). */
function WhatsappVideoLightbox({
  chatId,
  msgId,
  caption,
  onClose,
}: {
  chatId: number
  msgId: number
  caption: string | null
  onClose: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setUrl(null)
    void resolveWhatsappMidiaObjectUrl(chatId, msgId, () => fetchWhatsAppMidiaBlob(chatId, msgId))
      .then((u) => {
        if (!cancelled) setUrl(u)
      })
      .catch(() => {
        if (!cancelled) setUrl(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [chatId, msgId])

  async function entrarTelaCheia() {
    const el = videoRef.current
    if (!el) return
    try {
      if (el.requestFullscreen) await el.requestFullscreen()
      else if ('webkitRequestFullscreen' in el) {
        await (el as HTMLVideoElement & { webkitRequestFullscreen: () => Promise<void> }).webkitRequestFullscreen()
      }
    } catch {
      /* browser bloqueou — overlay já é o fallback */
    }
  }

  return (
    <div
      className="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-black/90 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <button
        type="button"
        className="absolute top-4 right-4 flex h-12 w-12 cursor-pointer items-center justify-center rounded-full bg-white/10 text-3xl font-bold text-white transition-colors touch-manipulation hover:bg-white/20"
        onClick={onClose}
        aria-label="Fechar"
      >
        &times;
      </button>
      {loading || !url ? (
        <p className="animate-pulse text-sm text-white/70">Carregando vídeo…</p>
      ) : (
        <div className="flex max-h-[90vh] w-full max-w-5xl flex-col items-center gap-3" onClick={(e) => e.stopPropagation()}>
          <video
            ref={videoRef}
            controls
            autoPlay
            src={url}
            className="max-h-[min(80vh,48rem)] w-full rounded-xl bg-black shadow-2xl"
          />
          <div className="flex flex-wrap items-center justify-center gap-2">
            <button
              type="button"
              className="rounded-xl bg-white/15 px-4 py-2 text-xs font-semibold text-white transition hover:bg-white/25"
              onClick={() => void entrarTelaCheia()}
            >
              Tela cheia
            </button>
            <a
              href={url}
              download="whatsapp-video.mp4"
              className="rounded-xl bg-cyan-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-cyan-700"
            >
              Baixar vídeo
            </a>
          </div>
          {caption ? (
            <p className="max-w-2xl rounded-xl bg-black/40 px-4 py-2 text-center text-sm text-white backdrop-blur-md">
              {caption}
            </p>
          ) : null}
        </div>
      )}
    </div>
  )
}

/** Foto do contacto em overlay (#681). */
function WhatsappFotoPerfilLightbox({ src, nome, onClose }: { src: string; nome?: string | null; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-black/90 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      role="presentation"
    >
      <button
        type="button"
        className="absolute top-4 right-4 flex h-12 w-12 cursor-pointer items-center justify-center rounded-full bg-white/10 text-3xl font-bold text-white transition-colors touch-manipulation hover:bg-white/20"
        onClick={onClose}
        aria-label="Fechar"
      >
        &times;
      </button>
      <img
        src={src}
        alt={nome ? `Foto de ${nome}` : 'Foto do contacto'}
        className="max-h-[85vh] max-w-full rounded-2xl object-contain shadow-2xl"
        referrerPolicy="no-referrer"
        onClick={(e) => e.stopPropagation()}
      />
      {nome ? (
        <p className="mt-4 text-sm font-medium text-white/90" onClick={(e) => e.stopPropagation()}>
          {nome}
        </p>
      ) : null}
    </div>
  )
}

const WA_DETALHES_SESSION_KEY = 'deskrudder-wa-conversa-detalhes'

// --- Componente Principal ---

type WhatsappConversaProps = {
  /** Conversa aberta pelo hub (sem id na URL) (#654). */
  chatIdProp?: number
}

export function WhatsappConversa({ chatIdProp }: WhatsappConversaProps = {}) {

  const { chatId } = useParams<{ chatId: string }>()

  const id = chatIdProp ?? Number(chatId)

  const toast = useToast()

  const { user } = useAuth()
  const { subscribe, useFallback } = useEventStream()

 

  // Refs

  const scrollRef = useRef<HTMLDivElement>(null)
  const stickToBottomRef = useRef(true)
  const initialScrollRestoredRef = useRef(false)
  const saveScrollRafRef = useRef<number | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const carregarGenRef = useRef(0)

  const [pickerAnexo, setPickerAnexo] = useState<TipoAnexoPicker>('imagem')
  const [arquivoPendente, setArquivoPendente] = useState<File | null>(null)
  const [dragAtivo, setDragAtivo] = useState(false)
  const dragDepthRef = useRef(0)
  const [legendaMidia, setLegendaMidia] = useState('')



  // Estados de Dados

  const [chat, setChat] = useState<WhatsappChats.Chat | null>(null)

  const [msgs, setMsgs] = useState<WhatsappChats.Mensagem[]>([])

  const [meusChats, setMeusChats] = useState<WhatsappChats.Chat[]>([])

  const chatRef = useRef(chat)
  const userIdRef = useRef(user?.id)
  chatRef.current = chat
  userIdRef.current = user?.id

 

  // Estados de UI

  const [sidebarAberta, setSidebarAberta] = useState(true)

  const [loading, setLoading] = useState(true)

  const [texto, setTexto] = useState('')

  const [enviando, setEnviando] = useState(false)
  const enviandoRef = useRef(false)
  const enviandoMidiaRef = useRef(false)
  const [reagirMsgId, setReagirMsgId] = useState<number | null>(null)

  // Estados de WhatsApp Clone (Citação e Zoom)
  const [msgRespondida, setMsgRespondida] = useState<WhatsappChats.Mensagem | null>(null)
  const [focoComposerEm, setFocoComposerEm] = useState(0)
  const [zoomMsgId, setZoomMsgId] = useState<number | null>(null)
  const [videoZoomMsgId, setVideoZoomMsgId] = useState<number | null>(null)
  const [fotoPerfilAberta, setFotoPerfilAberta] = useState(false)
  const [numeroCopiado, setNumeroCopiado] = useState(false)
  const [detalhesMobileAbertos, setDetalhesMobileAbertos] = useState(() => {
    try {
      return sessionStorage.getItem(WA_DETALHES_SESSION_KEY) === '1'
    } catch {
      return false
    }
  })
  const [modoInterno, setModoInterno] = useState(false)
  const [modalAssumirSetor, setModalAssumirSetor] = useState(false)

  // Transferência
  const [modalTransferir, setModalTransferir] = useState(false)
  const [transferSetorId, setTransferSetorId] = useState<number | ''>('')
  const [transferAtendenteId, setTransferAtendenteId] = useState<number | ''>('')
  const [transferindo, setTransferindo] = useState(false)
  const [modalVincFuncionario, setModalVincFuncionario] = useState(false)
  const [modalEmpresaContexto, setModalEmpresaContexto] = useState(false)
  const [empresaContextoId, setEmpresaContextoId] = useState<number | ''>('')
  const [salvandoEmpresaContexto, setSalvandoEmpresaContexto] = useState(false)

  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [atendentesDestino, setAtendentesDestino] = useState<Atendentes.Atendente[]>([])
  const [erroAtendentesDestino, setErroAtendentesDestino] = useState<string | null>(null)

  // Modais (Vincular/Transferir/Abrir)

  const [modalTickets, setModalTickets] = useState(false)
  const [ticketsVinculados, setTicketsVinculados] = useState<Tickets.Ticket[]>([])
  const [demandasReloadKey, setDemandasReloadKey] = useState(0)
  const [demandasTimeline, setDemandasTimeline] = useState<WhatsappChats.Demanda[]>([])
  const [modalEncerrar, setModalEncerrar] = useState(false)
  const [menuMobileAberto, setMenuMobileAberto] = useState(false)
  const menuMobileRef = useRef<HTMLDivElement>(null)
  const [filaAguardandoAberta, setFilaAguardandoAberta] = useState(false)
  const [assumindo, setAssumindo] = useState(false)
  const { filaCount, refreshContagens, abrirChat } = useChatHub()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const { voltarLista, sairParaListaSegura } = useWhatsappVoltarLista()
  const listaRetorno = resolveWhatsappListFallback(
    location.state,
    searchParams.get('from'),
    WHATSAPP_LIST_PATHS.atendendo,
  )

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || e.defaultPrevented || modalEncerrar) return
      const tag = (e.target as HTMLElement | null)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return
      // Overlays locais primeiro — não sair da conversa (#571 / #653)
      if (zoomMsgId != null) {
        e.preventDefault()
        e.stopPropagation()
        setZoomMsgId(null)
        return
      }
      if (videoZoomMsgId != null) {
        e.preventDefault()
        e.stopPropagation()
        setVideoZoomMsgId(null)
        return
      }
      if (fotoPerfilAberta) {
        e.preventDefault()
        e.stopPropagation()
        setFotoPerfilAberta(false)
        return
      }
      if (arquivoPendente) {
        e.preventDefault()
        setArquivoPendente(null)
        setLegendaMidia('')
        return
      }
      if (filaAguardandoAberta) {
        e.preventDefault()
        setFilaAguardandoAberta(false)
        return
      }
      if (menuMobileAberto) {
        e.preventDefault()
        setMenuMobileAberto(false)
        return
      }
      // Sai para lista segura — nunca history.back pela pilha de chats (#653)
      e.preventDefault()
      sairParaListaSegura()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [
    sairParaListaSegura,
    modalEncerrar,
    zoomMsgId,
    videoZoomMsgId,
    fotoPerfilAberta,
    arquivoPendente,
    filaAguardandoAberta,
    menuMobileAberto,
  ])

  useEffect(() => {
    if (!menuMobileAberto) return
    const onDoc = (e: globalThis.MouseEvent) => {
      if (menuMobileRef.current && !menuMobileRef.current.contains(e.target as Node)) {
        setMenuMobileAberto(false)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [menuMobileAberto])

  const viuEmAtendimentoRef = useRef(false)
  const inatividadeToastFeitoRef = useRef(false)
  const fechouPainelAposEncerrarRef = useRef(false)

  useEffect(() => {
    viuEmAtendimentoRef.current = false
    inatividadeToastFeitoRef.current = false
    fechouPainelAposEncerrarRef.current = false
  }, [id])

  useEffect(() => {
    if (chat?.id === id && chat.estado === 'em_atendimento') {
      viuEmAtendimentoRef.current = true
    }
  }, [chat?.id, chat?.estado, id])

  useEffect(() => {
    if (!chat || chat.id !== id || inatividadeToastFeitoRef.current) return
    if (!viuEmAtendimentoRef.current) return

    const fechado = chat.estado === 'encerrado' || chat.estado === 'aguardando_avaliacao'
    if (!fechado || !chatEncerramentoPorInatividade(msgs)) return
    if (!chat.classificacao_demanda_pendente) return

    const podeClassificar =
      chat.atendente_id === user?.id || user?.role === 'admin'
    if (!podeClassificar) return

    inatividadeToastFeitoRef.current = true
    toast.showSuccess(
      'Atendimento encerrado por inatividade. Pode reler a conversa e registar a demanda no aviso abaixo.',
    )
  }, [chat, id, msgs, user?.id, user?.role, toast])

  useEffect(() => {
    if (!chat || chat.id !== id || fechouPainelAposEncerrarRef.current) return
    const naMesa = chatIdProp != null || location.pathname.startsWith('/chat/')
    if (!naMesa || !viuEmAtendimentoRef.current) return
    const fechado = chat.estado === 'encerrado' || chat.estado === 'aguardando_avaliacao'
    if (!fechado || chat.classificacao_demanda_pendente) return
    fechouPainelAposEncerrarRef.current = true
    voltarLista()
  }, [chat, id, chatIdProp, location.pathname, voltarLista])

  const refrescarTimelineDemandas = useCallback(() => {
    setDemandasReloadKey((k) => k + 1)
  }, [])

  useEffect(() => {
    if (!id) return
    whatsappChats
      .demandas(id)
      .then(setDemandasTimeline)
      .catch(() => setDemandasTimeline([]))
  }, [id, demandasReloadKey])



  // Scroll: restaurar última posição vista; só cola no fim se já estava no fundo.
  useEffect(() => {
    if (!id) return
    initialScrollRestoredRef.current = false
    stickToBottomRef.current = false
  }, [id])

  useEffect(() => {
    if (loading || msgs.length === 0 || initialScrollRestoredRef.current || !id) return
    initialScrollRestoredRef.current = true
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const el = scrollRef.current
        if (!el) return
        stickToBottomRef.current = restoreWhatsappScroll(Number(id), el)
      })
    })
  }, [loading, msgs.length, id])

  useEffect(() => {
    if (loading || !initialScrollRestoredRef.current || !stickToBottomRef.current) return
    requestAnimationFrame(() => {
      const el = scrollRef.current
      if (el) scrollWhatsappToBottom(el)
    })
  }, [msgs, loading])

  /** #751: ao abrir o teclado, manter a última mensagem acima do composer. */
  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    const onVv = () => {
      if (!stickToBottomRef.current) return
      requestAnimationFrame(() => {
        const el = scrollRef.current
        if (el) scrollWhatsappToBottom(el)
      })
    }
    vv.addEventListener('resize', onVv)
    vv.addEventListener('scroll', onVv)
    return () => {
      vv.removeEventListener('resize', onVv)
      vv.removeEventListener('scroll', onVv)
    }
  }, [])
  useEffect(() => {
    const el = scrollRef.current
    if (!el || !id) return
    const chatId = Number(id)

    const onScroll = () => {
      stickToBottomRef.current = isNearBottom(el)
      if (saveScrollRafRef.current != null) cancelAnimationFrame(saveScrollRafRef.current)
      saveScrollRafRef.current = requestAnimationFrame(() => {
        saveWhatsappScroll(chatId, el)
      })
    }

    el.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      el.removeEventListener('scroll', onScroll)
      if (saveScrollRafRef.current != null) cancelAnimationFrame(saveScrollRafRef.current)
      saveWhatsappScroll(chatId, el)
    }
  }, [id, loading])

  // Carregar lista de chats lateral

  const carregarSidebar = useCallback(async () => {

    try {

      const rows = await whatsappChats.meus()

      setMeusChats((prev) =>
        rows.map((row) => {
          const antigo = prev.find((c) => c.id === row.id)
          return antigo ? mergeWhatsappChat(antigo, row) : row
        }),
      )

    } catch { setMeusChats([]) }

  }, [])



  // Carregar conversa e mensagens

  const carregar = useCallback(async () => {

    if (!id) return

    const gen = ++carregarGenRef.current
    const el = scrollRef.current
    const stick = stickToBottomRef.current
    const prevTop = el?.scrollTop ?? 0
    const prevHeight = el?.scrollHeight ?? 0

    try {

      const [c, m] = await Promise.all([whatsappChats.get(id), whatsappChats.mensagens(id)])

      if (gen !== carregarGenRef.current) return

      setChat((prev) => mergeWhatsappChat(prev, c))

      setMsgs(whatsappMensagensUnicas(m))

      requestAnimationFrame(() => {
        if (!initialScrollRestoredRef.current) return
        const container = scrollRef.current
        if (!container) return
        if (stick) {
          scrollWhatsappToBottom(container)
        } else if (el) {
          preserveScrollOnContentChange(container, prevTop, prevHeight)
        }
      })

    } catch (err) {

      toast.showError(mensagemFalhaParaToast(err))

    }

  }, [id, toast])



  const aplicarChatAtualizado = useCallback((atualizado: WhatsappChats.Chat) => {
    carregarGenRef.current += 1
    setChat(atualizado)
    setMeusChats((prev) => replaceWhatsappChatLista(prev, atualizado))
  }, [])



  useEffect(() => {

    void carregarSidebar()

  }, [carregarSidebar])



  useEffect(() => {

    if (!id) return

    setLoading(true)
    viuEmAtendimentoRef.current = false
    inatividadeToastFeitoRef.current = false

    carregar().then(() => whatsappChats.marcarVisto(id)).finally(() => setLoading(false))

    return () => {
      revokeWhatsappMidiaForChat(Number(id))
    }

  }, [id, carregar])



  useEffect(() => {
    if (!chat) return
    const responsavel = chat.atendente_id === user?.id
    if (!responsavel && chat.estado === 'em_atendimento') {
      setModoInterno(true)
    } else {
      setModoInterno(false)
    }
  }, [chat, user?.id])

  useEffect(() => {
    // 1 empresa e ainda sem contexto: preenche automaticamente sem bloquear o atendimento
    if (!chat || !user?.id) return
    if (chat.atendente_id !== user.id || chat.estado !== 'em_atendimento') return
    if (chat.empresa_id) return
    const opcoes = chat.empresas_opcoes || []
    if (opcoes.length !== 1) return
    let cancelled = false
    void whatsappChats
      .definirEmpresaContexto(chat.id, opcoes[0].id)
      .then((atualizado) => {
        if (!cancelled) setChat((prev) => mergeWhatsappChat(prev, atualizado))
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [chat, user?.id])

  useEffect(() => {
    if (!id) return
    const chatId = Number(id)
    const unsubMsg = subscribe('chat.mensagem', (payload) => {
      if (Number(payload.chat_id) !== chatId) return
      const msg = normalizarReacoesMensagem(
        payload.mensagem as WhatsappChats.Mensagem,
        userIdRef.current,
      )
      if (!msg?.id) return
      setMsgs((prev) => {
        const mergeMsg = (prevRow: WhatsappChats.Mensagem, incoming: WhatsappChats.Mensagem) => {
          const merged = { ...prevRow, ...incoming }
          // SSE omite flags por visualizador; preservar as já conhecidas
          if (incoming.pode_editar === undefined) merged.pode_editar = prevRow.pode_editar
          if (incoming.pode_apagar_para_todos === undefined) {
            merged.pode_apagar_para_todos = prevRow.pode_apagar_para_todos
          }
          if (merged.apagada) {
            merged.pode_editar = false
            merged.pode_apagar_para_todos = false
          }
          return merged
        }
        const idx = prev.findIndex((m) => m.id === msg.id)
        if (idx >= 0) {
          const next = [...prev]
          next[idx] = mergeMsg(next[idx], msg)
          return next
        }
        if (msg.wa_message_id && prev.some((m) => m.wa_message_id === msg.wa_message_id)) {
          const widx = prev.findIndex((m) => m.wa_message_id === msg.wa_message_id)
          if (widx >= 0) {
            const next = [...prev]
            next[widx] = mergeMsg(next[widx], msg)
            return next
          }
        }
        return [...prev, msg]
      })
      // ✓✓ azul no WhatsApp do cliente: marcar leitura em inbound novo enquanto o responsável está no chat
      const c = chatRef.current
      if (
        msg.direcao === 'inbound' &&
        c?.estado === 'em_atendimento' &&
        c.atendente_id != null &&
        c.atendente_id === userIdRef.current
      ) {
        void whatsappChats.marcarVisto(chatId)
      }
    })
    const unsubFila = subscribe('chat.fila', (payload) => {
      const payloadChatId = Number(payload.chat_id)
      const chatData = payload.chat as WhatsappChats.Chat | undefined
      if (payloadChatId === chatId) {
        if (chatData) {
          carregarGenRef.current += 1
          setChat((prev) => mergeWhatsappChat(prev, chatData))
          setMeusChats((prev) => patchWhatsappChatLista(prev, chatData))
        } else {
          void carregar().catch(() => {})
        }
      }
      if (
        chatData &&
        chatData.estado !== 'em_atendimento' &&
        !chatData.classificacao_demanda_pendente
      ) {
        setMeusChats((prev) => prev.filter((c) => c.id !== payloadChatId))
      } else if (!chatData || payloadChatId !== chatId) {
        void carregarSidebar()
      }
    })
    return () => {
      unsubMsg()
      unsubFila()
    }
  }, [id, subscribe, carregar, carregarSidebar])

  // Polling de segurança (#442): complementa SSE quando Gunicorn usa N workers in-process
  useEffect(() => {
    if (!chat || chat.estado === 'encerrado' || chat.estado === 'aguardando_avaliacao') return
    const intervalMs = useFallback ? 5000 : 4000
    const t = setInterval(() => void carregar().catch(() => {}), intervalMs)
    return () => clearInterval(t)
  }, [useFallback, chat, carregar])

  useEffect(() => {
    if (!chat?.ticket_ids?.length) {
      setTicketsVinculados([])
      return
    }
    let cancelled = false
    Promise.all(chat.ticket_ids.map((tid) => tickets.get(tid)))
      .then((rows) => {
        if (!cancelled) setTicketsVinculados(rows)
      })
      .catch(() => {
        if (!cancelled) setTicketsVinculados([])
      })
    return () => {
      cancelled = true
    }
  }, [chat?.ticket_ids])

//transferencia de atendente
useEffect(() => {
  if (!modalTransferir) return

  if (chat?.setor_id) {
    setTransferSetorId(chat.setor_id)
  } else {
    setTransferSetorId('')
  }
  setTransferAtendenteId('')

  whatsappChats
    .setoresParaTransferencia()
    .then((rows) =>
      setSetoresList(
        rows.map((s) => ({
          id: s.id,
          nome: s.nome,
          slug: '',
          ativo: true,
        })) as unknown as Setores.Setor[],
      ),
    )
    .catch(() => setSetoresList([]))

  setAtendentesDestino([])
  setErroAtendentesDestino(null)
}, [modalTransferir, chat?.id, chat?.setor_id])

//transferencia de setor
useEffect(() => {
  const sid = transferSetorId === '' ? null : Number(transferSetorId)
  if (!modalTransferir || !sid) return

  setAtendentesDestino([])
  setErroAtendentesDestino(null)

  atendentes
    .listPorSetor(sid, { incluir_inativos: true })
    .then((rows) => {
      setAtendentesDestino(rows)
    })
    .catch((err) => {
      setAtendentesDestino([])
      setErroAtendentesDestino(mensagemFalhaParaToast(err))
    })
}, [modalTransferir, transferSetorId])

  function inserirReferenciaKb(ref: string) {
    const sep = texto && !texto.endsWith('\n') ? '\n\n' : texto ? '' : ''
    setTexto(texto + sep + ref)
  }

  function iniciarResposta(m: WhatsappChats.Mensagem) {
    setMsgRespondida(m)
    setFocoComposerEm((n) => n + 1)
  }

  function duploCliqueResponder(e: MouseEvent, m: WhatsappChats.Mensagem, isSystem: boolean) {
    if (isSystem || encerrado || !podeEnviar || modoInterno) return
    const t = e.target as HTMLElement
    // Só ao lado do balão — dentro do balão permite selecionar/copiar texto
    if (t.closest('[data-msg-bubble], button, a, input, textarea, video, audio')) return
    iniciarResposta(m)
  }

  async function enviar() {

    if (!chat || !texto.trim() || enviando || enviandoRef.current || (!modoInterno && !podeEnviar)) return

    enviandoRef.current = true
    setEnviando(true)

    try {
      if (modoInterno) {
        await whatsappChats.comentarInterno(chat.id, texto.trim())
      } else {
        await whatsappChats.enviar(chat.id, texto.trim(), msgRespondida?.wa_message_id || null)
      }

      setTexto('')
      setMsgRespondida(null)

      stickToBottomRef.current = true
      await carregar()

    } catch (err) {

      toast.showError(mensagemFalhaParaToast(err))

    } finally {
      enviandoRef.current = false
      setEnviando(false)
    }

  }

  async function transferirChat() {
  if (!chat) return

  if (!transferSetorId) {
    toast.showWarning('Selecione o setor de destino.')
    return
  }

  const setor_id = Number(transferSetorId)
  const atendente_id = transferAtendenteId
    ? Number(transferAtendenteId)
    : null

  setTransferindo(true)
  try {
    const atualizado = await whatsappChats.transferir(chat.id, {
      setor_id,
      atendente_id,
    })

    setModalTransferir(false)
    setTransferSetorId('')
    setTransferAtendenteId('')

    setChat(atualizado)
    await Promise.all([carregar(), carregarSidebar()])
    void refetchPendenciasResumo()

    toast.showSuccess(mensagemTransferenciaSucesso(atualizado))

    if (atualizado.atendente_id !== user?.id && atualizado.estado === 'em_atendimento') {
      navigate('/chat/atendendo')
    }
  } catch (err) {
    toast.showWarning(
      mensagemFalhaParaToast(err, 'Não foi possível transferir o chat.')
    )
  } finally {
    setTransferindo(false)
  }
}

  function abrirPickerAnexo(tipo: TipoAnexoPicker) {
    setPickerAnexo(tipo)
    window.setTimeout(() => fileInputRef.current?.click(), 0)
  }

  async function handleGravacaoConcluida(file: File) {
    if (!chat || enviando) return
    setEnviando(true)
    try {
      await whatsappChats.enviarMidia(
        chat.id,
        file,
        '',
        msgRespondida?.wa_message_id || null,
      )
      setMsgRespondida(null)
      stickToBottomRef.current = true
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao enviar áudio.'))
    } finally {
      setEnviando(false)
    }
  }

  function handleFileSelecionado(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !chat || !podeEnviar) {
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    setArquivoPendente(file)
    setLegendaMidia('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function confirmarEnvioMidia() {
    if (!arquivoPendente || !chat || !podeEnviar || enviando || enviandoMidiaRef.current) return
    enviandoMidiaRef.current = true
    setEnviando(true)
    try {
      await whatsappChats.enviarMidia(
        chat.id,
        arquivoPendente,
        legendaMidia.trim(),
        msgRespondida?.wa_message_id || null,
      )
      setMsgRespondida(null)
      setArquivoPendente(null)
      setLegendaMidia('')
      stickToBottomRef.current = true
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha no envio do anexo'))
    } finally {
      enviandoMidiaRef.current = false
      setEnviando(false)
    }
  }

  async function executarAssumirChat(setorId?: number) {
    if (!chat || chat.estado !== 'aguardando_atendente' || assumindo) return
    setAssumindo(true)
    try {
      const atualizado = await whatsappChats.assumir(
        chat.id,
        setorId != null ? { setor_id: setorId } : undefined,
      )
      setChat((prev) => mergeWhatsappChat(prev, atualizado))
      setModalAssumirSetor(false)
      void refreshContagens()
      void refetchPendenciasResumo()
      toast.showSuccess('Chat assumido.')
      abrirChat('whatsapp', chat.id)
      navigate(chatWhatsappLink('atendendo'), { replace: true })
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

  function assumirChat() {
    if (!chat || chat.estado !== 'aguardando_atendente' || assumindo) return
    if (precisaEscolherSetorAoAssumir(user, Boolean(chat.setor_id || chat.setor_nome))) {
      setModalAssumirSetor(true)
      return
    }
    void executarAssumirChat()
  }

  async function enviarFigurinha(file: File) {
    if (!chat || !podeEnviar || enviando || enviandoMidiaRef.current) return
    enviandoMidiaRef.current = true
    setEnviando(true)
    try {
      await whatsappChats.enviarFigurinha(chat.id, file, msgRespondida?.wa_message_id || null)
      setMsgRespondida(null)
      stickToBottomRef.current = true
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao enviar figurinha'))
    } finally {
      enviandoMidiaRef.current = false
      setEnviando(false)
    }
  }



  async function handleEncerrado(atualizado: WhatsappChats.Chat) {
    toast.showSuccess(
      atualizado.estado === 'aguardando_avaliacao' && atualizado.classificacao_demanda_pendente
        ? 'Atendimento encerrado. Aguardando avaliação do cliente.'
        : atualizado.classificacao_demanda_pendente === false && chatEncerramentoPorInatividade(msgs)
          ? 'Classificação da sessão concluída.'
          : atualizado.estado === 'aguardando_avaliacao'
            ? 'Atendimento encerrado. Aguardando avaliação do cliente.'
            : 'Atendimento encerrado.',
    )
    void refreshContagens()
    void refetchPendenciasResumo()
    const naMesa = chatIdProp != null || location.pathname.startsWith('/chat/')
    // Demanda pendente: o painel fica aberto para classificar. Caso contrário, fecha como Voltar.
    if (naMesa && !atualizado.classificacao_demanda_pendente) {
      fechouPainelAposEncerrarRef.current = true
      voltarLista()
      return
    }
    setChat(atualizado)
    await Promise.all([carregar(), carregarSidebar()])
    refrescarTimelineDemandas()
  }

  async function confirmarEmpresaContexto() {
    if (!chat || empresaContextoId === '') {
      toast.showWarning('Selecione a empresa do atendimento.')
      return
    }
    setSalvandoEmpresaContexto(true)
    try {
      const atualizado = await whatsappChats.definirEmpresaContexto(chat.id, Number(empresaContextoId))
      setChat((prev) => mergeWhatsappChat(prev, atualizado))
      setModalEmpresaContexto(false)
      setEmpresaContextoId('')
      toast.showSuccess('Empresa do atendimento definida.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível definir a empresa.'))
    } finally {
      setSalvandoEmpresaContexto(false)
    }
  }

  function abrirModalEmpresaContexto() {
    if (!chat) return
    setEmpresaContextoId(chat.empresa_id ?? '')
    setModalEmpresaContexto(true)
  }



  if (loading && !chat) return <div className="flex h-full items-center justify-center italic text-slate-400">Carregando workspace...</div>



  const encerrado = chat?.estado === 'encerrado' || chat?.estado === 'aguardando_avaliacao'

  const isResponsavel = chat?.atendente_id === user?.id
  const isAdmin = user?.role === 'admin'

  const podeTransferir = !encerrado && (isResponsavel || isAdmin)

  const podeEnviar =
    chat?.estado === 'em_atendimento' &&
    isResponsavel &&
    !encerrado &&
    !chat?.classificacao_demanda_pendente

  const podeReagir = Boolean(podeEnviar)

  async function reagirMensagem(m: WhatsappChats.Mensagem, emoji: string) {
    if (!chat || !podeReagir || m.evento_sistema || m.apagada) return
    try {
      const atualizada = await whatsappChats.definirReacao(chat.id, m.id, emoji)
      setMsgs((prev) =>
        prev.map((row) =>
          row.id === atualizada.id ? normalizarReacoesMensagem(atualizada, user?.id) : row,
        ),
      )
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao reagir'))
    }
  }

  async function editarMensagemWhatsapp(m: WhatsappChats.Mensagem, texto: string) {
    if (!chat) return
    try {
      const atualizada = await whatsappChats.editarMensagem(chat.id, m.id, texto)
      setMsgs((prev) =>
        prev.map((row) =>
          row.id === atualizada.id ? normalizarReacoesMensagem(atualizada, user?.id) : row,
        ),
      )
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao editar mensagem'))
      throw err
    }
  }

  async function apagarMensagemWhatsapp(m: WhatsappChats.Mensagem) {
    if (!chat) return
    try {
      const atualizada = await whatsappChats.apagarMensagem(chat.id, m.id)
      setMsgs((prev) =>
        prev.map((row) =>
          row.id === atualizada.id ? normalizarReacoesMensagem(atualizada, user?.id) : row,
        ),
      )
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao apagar mensagem'))
      throw err
    }
  }

  const podeEncerrar = !encerrado && chat?.estado === 'em_atendimento' && (isResponsavel || isAdmin)

  const podeDefinirEmpresa =
    !encerrado &&
    Boolean(chat?.funcionario_rede_id) &&
    (chat?.empresas_opcoes?.length ?? 0) > 0 &&
    (isResponsavel || isAdmin)

  const precisaEmpresaContexto =
    podeDefinirEmpresa && !chat?.empresa_id && (chat?.empresas_opcoes?.length ?? 0) > 1

  const mostrarBannerDemandaInatividade =
    Boolean(chat?.classificacao_demanda_pendente) && (isResponsavel || isAdmin)

  const podeDigitarMensagem = !encerrado && !chat?.classificacao_demanda_pendente && (modoInterno || podeEnviar)

  const composerPlaceholder =
    encerrado || chat?.classificacao_demanda_pendente
      ? chat?.classificacao_demanda_pendente
        ? 'Chat aguarda classificação de demanda (somente leitura)'
        : 'Chat encerrado'
      : !podeEnviar && chat?.estado === 'em_atendimento'
        ? 'Apenas o responsável pode enviar ao cliente — use comentário interno'
        : modoInterno
          ? 'Comentário interno (não enviado ao cliente)…'
          : 'Digite uma mensagem…'

  const motivoAnexoDesabilitado =
    encerrado
      ? undefined
      : chat?.estado === 'aguardando_atendente'
        ? 'Assuma este chat para enviar anexos ao cliente.'
        : !podeEnviar && chat?.estado === 'em_atendimento'
          ? `Este chat está com ${chat.atendente_nome || 'outro atendente'}.`
          : undefined

  const modoHub = chatIdProp != null || location.pathname.startsWith('/chat/')

  const podeAceitarDrop = Boolean(podeEnviar && !encerrado && !modoInterno && !enviando)

  function resetDrag() {
    dragDepthRef.current = 0
    setDragAtivo(false)
  }

  function handleDragEnter(e: DragEvent<HTMLElement>) {
    e.preventDefault()
    e.stopPropagation()
    if (![...e.dataTransfer.types].includes('Files')) return
    dragDepthRef.current += 1
    if (podeAceitarDrop) setDragAtivo(true)
  }

  function handleDragOver(e: DragEvent<HTMLElement>) {
    e.preventDefault()
    e.stopPropagation()
    if (![...e.dataTransfer.types].includes('Files')) return
    e.dataTransfer.dropEffect = podeAceitarDrop ? 'copy' : 'none'
  }

  function handleDragLeave(e: DragEvent<HTMLElement>) {
    e.preventDefault()
    e.stopPropagation()
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1)
    if (dragDepthRef.current === 0) setDragAtivo(false)
  }

  function handleDrop(e: DragEvent<HTMLElement>) {
    e.preventDefault()
    e.stopPropagation()
    resetDrag()
    const files = Array.from(e.dataTransfer.files || [])
    if (files.length === 0) return
    if (!podeAceitarDrop) {
      toast.showWarning(motivoAnexoDesabilitado || 'Não é possível anexar neste chat.')
      return
    }
    setArquivoPendente(files[0])
    setLegendaMidia('')
    if (files.length > 1) {
      toast.showWarning('Só é possível anexar um ficheiro de cada vez. Foi usado o primeiro.')
    }
  }

  return (

    <div
      className={
        modoHub
          ? 'flex h-full min-h-0 overflow-hidden bg-white dark:bg-slate-950'
          : 'flex h-[calc(100vh-140px)] min-h-[500px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-950'
      }
    >

     

      {/* SIDEBAR RECOLHÍVEL — oculta no hub unificado (/chat) */}

      {!modoHub && (
      <aside className={`

        transition-all duration-300 ease-in-out border-r border-slate-100 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/30

        ${sidebarAberta ? 'w-72' : 'w-16'} flex flex-col overflow-hidden

      `}>

        <div className="flex h-16 items-center justify-between px-4 border-b border-slate-100 dark:border-slate-800 shrink-0">

          {sidebarAberta && <h2 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Meus Chats</h2>}

          <Button

            variant="ghost"


            onClick={() => setSidebarAberta(!sidebarAberta)}

            className={`hover:bg-slate-200/50 dark:hover:bg-slate-800 ${!sidebarAberta ? 'mx-auto' : ''}`}

          >

            {sidebarAberta ? '❮' : '❯'}

          </Button>

        </div>

       

        <div className="flex-1 overflow-y-auto">

          {meusChats.map((c) => (

            <Link

              key={c.id}

              to={whatsappConversaLink(listaRetorno)}

              onClick={() => marcarWhatsappChatAtivo(c.id)}

              className={`flex items-center p-4 gap-3 transition-colors ${c.id === id ? 'bg-white shadow-sm dark:bg-slate-800' : 'hover:bg-white/40 dark:hover:bg-slate-900/50'}`}

            >

              <WhatsappAvatar
                nome={c.cliente_nome}
                fotoUrl={c.foto_perfil_url}
                className="h-8 w-8 text-xs shadow-sm"
                fallbackClassName={
                  c.id === id
                    ? 'bg-cyan-600 text-white'
                    : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                }
              />

              {sidebarAberta && (

                <div className="min-w-0 flex-1">

                  <div className="flex justify-between items-center">

                    <p className="truncate text-sm font-bold text-slate-800 dark:text-slate-100">{c.cliente_nome || 'Cliente'}</p>

                    {c.estado === 'aguardando_atendente' && <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />}
                    {c.classificacao_demanda_pendente && (
                      <span className="shrink-0 rounded-full bg-amber-100 px-1.5 py-0.5 text-[9px] font-medium text-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
                        Demanda
                      </span>
                    )}
                    {!c.funcionario_rede_id && (
                      <span className="shrink-0 rounded-full bg-violet-100 px-1.5 py-0.5 text-[9px] font-medium text-violet-700 dark:bg-violet-950/50 dark:text-violet-300">
                        Sem vínculo
                      </span>
                    )}

                  </div>

                  <p className="truncate text-[10px] font-mono text-slate-400" title={exibirProtocolo(c.protocolo)}>
                    {exibirProtocolo(c.protocolo)}
                  </p>
                  <p className="truncate text-[10px] text-slate-500 dark:text-slate-400">
                    {rotuloResponsavelChat(c, user?.id)}
                  </p>

                </div>

              )}

            </Link>

          ))}

        </div>

      </aside>
      )}



      {/* ÁREA DE CONVERSA */}

      <main
        className="relative flex min-w-0 flex-1 flex-col bg-white dark:bg-slate-950"
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {dragAtivo && podeAceitarDrop && (
          <div
            className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center border-2 border-dashed border-cyan-500 bg-cyan-950/40"
            aria-hidden
          >
            <p className="rounded-xl bg-white/95 px-4 py-2 text-sm font-semibold text-cyan-800 shadow-sm dark:bg-slate-900/95 dark:text-cyan-200">
              Solte o ficheiro para anexar
            </p>
          </div>
        )}

       

        {/* Header do Chat */}

        <header className="shrink-0 border-b border-slate-100 shadow-sm z-10 dark:border-slate-800">

          <div className="flex items-center gap-2 px-3 py-2 sm:px-4">

            <Button
              type="button"
              variant="ghost"
              className="h-11 shrink-0 px-2 text-xs font-medium md:h-9"
              onClick={voltarLista}
              aria-label="Voltar à lista"
            >
              <span aria-hidden>←</span>
              <span className="hidden sm:inline"> Voltar</span>
            </Button>

            <WhatsappAvatar
              nome={chat?.cliente_nome}
              fotoUrl={chat?.foto_perfil_url}
              className="h-9 w-9 text-sm"
              fallbackClassName="bg-cyan-100 text-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-200"
              onFotoClick={
                chat?.foto_perfil_url ? () => setFotoPerfilAberta(true) : undefined
              }
            />
            <div className="min-w-0 flex-1">
              <h1 className="truncate font-bold text-slate-900 dark:text-white">
                {chat?.cliente_nome || 'Atendimento'}
              </h1>
              {chat?.wa_id ? (
                <button
                  type="button"
                  className="mt-0.5 max-w-full truncate font-mono text-[11px] text-slate-500 transition hover:text-cyan-700 dark:text-slate-400 dark:hover:text-cyan-300"
                  title={numeroCopiado ? 'Copiado' : 'Clique para copiar o número'}
                  onClick={() => {
                    const raw = chat.wa_id
                    void navigator.clipboard?.writeText(raw).then(() => {
                      setNumeroCopiado(true)
                      window.setTimeout(() => setNumeroCopiado(false), 1500)
                    })
                  }}
                >
                  {numeroCopiado ? 'Copiado!' : formatWaIdExibicao(chat.wa_id)}
                </button>
              ) : null}
            </div>

            <button
              type="button"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 md:hidden dark:hover:bg-slate-800 dark:hover:text-slate-100"
              aria-expanded={detalhesMobileAbertos}
              aria-label={detalhesMobileAbertos ? 'Ocultar detalhes' : 'Mostrar detalhes'}
              onClick={() => {
                setDetalhesMobileAbertos((aberto) => {
                  const next = !aberto
                  try {
                    sessionStorage.setItem(WA_DETALHES_SESSION_KEY, next ? '1' : '0')
                  } catch {
                    /* ignore */
                  }
                  return next
                })
              }}
            >
              <span className="text-lg leading-none" aria-hidden>
                {detalhesMobileAbertos ? '▴' : '▾'}
              </span>
            </button>

            <div className="flex shrink-0 items-center gap-1 md:gap-2">

              {chat?.estado === 'aguardando_atendente' && (
                <Button
                  type="button"
                  variant="primary"
                  className="h-11 shrink-0 px-3 text-xs font-semibold"
                  loading={assumindo}
                  onClick={() => void assumirChat()}
                >
                  Atender
                </Button>
              )}

              {!encerrado && (
                <>
                  {chat && (
                    <div className="hidden md:flex">
                      <WhatsappInatividadeControle
                        chat={chat}
                        msgs={msgs}
                        isResponsavel={isResponsavel}
                        onChatUpdate={aplicarChatAtualizado}
                      />
                    </div>
                  )}
                  {podeTransferir && (
                    <Button
                      variant="primary"
                      className="hidden md:inline-flex h-8 text-xs"
                      onClick={() => setModalTransferir(true)}
                    >
                      Transferir
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    className="hidden md:inline-flex h-8 text-xs"
                    onClick={() => setModalTickets(true)}
                  >
                    Tickets{ticketsVinculados.length > 0 ? ` (${ticketsVinculados.length})` : ''}
                  </Button>

                  {podeEncerrar && (
                    <Button variant="danger" className="hidden h-8 px-3 text-xs md:inline-flex" onClick={() => setModalEncerrar(true)}>
                      Encerrar
                    </Button>
                  )}

                  <div className="relative md:hidden" ref={menuMobileRef}>
                    <button
                      type="button"
                      aria-label="Mais ações"
                      aria-expanded={menuMobileAberto}
                      onClick={() => setMenuMobileAberto((o) => !o)}
                      className="flex h-11 w-11 items-center justify-center rounded-lg text-lg text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      ⋮
                    </button>
                    {menuMobileAberto && (
                      <div className="absolute right-0 top-full z-30 mt-1 min-w-[12rem] rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                        {podeTransferir && (
                          <button
                            type="button"
                            className="block min-h-11 w-full px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                            onClick={() => {
                              setMenuMobileAberto(false)
                              setModalTransferir(true)
                            }}
                          >
                            Transferir
                          </button>
                        )}
                        <button
                          type="button"
                          className="block min-h-11 w-full px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                          onClick={() => {
                            setMenuMobileAberto(false)
                            setModalTickets(true)
                          }}
                        >
                          Tickets{ticketsVinculados.length > 0 ? ` (${ticketsVinculados.length})` : ''}
                        </button>
                        {podeEncerrar && (
                          <button
                            type="button"
                            className="block min-h-11 w-full px-4 py-3 text-left text-sm text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40"
                            onClick={() => {
                              setMenuMobileAberto(false)
                              setModalEncerrar(true)
                            }}
                          >
                            Encerrar
                          </button>
                        )}
                        {podeDefinirEmpresa && (
                          <button
                            type="button"
                            className="block min-h-11 w-full px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                            onClick={() => {
                              setMenuMobileAberto(false)
                              abrirModalEmpresaContexto()
                            }}
                          >
                            {chat?.empresa_id ? 'Alterar empresa' : 'Definir empresa'}
                          </button>
                        )}
                        {modoHub && filaCount > 0 && (
                          <button
                            type="button"
                            className="block min-h-11 w-full border-t border-slate-100 px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-200 dark:hover:bg-slate-800"
                            onClick={() => {
                              setMenuMobileAberto(false)
                              setFilaAguardandoAberta(true)
                            }}
                          >
                            Aguardando ({filaCount > 99 ? '99+' : filaCount})
                          </button>
                        )}
                        {chat && (
                          <WhatsappInatividadeControle
                            chat={chat}
                            msgs={msgs}
                            isResponsavel={isResponsavel}
                            onChatUpdate={aplicarChatAtualizado}
                            className="border-t border-slate-100 px-3 py-2 dark:border-slate-800"
                          />
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}

            </div>

          </div>

          <div
            className={`space-y-1.5 px-3 pb-2 sm:px-4 sm:pb-3 ${detalhesMobileAbertos ? '' : 'hidden md:block'}`}
          >

            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px]">
              <span className="min-w-0 truncate font-mono font-bold text-cyan-600" title={exibirProtocolo(chat?.protocolo)}>
                {exibirProtocolo(chat?.protocolo)}
              </span>
              <span className="text-slate-300">•</span>
              <span className={classeCorEstadoChat(chat?.estado ?? '')}>
                {chat ? rotuloEstadoChat(chat.estado) : '—'}
              </span>
              {chat && (
                <>
                  <span className="text-slate-300">•</span>
                  <span className="max-w-[10rem] truncate text-slate-600 sm:max-w-none dark:text-slate-300">
                    {rotuloResponsavelChat(chat, user?.id)}
                  </span>
                  {chat.setor_nome && (
                    <>
                      <span className="text-slate-300">•</span>
                      <span className="max-w-[10rem] truncate text-slate-500 dark:text-slate-400">
                        {chat.setor_nome}
                      </span>
                    </>
                  )}
                </>
              )}
            </div>

            {ticketsVinculados.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {ticketsVinculados.map((t) => (
                  <Link
                    key={t.id}
                    to={TICKETS_PATH}
                    onClick={() => marcarTicketAtivo(t.id)}
                    className="inline-flex rounded-full border border-cyan-200/80 bg-cyan-50 px-2 py-0.5 text-[10px] font-medium text-cyan-800 dark:border-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300"
                    title={t.assunto}
                  >
                    {exibirProtocolo(t.protocolo)}
                  </Link>
                ))}
              </div>
            )}

            {chat?.funcionario_rede_id && (
              <div className="flex flex-wrap items-center gap-1.5">
                <Link
                  to={`/funcionarios-rede/${chat.funcionario_rede_id}`}
                  className="inline-flex max-w-full truncate rounded-full border border-violet-200/80 bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-800 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-300"
                  title={chat.funcionario_email ?? undefined}
                >
                  {chat.funcionario_nome}
                  {chat.funcionario_tipo ? ` · ${chat.funcionario_tipo}` : ''}
                </Link>
                {chat.empresa_nome && chat.empresa_id ? (
                  <Link
                    to={`/empresas/${chat.empresa_id}`}
                    state={{ voltarPara: `${location.pathname}${location.search}` }}
                    className="inline-flex max-w-full truncate rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-700 transition-colors hover:border-cyan-400 hover:text-cyan-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-cyan-600 dark:hover:text-cyan-300"
                    title="Ver detalhe da empresa"
                  >
                    {chat.empresa_nome}
                  </Link>
                ) : podeDefinirEmpresa ? (
                  <button
                    type="button"
                    onClick={abrirModalEmpresaContexto}
                    className="inline-flex rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-800 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                  >
                    Definir empresa
                  </button>
                ) : (
                  <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
                    Sem empresa
                  </span>
                )}
              </div>
            )}

          </div>

        </header>

        {chat && !chat.funcionario_rede_id && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-950 dark:border-violet-900/40 dark:bg-violet-950/30 dark:text-violet-100">
            <p>{CONTATO_CLIENTE.bannerNaoVinculado}</p>
            <Button variant="primary" className="h-8 shrink-0 text-xs" onClick={() => setModalVincFuncionario(true)}>
              {CONTATO_CLIENTE.vincularEmpresa}
            </Button>
          </div>
        )}

        {precisaEmpresaContexto && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100">
            <p>
              Este contacto pertence a mais de uma empresa. Pergunte ao cliente qual empresa deseja
              atendimento e vincule quando souber — pode fazer isso a qualquer momento antes de
              encerrar.
            </p>
            <Button variant="primary" className="h-8 shrink-0 text-xs" onClick={abrirModalEmpresaContexto}>
              Definir empresa
            </Button>
          </div>
        )}

        {mostrarBannerDemandaInatividade && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100">
            <p>
              Atendimento encerrado por inatividade. Reler a conversa se precisar e{' '}
              <strong>registar a demanda</strong> desta sessão.
            </p>
            <Button
              variant="primary"
              className="h-8 shrink-0 text-xs"
              onClick={() => setModalEncerrar(true)}
            >
              Registar demanda
            </Button>
          </div>
        )}

        {!encerrado && chat?.estado === 'em_atendimento' && !isResponsavel && (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100">
            {isAdmin ? (
              <>
                Modo acompanhamento (administrador): chat com{' '}
                <strong>{chat.atendente_nome || 'outro atendente'}</strong>. Mensagens ao cliente
                ficam bloqueadas — use comentário interno.
              </>
            ) : (
              <>
                Este chat está com <strong>{chat.atendente_nome || 'outro atendente'}</strong>.
                Você pode acompanhar em modo interno; mensagens ao cliente ficam bloqueadas.
              </>
            )}
          </div>
        )}



        {chat && chat.estado === 'em_atendimento' && (
          <div className={detalhesMobileAbertos ? '' : 'hidden md:block'}>
            <WhatsappDemandasPanel
              key={chat.id}
              chatId={chat.id}
              podeRegistrar={isResponsavel || isAdmin}
              onDemandasChange={refrescarTimelineDemandas}
            />
          </div>
        )}



        {/* Mensagens (Feed) */}

        <div

          ref={scrollRef}

          className="flex-1 overflow-y-auto p-4 space-y-4 relative bg-[#efeae2] dark:bg-slate-900/60"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(0,0,0,0.03) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}

        >

          {mergeTimelineChat(msgs, demandasTimeline).map((item) => {
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
                    {m.atendente_nome && (
                      <p className="mt-0.5 text-[10px] text-violet-700/80 dark:text-violet-300/80">
                        {m.atendente_nome}
                        {m.created_at
                          ? ` · ${new Date(m.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`
                          : ''}
                      </p>
                    )}
                  </div>
                </div>
              )
            }

            const isInbound = m.direcao === 'inbound'

            const isSystem =
              m.evento_sistema === 'comentario_interno' || m.evento_sistema === 'transferencia'
            const isTransferencia = m.evento_sistema === 'transferencia'

           

            return (

              <div 
                key={m.id} 
                id={`msg-${m.wa_message_id || m.id}`}
                data-wa-msg-id={m.id}
                onDoubleClick={(e) => duploCliqueResponder(e, m, isSystem)}
                className={`flex w-full group cursor-default items-center gap-2 transition-all ${isInbound ? 'justify-start' : 'justify-end'}`}
              >
                {!isInbound && !isSystem && !m.apagada && (
                  <button
                    onClick={() => iniciarResposta(m)}
                    className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full p-1.5 text-slate-400 opacity-100 transition-opacity hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200 md:h-auto md:w-auto md:opacity-0 md:group-hover:opacity-100"
                    title="Responder"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>
                  </button>
                )}

                <div
                  className={`relative max-w-[85%] space-y-1 sm:max-w-[70%] ${isInbound ? 'items-start' : 'items-end'}`}
                >

                  {isSystem && (
                    <span className="text-[9px] font-bold uppercase px-2 text-amber-600">
                      {isTransferencia ? '↪ Transferência' : '🔒 Interno'}
                    </span>
                  )}

                  <div
                    data-msg-bubble
                    className={`

                    rounded-2xl px-4 py-2 text-sm shadow-sm relative group/bubble

                    ${isSystem ? 'bg-amber-50 text-amber-900 border border-amber-100 dark:bg-amber-950/30 dark:text-amber-200 dark:border-amber-900/50' :

                      isInbound ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-tl-none ring-1 ring-slate-100 dark:ring-slate-700 pr-8' :

                      'bg-cyan-600 text-white rounded-tr-none pr-8'}

                  `}>

                    {!isSystem && !m.apagada && (
                      <WhatsappMensagemAcoes
                        mensagem={m}
                        onEditar={!isInbound ? (texto) => editarMensagemWhatsapp(m, texto) : undefined}
                        onApagar={!isInbound ? () => apagarMensagemWhatsapp(m) : undefined}
                        podeReagir={podeReagir}
                        onReagirMenu={podeReagir ? () => setReagirMsgId(m.id) : undefined}
                        tomClaro={isInbound}
                      />
                    )}

                    {m.is_forwarded && !m.apagada && (
                      <p
                        className={`mb-1 flex items-center gap-1 text-[11px] italic ${
                          isInbound ? 'text-slate-400 dark:text-slate-500' : 'text-white/80'
                        }`}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="12"
                          height="12"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden
                          className="shrink-0 opacity-80"
                        >
                          <path d="m15 17 5-5-5-5" />
                          <path d="M4 18v-2a4 4 0 0 1 4-4h12" />
                        </svg>
                        {(m.forwarding_score ?? 0) >= 127
                          ? 'Encaminhada muitas vezes'
                          : 'Encaminhada'}
                      </p>
                    )}

                    {m.quoted_wa_message_id && !m.apagada && (
                      <div 
                        onClick={() => {
                          const el = document.getElementById(`msg-${m.quoted_wa_message_id}`);
                          if (el) {
                            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            el.classList.add('bg-cyan-100/50', 'dark:bg-cyan-950/30');
                            setTimeout(() => {
                              el.classList.remove('bg-cyan-100/50', 'dark:bg-cyan-950/30');
                            }, 1500);
                          }
                        }}
                        className={`mb-2 rounded border-l-4 p-2 text-xs cursor-pointer hover:bg-black/5 transition-colors
                          ${isInbound 
                            ? 'bg-slate-100 dark:bg-slate-900 border-cyan-600 text-slate-600 dark:text-slate-300' 
                            : 'bg-black/10 border-white text-slate-100'}`}
                      >
                        <p className={`font-bold text-[10px] ${isInbound ? 'text-cyan-600 dark:text-cyan-400' : 'text-white'}`}>
                          Mensagem Citada
                        </p>
                        <p className="truncate max-w-xs">{m.quoted_corpo_preview || 'Mídia'}</p>
                      </div>
                    )}

                    <ConteudoMensagemWhatsApp
                      chatId={id}
                      m={m}
                      onImageClick={(msgId) => setZoomMsgId(msgId)}
                      onVideoClick={(msgId) => setVideoZoomMsgId(msgId)}
                    />

                    {!isSystem && (
                      <MensagemRodapeMeta
                        hora={m.created_at}
                        status={m.status_entrega}
                        direcao={m.direcao}
                        eventoSistema={m.evento_sistema}
                        variant={isInbound ? 'escuro' : 'claro'}
                        editada={m.editada}
                        className={isInbound ? 'text-slate-400' : ''}
                      />
                    )}

                  </div>

                  {!isSystem && !m.apagada && (
                    <WhatsappReacoesBar
                      reacoes={m.reacoes || []}
                      podeReagir={podeReagir}
                      onReagir={podeReagir ? (emoji) => void reagirMensagem(m, emoji) : undefined}
                      alinhamento={isInbound ? 'start' : 'end'}
                      pickerExternoAberto={reagirMsgId === m.id}
                      onPickerExternoClose={() => setReagirMsgId(null)}
                    />
                  )}

                </div>

                {isInbound && !isSystem && !m.apagada && (
                  <button
                    onClick={() => iniciarResposta(m)}
                    className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full p-1.5 text-slate-400 opacity-100 transition-opacity hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200 md:h-auto md:w-auto md:opacity-0 md:group-hover:opacity-100"
                    title="Responder"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>
                  </button>
                )}

              </div>

            )

          })}

        </div>



        {/* Footer: Input & Mídia */}

        <footer className="shrink-0 border-t border-slate-100 bg-white p-3 dark:border-slate-800 dark:bg-slate-950 sm:p-4 [:is(html[data-vv-keyboard='0'])_&]:pb-[max(0.75rem,env(safe-area-inset-bottom))]">

          {msgRespondida && (
            <div className="flex items-center justify-between bg-slate-100 dark:bg-slate-900 border-l-4 border-cyan-600 px-4 py-2 rounded-t-xl mb-1 text-xs animate-in slide-in-from-bottom-2 duration-150">
              <div className="min-w-0 flex-1">
                <p className="font-bold text-cyan-600 dark:text-cyan-400">
                  {msgRespondida.direcao === 'inbound' ? (chat?.cliente_nome || 'Cliente') : (msgRespondida.atendente_nome || 'Você')}
                </p>
                <p className="truncate text-slate-600 dark:text-slate-300">
                  {msgRespondida.tipo_midia && msgRespondida.tipo_midia !== 'texto' 
                    ? `📷 [${msgRespondida.tipo_midia.charAt(0).toUpperCase() + msgRespondida.tipo_midia.slice(1)}]` 
                    : msgRespondida.corpo}
                </p>
              </div>
              <button 
                onClick={() => setMsgRespondida(null)} 
                className="ml-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg font-bold w-6 h-6 rounded-full flex items-center justify-center hover:bg-slate-200 dark:hover:bg-slate-800 cursor-pointer"
              >
                &times;
              </button>
            </div>
          )}

          {modoInterno && (
            <p className="mb-2 text-sm text-amber-600">
              Este chat pertence a outro atendente. A mensagem será registrada como comentário interno e não será enviada ao cliente.
            </p>
          )}

          {!encerrado && !modoInterno && !podeEnviar && (
            <p className="mb-2 text-[11px] text-amber-800 dark:text-amber-200">{motivoAnexoDesabilitado}</p>
          )}

          {arquivoPendente && (
            <div
              className="mb-2 rounded-xl border border-cyan-200 bg-cyan-50/80 p-3 dark:border-cyan-900/40 dark:bg-cyan-950/20"
              tabIndex={arquivoPendente.type.startsWith('audio/') ? 0 : undefined}
              onKeyDown={
                arquivoPendente.type.startsWith('audio/')
                  ? (e) => {
                      if (e.key === 'Enter' && !e.shiftKey && !enviando && podeEnviar) {
                        e.preventDefault()
                        e.stopPropagation()
                        void confirmarEnvioMidia()
                      }
                    }
                  : undefined
              }
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
                    if (e.key !== 'Enter' || e.shiftKey) return
                    if (!window.matchMedia('(min-width: 768px)').matches) return
                    e.preventDefault()
                    e.stopPropagation()
                    if (!enviando && podeEnviar) void confirmarEnvioMidia()
                  }}
                  placeholder="Legenda opcional (visível no WhatsApp)"
                  className={`mt-2 ${TEXTAREA_FIELD_CLASS}`}
                  autoFocus
                />
              )}
              <div className="mt-2 flex justify-end gap-2">
                <Button
                  variant="ghost"
                  className="h-8 text-xs"
                  onClick={() => {
                    setArquivoPendente(null)
                    setLegendaMidia('')
                  }}
                >
                  Cancelar
                </Button>
                <Button className="h-8 text-xs" loading={enviando} onClick={() => void confirmarEnvioMidia()}>
                  Enviar anexo
                </Button>
              </div>
            </div>
          )}

          {!arquivoPendente ? (
            <WhatsappComposerBar
              texto={texto}
              onTextoChange={setTexto}
              onEnviar={() => void enviar()}
              enviando={enviando}
              encerrado={encerrado}
              podeEnviar={podeEnviar}
              modoInterno={modoInterno}
              podeDigitar={podeDigitarMensagem}
              onEscolherAnexo={abrirPickerAnexo}
              onAudioGravado={handleGravacaoConcluida}
              onInserirEmoji={setTexto}
              onEnviarFigurinha={(file) => void enviarFigurinha(file)}
              onColarArquivo={(file) => {
                setArquivoPendente(file)
                setLegendaMidia('')
              }}
              setorId={chat?.setor_id}
              onInserirReferenciaKb={inserirReferenciaKb}
              focoPedidoEm={focoComposerEm}
              placeholder={composerPlaceholder}
            />
          ) : null}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelecionado}
            className="hidden"
            accept={ACCEPT_ANEXO[pickerAnexo]}
          />
        </footer>

      </main>



      {/* Modais (Vincular exemplo) */}

      {modalTransferir && (
  <div className="fixed inset-0 z-[100] flex items-end justify-center bg-slate-900/50 p-0 backdrop-blur-sm md:items-center md:p-4">
    <Card className="max-h-[min(92dvh,var(--vv-height,92dvh))] w-full max-w-lg overflow-y-auto rounded-b-none p-6 md:rounded-2xl">
      <h3 className="text-lg font-bold">Transferir Atendimento</h3>
      {chat && (
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Responsável atual: <strong>{rotuloResponsavelChat(chat, user?.id)}</strong>
          {chat.setor_nome ? ` • Setor ${chat.setor_nome}` : ''}
        </p>
      )}

      <div className="mt-4 space-y-4">

        {/* SETOR */}
        <Select
  value={transferSetorId === '' ? '' : transferSetorId}
  onChange={(v) => {
    const n = v === '' ? '' : Number(v)
    setTransferSetorId(n)
    setTransferAtendenteId('')
  }}
  includeEmpty
  emptyLabel="Selecione o setor"
  options={setoresList.map((s) => ({
    value: s.id,
    label: s.nome,
  }))}
/>

        {/* ATENDENTE */}
        <Select
  value={transferAtendenteId === '' ? '' : transferAtendenteId}
  onChange={(v) =>
    setTransferAtendenteId(v === '' ? '' : Number(v))
  }
  includeEmpty
  emptyLabel="Deixar na fila"
  disabled={!transferSetorId || atendentesDestino.length === 0}
  options={atendentesDestino.map((a) => ({
    value: a.id,
    label: a.nome,
  }))}
/>

        {erroAtendentesDestino && (
          <p className="text-xs text-amber-500">
            Sem permissão para escolher atendente neste setor.
          </p>
        )}
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={() => setModalTransferir(false)} variant="secondary">
          Cancelar
        </Button>

        <Button onClick={() => void transferirChat()} loading={transferindo}>
          Transferir
        </Button>
      </div>
    </Card>
  </div>
)}

        {modalVincFuncionario && chat && (
          <WhatsappVincFuncionarioModal
            chat={chat}
            open={modalVincFuncionario}
            onClose={() => setModalVincFuncionario(false)}
            onSuccess={aplicarChatAtualizado}
          />
        )}

        {modalEmpresaContexto && chat && (
          <ChatBottomSheet
            open={modalEmpresaContexto}
            title="Empresa do atendimento"
            onClose={() => {
              setModalEmpresaContexto(false)
              setEmpresaContextoId('')
            }}
            zClassName="z-[120]"
          >
            <p className="mb-4 text-sm text-slate-500">
              Vincule a empresa que o cliente indicou. Pode alterar enquanto o chat não estiver
              encerrado.
            </p>
            <SelectComPesquisa
              label="Empresa"
              value={empresaContextoId}
              onChange={(id) => setEmpresaContextoId(id)}
              items={(chat.empresas_opcoes || []).map((e) => ({ id: e.id, label: e.nome }))}
              placeholder="Selecione a empresa"
              hint="Digite parte do nome do posto"
              required
            />
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="ghost"
                disabled={salvandoEmpresaContexto}
                onClick={() => {
                  setModalEmpresaContexto(false)
                  setEmpresaContextoId('')
                }}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                loading={salvandoEmpresaContexto}
                disabled={empresaContextoId === ''}
                onClick={() => void confirmarEmpresaContexto()}
              >
                Confirmar
              </Button>
            </div>
          </ChatBottomSheet>
        )}

      {chat && (
        <WhatsappTicketsModal
          chat={chat}
          open={modalTickets}
          onClose={() => setModalTickets(false)}
          onSuccess={(atualizado) => {
            aplicarChatAtualizado(atualizado)
            refrescarTimelineDemandas()
          }}
        />
      )}

      {chat && (
        <WhatsappEncerrarModal
          open={modalEncerrar}
          chatId={chat.id}
          chatEstado={chat.estado}
          msgs={msgs}
          onClose={() => setModalEncerrar(false)}
          onEncerrado={(atualizado) => void handleEncerrado(atualizado)}
          onDemandasChange={refrescarTimelineDemandas}
        />
      )}

      {zoomMsgId != null && (
        <WhatsappZoomLightbox
          chatId={id}
          msgs={msgs}
          zoomMsgId={zoomMsgId}
          onClose={() => setZoomMsgId(null)}
          onChangeMsgId={setZoomMsgId}
        />
      )}

      {videoZoomMsgId != null && (
        <WhatsappVideoLightbox
          chatId={id}
          msgId={videoZoomMsgId}
          caption={
            (() => {
              const m = msgs.find((x) => x.id === videoZoomMsgId)
              return m ? legendaMidiaVisivel(m.corpo) : null
            })()
          }
          onClose={() => setVideoZoomMsgId(null)}
        />
      )}

      {fotoPerfilAberta && chat?.foto_perfil_url ? (
        <WhatsappFotoPerfilLightbox
          src={chat.foto_perfil_url}
          nome={chat.cliente_nome}
          onClose={() => setFotoPerfilAberta(false)}
        />
      ) : null}

      <AssumirWhatsappSetorModal
        open={modalAssumirSetor}
        setorIds={user?.setor_ids || []}
        loading={assumindo}
        onClose={() => setModalAssumirSetor(false)}
        onConfirm={(setorId) => void executarAssumirChat(setorId)}
      />

      {modoHub && (
        <ChatFilaAguardandoSheet
          open={filaAguardandoAberta}
          onClose={() => setFilaAguardandoAberta(false)}
        />
      )}
      
    </div>

      
  )

}