import { useCallback, useEffect, useState, useRef } from 'react'

import { Link, useNavigate, useParams } from 'react-router-dom'

import {


  atendentes,
  tickets,
  whatsappChats,

  fetchWhatsAppMidiaBlob,


  type Setores,

  type Atendentes,

  type Tickets,
  type WhatsappChats,

} from '../../api/client'

import { Card } from '../../components/ui/Card'

import { Button } from '../../components/ui/Button'

import { Select } from '../../components/ui/Select'

import { useToast } from '../../components/ui/Toast'

import { mensagemFalhaParaToast } from '../../api/errorMessage'

import { exibirProtocolo } from '../../lib/exibirProtocolo'

import { useAuth } from '../../contexts/AuthContext'
import { useEventStream } from '../../contexts/EventStreamContext'
import { refetchPendenciasResumo } from '../../hooks/useAlertaFilaSemResponsavel'
import { CustomAudioPlayer } from '../../components/CustomAudioPlayer'
import {
  mensagemTransferenciaSucesso,
  rotuloEstadoChat,
  rotuloResponsavelChat,
} from '../../lib/whatsappChatMeta'
import { WhatsappTicketsModal } from './WhatsappTicketsModal'
import { WhatsappVincFuncionarioModal } from './WhatsappVincFuncionarioModal'

const ROTULO_SEM_LEGENDA = /^\[(Imagem|Áudio|Vídeo|Documento|Figurinha)\]$/



// --- Subcomponente de Renderização de Mídia ---

function ConteudoMensagemWhatsApp({ chatId, m, onImageClick }: { chatId: number; m: WhatsappChats.Mensagem; onImageClick: (url: string, caption: string | null) => void }) {

  const tipo = (m.tipo_midia || 'texto').toLowerCase()

  const [url, setUrl] = useState<string | null>(null)

  const [loading, setLoading] = useState(false)

  const [err, setErr] = useState(false)



  useEffect(() => {

    if (!m.midia_disponivel || tipo === 'texto') {

      setUrl(null)

      return

    }

    let objectUrl: string | null = null

    let cancelled = false

    setLoading(true)

    fetchWhatsAppMidiaBlob(chatId, m.id)

      .then((blob) => {

        if (cancelled) return

        const u = URL.createObjectURL(blob)

        objectUrl = u

        setUrl(u)

      })

      .catch(() => { if (!cancelled) setErr(true) })

      .finally(() => { if (!cancelled) setLoading(false) })

    return () => {

      cancelled = true

      if (objectUrl) URL.revokeObjectURL(objectUrl)

    }

  }, [chatId, m.id, m.midia_disponivel, tipo])



  const legenda = m.corpo && !ROTULO_SEM_LEGENDA.test(m.corpo.trim()) ? m.corpo : null



  if (tipo === 'texto' || !m.tipo_midia) return <p className="whitespace-pre-wrap">{m.corpo}</p>

  if (loading || !url) return <p className="text-[10px] animate-pulse opacity-50">Carregando mídia...</p>

  if (err) return <p className="text-[10px] italic opacity-50">Erro ao carregar mídia</p>



  const mediaClass = "max-h-64 max-w-full rounded-lg border border-black/5 shadow-sm"



  if (tipo === 'imagem' || tipo === 'figurinha') {

    return (

      <div className="space-y-1">

        <img 

          src={url} 

          alt="" 

          className={`${mediaClass} cursor-zoom-in transition-transform duration-200 hover:scale-[1.02]`} 

          onClick={() => onImageClick(url, legenda)}

        />

        {legenda && <p className="text-xs opacity-80 italic">{legenda}</p>}

      </div>

    )

  }

  if (tipo === 'audio') return <CustomAudioPlayer src={url} />

  if (tipo === 'video') return <video controls src={url} className={mediaClass} />

 

  const downloadLabel = {
    documento: '📄 Baixar Documento',
    audio: '🔊 Baixar Áudio',
    video: '🎬 Baixar Vídeo',
    imagem: '📷 Baixar Imagem',
    figurinha: '📷 Baixar Imagem',
  }[tipo] || `📄 Baixar ${tipo || 'Ficheiro'}`

  return (

    <a href={url} download className="flex items-center gap-2 text-xs font-bold underline">
      <span>{downloadLabel.split(' ')[0]}</span> {downloadLabel.replace(/^\S+\s*/, '')}
    </a>

  )

}



// --- Componente Principal ---

