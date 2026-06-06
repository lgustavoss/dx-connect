import { useCallback, useEffect, useState, useRef } from 'react'

import { Link, useParams } from 'react-router-dom'

import {


  atendentes,


  whatsappChats,

  fetchWhatsAppMidiaBlob,


  type Setores,

  type Atendentes,

  type WhatsappChats,

} from '../../api/client'

import { Card } from '../../components/ui/Card'

import { Button } from '../../components/ui/Button'

import { Input } from '../../components/ui/Input'

import { Select } from '../../components/ui/Select'

import { useToast } from '../../components/ui/Toast'

import { mensagemFalhaParaToast } from '../../api/errorMessage'

import { exibirProtocolo } from '../../lib/exibirProtocolo'

import { useAuth } from '../../contexts/AuthContext'
import { CustomAudioPlayer } from '../../components/CustomAudioPlayer'



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

 

  return (

    <a href={url} download className="flex items-center gap-2 text-xs font-bold underline">

      <span>📄</span> Baixar Documento

    </a>

  )

}



// --- Componente Principal ---

export function WhatsappConversa() {

  const { chatId } = useParams<{ chatId: string }>()

  const id = Number(chatId)

  const toast = useToast()

  const { user } = useAuth()

 

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

  // Transferência
  const [modalTransferir, setModalTransferir] = useState(false)
  const [transferSetorId, setTransferSetorId] = useState<number | ''>('')
  const [transferAtendenteId, setTransferAtendenteId] = useState<number | ''>('')
  const [transferindo, setTransferindo] = useState(false)

  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [atendentesDestino, setAtendentesDestino] = useState<Atendentes.Atendente[]>([])
  const [erroAtendentesDestino, setErroAtendentesDestino] = useState<string | null>(null)

  // Modais (Vincular/Transferir/Abrir)

  const [modalVinc, setModalVinc] = useState(false)

  const [ticketVincId, setTicketVincId] = useState('')



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



  // Polling para novas mensagens (a cada 5s)

  useEffect(() => {

    if (!chat || chat.estado === 'encerrado') return

    const t = setInterval(() => void carregar().catch(() => {}), 5000)

    return () => clearInterval(t)

  }, [chat, carregar])

//transferencia de atendente
useEffect(() => {
  if (!modalTransferir) return

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
}, [modalTransferir])

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

    if (!chat || !texto.trim() || enviando) return

    setEnviando(true)

    try {

      await whatsappChats.enviar(chat.id, texto.trim(), msgRespondida?.wa_message_id || null)

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
    await whatsappChats.transferir(chat.id, {
      setor_id,
      atendente_id,
    })

    setModalTransferir(false)
    setTransferSetorId('')
    setTransferAtendenteId('')

    await carregar()

    toast.showSuccess('Chat transferido.')
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

    if (!file || !chat) return

   

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

      await whatsappChats.encerrar(chat.id)

      await carregar()

      toast.showSuccess('Atendimento encerrado.')

    } finally { setEncerrando(false) }

  }



  if (loading && !chat) return <div className="flex h-full items-center justify-center italic text-slate-400">Carregando workspace...</div>



  const encerrado = chat?.estado === 'encerrado'

  const isResponsavel = user?.role === 'admin' || (chat?.atendente_id === user?.id)

  const podeEnviar = chat?.estado === 'em_atendimento' && isResponsavel && !encerrado



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

              <div className="flex items-center gap-2 text-[10px]">

                <span className="min-w-0 truncate font-mono font-bold text-cyan-600" title={exibirProtocolo(chat?.protocolo)}>
                  {exibirProtocolo(chat?.protocolo)}
                </span>

                <span className="text-slate-300">•</span>

                <span className={`capitalize ${encerrado ? 'text-red-500' : 'text-emerald-500'}`}>{chat?.estado.replace(/_/g, ' ')}</span>

              </div>

            </div>

          </div>



          <div className="flex items-center gap-2">

             {!encerrado && (

              <>

              <Button
  variant="primary"
  className="hidden sm:inline-flex text-xs h-8"
  onClick={() => setModalTransferir(true)}
>
  Transferir
</Button>

                <Button variant="ghost" className="hidden sm:inline-flex text-xs h-8" onClick={() => setModalVinc(true)}>Tickets</Button>

                {podeEnviar && (

                  <Button variant="danger" className="h-8 px-3 text-xs" onClick={() => void encerrar()} loading={encerrando}>Encerrar</Button>

                )}

              </>

            )}

          </div>

        </header>



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

            const isSystem = m.evento_sistema === 'comentario_interno'

           

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

                  {isSystem && <span className="text-[9px] font-bold text-amber-600 uppercase px-2">🔒 Interno</span>}

                 

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

              disabled={enviando || encerrado}

              className="h-10 w-10 shrink-0 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"

            >

              📎

            </Button>



            <textarea

              value={texto}

              onChange={(e) => setTexto(e.target.value)}

              placeholder={podeEnviar ? "Escreva uma mensagem..." : "Apenas leitura..."}

              rows={1}

              disabled={encerrado}

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

              disabled={enviando || !texto.trim() || encerrado}

              className="h-10 w-10 shrink-0 rounded-xl bg-cyan-600 p-0 text-white shadow-lg shadow-cyan-600/30 hover:bg-cyan-700 disabled:opacity-50"

            >

              {enviando ? '...' : '➤'}

            </Button>

          </div>

        </footer>

      </main>



      {/* Modais (Vincular exemplo) */}

      {modalTransferir && (
  <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
    <Card className="w-full max-w-lg p-6">
      <h3 className="text-lg font-bold">Transferir Atendimento</h3>

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

      {modalVinc && (

        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">

           <Card className="w-full max-w-lg p-6 animate-in zoom-in-95">

              <h3 className="text-lg font-bold">Vincular Ticket</h3>

              <Input className="mt-4" type="number" value={ticketVincId} onChange={(e) => setTicketVincId(e.target.value)} placeholder="Número do Ticket" />

              <div className="mt-6 flex justify-end gap-2">

                <Button variant="secondary" onClick={() => setModalVinc(false)}>Cancelar</Button>

                <Button onClick={() => {/* lógica vincular */ setModalVinc(false)}}>Vincular</Button>

              </div>

           </Card>

        </div>

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