export function WhatsappConversa() {

  const { chatId } = useParams<{ chatId: string }>()

  const id = Number(chatId)

  const toast = useToast()

  const { user } = useAuth()
  const { subscribe, useFallback } = useEventStream()

 

  // Refs

  const scrollRef = useRef<HTMLDivElement>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)



  // Estados de Dados

  const [chat, setChat] = useState<WhatsappChats.Chat | null>(null)

  const [msgs, setMsgs] = useState<WhatsappChats.Mensagem[]>([])

  const [meusChats, setMeusChats] = useState<WhatsappChats.Chat[]>([])

 

  // Estados de UI

  const [sidebarAberta, setSidebarAberta] = useState(true)

  const [loading, setLoading] = useState(true)

  const [texto, setTexto] = useState('')

  const [enviando, setEnviando] = useState(false)
  const [encerrando, setEncerrando] = useState(false)

  // Estados de WhatsApp Clone (Citação e Zoom)
  const [msgRespondida, setMsgRespondida] = useState<WhatsappChats.Mensagem | null>(null)
  const [activeZoomImage, setActiveZoomImage] = useState<string | null>(null)
  const [activeZoomImageCaption, setActiveZoomImageCaption] = useState<string | null>(null)
  const [modoInterno, setModoInterno] = useState(false)

  // Transferência
  const [modalTransferir, setModalTransferir] = useState(false)
  const [transferSetorId, setTransferSetorId] = useState<number | ''>('')
  const [transferAtendenteId, setTransferAtendenteId] = useState<number | ''>('')
  const [transferindo, setTransferindo] = useState(false)
  const [modalVincFuncionario, setModalVincFuncionario] = useState(false)

  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [atendentesDestino, setAtendentesDestino] = useState<Atendentes.Atendente[]>([])
  const [erroAtendentesDestino, setErroAtendentesDestino] = useState<string | null>(null)

  // Modais (Vincular/Transferir/Abrir)

  const [modalTickets, setModalTickets] = useState(false)
  const [ticketsVinculados, setTicketsVinculados] = useState<Tickets.Ticket[]>([])
  const navigate = useNavigate()



  // Auto-scroll para o fim

  useEffect(() => {

    if (scrollRef.current) {

      scrollRef.current.scrollTop = scrollRef.current.scrollHeight

    }

  }, [msgs])



  // Carregar lista de chats lateral

  const carregarSidebar = useCallback(async () => {

    try {

      const rows = await whatsappChats.meus()

      setMeusChats(rows)

    } catch { setMeusChats([]) }

  }, [])



  // Carregar conversa e mensagens

  const carregar = useCallback(async () => {

    if (!id) return

    try {

      const [c, m] = await Promise.all([whatsappChats.get(id), whatsappChats.mensagens(id)])

      setChat(c)

      setMsgs(m)

    } catch (err) {

      toast.showError(mensagemFalhaParaToast(err))

    }

  }, [id, toast])



  useEffect(() => {

    void carregarSidebar()

  }, [carregarSidebar])



  useEffect(() => {

    if (!id) return

    setLoading(true)

    carregar().then(() => whatsappChats.marcarVisto(id)).finally(() => setLoading(false))

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
    if (!id) return
    const chatId = Number(id)
    const unsubMsg = subscribe('chat.mensagem', (payload) => {
      if (Number(payload.chat_id) !== chatId) return
      const msg = payload.mensagem as WhatsappChats.Mensagem | undefined
      if (!msg) return
      setMsgs((prev) => {
        if (prev.some((m) => m.id === msg.id)) return prev
        if (msg.wa_message_id && prev.some((m) => m.wa_message_id === msg.wa_message_id)) return prev
        return [...prev, msg]
      })
    })
    const unsubFila = subscribe('chat.fila', (payload) => {
      const payloadChatId = Number(payload.chat_id)
      const chatData = payload.chat as WhatsappChats.Chat | undefined
      if (payloadChatId === chatId) {
        if (chatData) setChat(chatData)
        else void carregar().catch(() => {})
      }
      if (chatData && chatData.estado !== 'em_atendimento') {
        setMeusChats((prev) => prev.filter((c) => c.id !== payloadChatId))
      } else {
        void carregarSidebar()
      }
    })
    return () => {
      unsubMsg()
      unsubFila()
    }
  }, [id, subscribe, carregar, carregarSidebar])

  // Polling legado quando SSE indisponível
  useEffect(() => {
    if (!useFallback) return
    if (!chat || chat.estado === 'encerrado' || chat.estado === 'aguardando_avaliacao') return
    const t = setInterval(() => void carregar().catch(() => {}), 5000)
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


  // --- Ações ---

  async function enviar() {

    if (!chat || !texto.trim() || enviando || (!modoInterno && !podeEnviar)) return

    setEnviando(true)

    try {
      if (modoInterno) {
        await whatsappChats.comentarInterno(chat.id, texto.trim())
        toast.showSuccess('Comentário interno registrado.')
      } else {
        await whatsappChats.enviar(chat.id, texto.trim(), msgRespondida?.wa_message_id || null)
        toast.showSuccess('Mensagem enviada.')
      }

      setTexto('')
      setMsgRespondida(null)

      await carregar()

    } catch (err) {

      toast.showError(mensagemFalhaParaToast(err))

    } finally { setEnviando(false) }

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
      navigate('/whatsapp/atendendo')
    }
  } catch (err) {
    toast.showWarning(
      mensagemFalhaParaToast(err, 'Não foi possível transferir o chat.')
    )
  } finally {
    setTransferindo(false)
  }
}

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {

    const file = e.target.files?.[0]

    if (!file || !chat || !podeEnviar) return

   

    setEnviando(true)

    try {

      await whatsappChats.enviarMidia(chat.id, file, '', msgRespondida?.wa_message_id || null)

      setMsgRespondida(null)

      toast.showSuccess('Arquivo enviado!')

      await carregar()

    } catch (err) {

      toast.showError(mensagemFalhaParaToast(err, 'Falha no envio do arquivo'))

    } finally {

      setEnviando(false)

      if (fileInputRef.current) fileInputRef.current.value = ''

    }

  }



  async function encerrar() {

    if (!chat || !confirm('Encerrar este atendimento?')) return

    setEncerrando(true)

    try {

      const atualizado = await whatsappChats.encerrar(chat.id)

      await Promise.all([carregar(), carregarSidebar()])

      toast.showSuccess(
        atualizado.estado === 'aguardando_avaliacao'
          ? 'Atendimento encerrado. Aguardando avaliação do cliente.'
          : 'Atendimento encerrado.',
      )

    } finally { setEncerrando(false) }

  }



  if (loading && !chat) return <div className="flex h-full items-center justify-center italic text-slate-400">Carregando workspace...</div>



  const encerrado = chat?.estado === 'encerrado' || chat?.estado === 'aguardando_avaliacao'

  const isResponsavel = chat?.atendente_id === user?.id
  const isAdmin = user?.role === 'admin'

  const podeTransferir = !encerrado && (isResponsavel || isAdmin)

  const podeEnviar = chat?.estado === 'em_atendimento' && isResponsavel && !encerrado

  const podeEncerrar = !encerrado && chat?.estado === 'em_atendimento' && (isResponsavel || isAdmin)



  return (

    <div className="flex h-[calc(100vh-140px)] min-h-[500px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-950">

     

      {/* SIDEBAR RECOLHÍVEL */}

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

              to={`/whatsapp/c/${c.id}`}

              className={`flex items-center p-4 gap-3 transition-colors ${c.id === id ? 'bg-white shadow-sm dark:bg-slate-800' : 'hover:bg-white/40 dark:hover:bg-slate-900/50'}`}

            >

              <div className={`h-8 w-8 shrink-0 rounded-full flex items-center justify-center text-xs font-bold shadow-sm

                ${c.id === id ? 'bg-cyan-600 text-white' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}`}>

                {c.cliente_nome?.charAt(0) || '?'}

              </div>

              {sidebarAberta && (

                <div className="min-w-0 flex-1">

                  <div className="flex justify-between items-center">

                    <p className="truncate text-sm font-bold text-slate-800 dark:text-slate-100">{c.cliente_nome || 'Cliente'}</p>

                    {c.estado === 'aguardando_atendente' && <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />}

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



      {/* ÁREA DE CONVERSA */}

      <main className="flex flex-1 flex-col min-w-0 bg-white dark:bg-slate-950">

       

        {/* Header do Chat */}

        <header className="flex h-16 items-center justify-between border-b border-slate-100 px-4 dark:border-slate-800 shadow-sm z-10">

          <div className="flex items-center gap-3 min-w-0">

            <div className="min-w-0">

              <h1 className="truncate font-bold text-slate-900 dark:text-white">{chat?.cliente_nome || 'Atendimento'}</h1>

              <div className="flex flex-wrap items-center gap-2 text-[10px]">

                <span className="min-w-0 truncate font-mono font-bold text-cyan-600" title={exibirProtocolo(chat?.protocolo)}>
                  {exibirProtocolo(chat?.protocolo)}
                </span>

                <span className="text-slate-300">•</span>

                <span className={`capitalize ${encerrado ? 'text-red-500' : 'text-emerald-500'}`}>
                  {chat ? rotuloEstadoChat(chat.estado) : '—'}
                </span>

                {chat && (
                  <>
                    <span className="text-slate-300">•</span>
                    <span className="truncate text-slate-600 dark:text-slate-300">
                      Responsável: {rotuloResponsavelChat(chat, user?.id)}
                    </span>
                    {chat.setor_nome && (
                      <>
                        <span className="hidden sm:inline text-slate-300">•</span>
                        <span className="hidden sm:inline truncate text-slate-500 dark:text-slate-400">
                          {chat.setor_nome}
                        </span>
                      </>
                    )}
                  </>
                )}

              </div>

              {ticketsVinculados.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {ticketsVinculados.map((t) => (
                    <Link
                      key={t.id}
                      to={`/tickets/${t.id}`}
                      className="inline-flex rounded-full border border-cyan-200/80 bg-cyan-50 px-2 py-0.5 text-[10px] font-medium text-cyan-800 dark:border-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300"
                      title={t.assunto}
                    >
                      {exibirProtocolo(t.protocolo)}
                    </Link>
                  ))}
                </div>
              )}

              {chat?.funcionario_rede_id && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <Link
                    to={`/funcionarios-rede/${chat.funcionario_rede_id}`}
                    className="inline-flex rounded-full border border-violet-200/80 bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-800 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-300"
                    title={chat.funcionario_email ?? undefined}
                  >
                    {chat.funcionario_nome}
                    {chat.funcionario_tipo ? ` · ${chat.funcionario_tipo}` : ''}
                  </Link>
                  {chat.empresa_nome && (
                    <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                      {chat.empresa_nome}
                    </span>
                  )}
                </div>
              )}

            </div>

          </div>



          <div className="flex items-center gap-2">

             {!encerrado && (

              <>

              {podeTransferir && (
              <Button
  variant="primary"
  className="hidden sm:inline-flex text-xs h-8"
  onClick={() => setModalTransferir(true)}
>
  Transferir
</Button>
              )}
              <Button
                variant="ghost"
                className="hidden sm:inline-flex text-xs h-8"
                onClick={() => setModalVincFuncionario(true)}
              >
                Vincular funcionário
              </Button>

                <Button variant="ghost" className="hidden sm:inline-flex text-xs h-8" onClick={() => setModalTickets(true)}>
                  Tickets{ticketsVinculados.length > 0 ? ` (${ticketsVinculados.length})` : ''}
                </Button>

                {podeEncerrar && (

                  <Button variant="danger" className="h-8 px-3 text-xs" onClick={() => void encerrar()} loading={encerrando}>Encerrar</Button>

                )}

              </>

            )}

          </div>

        </header>

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



        {/* Mensagens (Feed) */}

        <div

          ref={scrollRef}

          className="flex-1 overflow-y-auto p-4 space-y-4 relative bg-[#efeae2] dark:bg-slate-900/60"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(0,0,0,0.03) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}

        >

          {msgs.map((m) => {

            const isInbound = m.direcao === 'inbound'

            const isSystem =
              m.evento_sistema === 'comentario_interno' || m.evento_sistema === 'transferencia'
            const isTransferencia = m.evento_sistema === 'transferencia'

           

            return (

              <div 
                key={m.id} 
                id={`msg-${m.wa_message_id || m.id}`}
                className={`flex w-full group items-center gap-2 transition-all ${isInbound ? 'justify-start' : 'justify-end'}`}
              >
                {!isInbound && !isSystem && (
                  <button
                    onClick={() => setMsgRespondida(m)}
                    className="opacity-25 group-hover:opacity-100 md:opacity-0 transition-opacity p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer shrink-0"
                    title="Responder"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>
                  </button>
                )}

                <div className={`max-w-[85%] sm:max-w-[70%] space-y-1 ${isInbound ? 'items-start' : 'items-end'}`}>

                  {isSystem && (
                    <span className="text-[9px] font-bold uppercase px-2 text-amber-600">
                      {isTransferencia ? '↪ Transferência' : '🔒 Interno'}
                    </span>
                  )}

                 

                  <div className={`

                    rounded-2xl px-4 py-2 text-sm shadow-sm relative group/bubble

                    ${isSystem ? 'bg-amber-50 text-amber-900 border border-amber-100 dark:bg-amber-950/30 dark:text-amber-200 dark:border-amber-900/50' :

                      isInbound ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-tl-none ring-1 ring-slate-100 dark:ring-slate-700' :

                      'bg-cyan-600 text-white rounded-tr-none'}

                  `}>

                    {m.quoted_wa_message_id && (
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

                    <ConteudoMensagemWhatsApp chatId={id} m={m} onImageClick={(url, caption) => {
                      setActiveZoomImage(url)
                      setActiveZoomImageCaption(caption)
                    }} />

                  </div>

                 

                  <p className="text-[9px] text-slate-400 px-1 font-medium">

                    {!isInbound && m.atendente_nome ? `${m.atendente_nome} • ` : ''}

                    {m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}

                  </p>

                </div>

                {isInbound && !isSystem && (
                  <button
                    onClick={() => setMsgRespondida(m)}
                    className="opacity-25 group-hover:opacity-100 md:opacity-0 transition-opacity p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer shrink-0"
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

        <footer className="p-4 bg-white dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800">

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

          <div className="flex items-end gap-2 bg-slate-100 dark:bg-slate-900 p-2 rounded-2xl shadow-inner">

           

            {/* Input de arquivo invisível */}

            <input

              type="file"

              ref={fileInputRef}

              onChange={handleFileUpload}

              className="hidden"

              accept="image/*,video/*,application/pdf"

            />



            <Button

              variant="ghost"

              onClick={() => fileInputRef.current?.click()}

              disabled={enviando || encerrado || !podeEnviar}

              className="h-10 w-10 shrink-0 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"

            >

              📎

            </Button>



            <textarea

              value={texto}

              onChange={(e) => setTexto(e.target.value)}

              placeholder={
                encerrado
                  ? "Apenas leitura..."
                  : modoInterno
                    ? "Escreva um comentário interno..."
                    : podeEnviar
                      ? "Escreva uma mensagem..."
                      : "Somente comentários internos são permitidos."
              }

              rows={1}

              disabled={encerrado || (!modoInterno && !podeEnviar)}

              className="flex-1 max-h-32 min-h-[40px] resize-none border-none bg-transparent p-2 text-sm focus:ring-0 dark:text-slate-100 placeholder:text-slate-400"

              onKeyDown={(e) => {

                if (e.key === 'Enter' && !e.shiftKey) {

                  e.preventDefault()

                  void enviar()

                }

              }}

            />



            <Button

              onClick={() => void enviar()}

              disabled={
                enviando || !texto.trim() || encerrado || (!modoInterno && !podeEnviar)
              }

              className="h-10 w-10 shrink-0 rounded-xl bg-cyan-600 p-0 text-white shadow-lg shadow-cyan-600/30 hover:bg-cyan-700 disabled:opacity-50"

            >

              {enviando ? '...' : modoInterno ? '✎' : '➤'}

            </Button>

          </div>

        </footer>

      </main>



      {/* Modais (Vincular exemplo) */}

      {modalTransferir && (
  <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
    <Card className="w-full max-w-lg p-6">
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
            onSuccess={(atualizado) => setChat(atualizado)}
          />
        )}

      {chat && (
        <WhatsappTicketsModal
          chat={chat}
          open={modalTickets}
          onClose={() => setModalTickets(false)}
          onSuccess={(atualizado) => setChat(atualizado)}
        />
      )}

      {/* Modal Zoom de Imagem */}
      {activeZoomImage && (
        <div 
          className="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-black/90 backdrop-blur-sm p-4 animate-in fade-in duration-200"
          onClick={() => {
            setActiveZoomImage(null)
            setActiveZoomImageCaption(null)
          }}
        >
          <button 
            className="absolute top-4 right-4 text-white text-3xl font-bold bg-white/10 hover:bg-white/20 w-12 h-12 rounded-full flex items-center justify-center transition-colors touch-manipulation cursor-pointer"
            onClick={() => {
              setActiveZoomImage(null)
              setActiveZoomImageCaption(null)
            }}
          >
            &times;
          </button>
          <img 
            src={activeZoomImage} 
            alt="" 
            className="max-h-[85vh] max-w-full rounded-lg shadow-2xl object-contain animate-in zoom-in-95 duration-200" 
            onClick={(e) => e.stopPropagation()} 
          />
          {activeZoomImageCaption && (
            <p className="mt-4 text-white text-sm max-w-2xl text-center bg-black/40 px-4 py-2 rounded-xl backdrop-blur-md">
              {activeZoomImageCaption}
            </p>
          )}
          <a 
            href={activeZoomImage} 
            download="whatsapp-imagem.jpg" 
            className="absolute bottom-4 right-4 bg-cyan-600 hover:bg-cyan-700 text-white font-bold text-xs px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-cyan-600/30 transition-all hover:scale-105" 
            onClick={(e) => e.stopPropagation()}
          >
            📥 Baixar Imagem
          </a>
        </div>
      )}
      
    </div>

      
  )

}