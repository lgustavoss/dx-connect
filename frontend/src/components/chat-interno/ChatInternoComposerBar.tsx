import { useEffect, useRef, useState } from 'react'

import { Button } from '../ui/Button'

import { ACCEPT_ANEXO, type TipoAnexoPicker } from '../../pages/whatsapp/WhatsappBarraAnexos'

import { WhatsappGravadorAudioInline } from '../../pages/whatsapp/WhatsappGravadorAudioInline'

import { WHATSAPP_EMOJIS } from '../../lib/whatsappEmojis'

import { ChatInternoMidiaPreviewOverlay } from './ChatInternoMidiaPreviewOverlay'



type MenuAnexo = { id: TipoAnexoPicker; label: string }



const MENU_ANEXOS: MenuAnexo[] = [

  { id: 'documento', label: 'Documento' },

  { id: 'imagem', label: 'Fotos e imagens' },

  { id: 'video', label: 'Vídeo' },

  { id: 'audio', label: 'Áudio' },

]



type Props = {

  texto: string

  onTextoChange: (v: string) => void

  onEnviar: () => void

  onEnviarMidia: (file: File, caption?: string) => void | Promise<void>

  enviando: boolean

  placeholder?: string

  labelEnviar?: string

  /** Incrementar para focar o textarea (ex.: após Responder). */
  focoPedidoEm?: number

}



function usaPreviewMidia(file: File): boolean {

  return file.type.startsWith('image/') || file.type.startsWith('video/')

}



export function ChatInternoComposerBar({

  texto,

  onTextoChange,

  onEnviar,

  onEnviarMidia,

  enviando,

  placeholder = 'Escreva uma mensagem…',

  labelEnviar = 'Enviar',

  focoPedidoEm,

}: Props) {

  const [menuAberto, setMenuAberto] = useState(false)

  const [painelEmojiAberto, setPainelEmojiAberto] = useState(false)

  const [gravando, setGravando] = useState(false)

  const [tipoPicker, setTipoPicker] = useState<TipoAnexoPicker | null>(null)

  const [midiaPendente, setMidiaPendente] = useState<File | null>(null)
  const [legendaPreview, setLegendaPreview] = useState('')

  const menuRef = useRef<HTMLDivElement>(null)

  const emojiRef = useRef<HTMLDivElement>(null)

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (focoPedidoEm == null || focoPedidoEm <= 0) return
    requestAnimationFrame(() => textareaRef.current?.focus())
  }, [focoPedidoEm])

  const temTexto = texto.trim().length > 0

  const campoBloqueado = Boolean(midiaPendente)
  const acoesBloqueadas = enviando || campoBloqueado



  useEffect(() => {

    if (!menuAberto) return

    const onDoc = (e: MouseEvent) => {

      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuAberto(false)

    }

    document.addEventListener('mousedown', onDoc)

    return () => document.removeEventListener('mousedown', onDoc)

  }, [menuAberto])



  function enviar() {

    if (acoesBloqueadas || !temTexto) return
    onEnviar()
    requestAnimationFrame(() => textareaRef.current?.focus())
  }



  function inserirEmojiNoCursor(emoji: string) {

    const el = textareaRef.current

    if (!el) {

      onTextoChange(texto + emoji)

      return

    }

    const start = el.selectionStart ?? texto.length

    const end = el.selectionEnd ?? texto.length

    const next = `${texto.slice(0, start)}${emoji}${texto.slice(end)}`

    onTextoChange(next)

    requestAnimationFrame(() => {

      el.focus()

      const pos = start + emoji.length

      el.setSelectionRange(pos, pos)

    })

  }



  function abrirPicker(tipo: TipoAnexoPicker) {

    setMenuAberto(false)

    setTipoPicker(tipo)

    requestAnimationFrame(() => fileInputRef.current?.click())

  }



  function enviarArquivoDireto(file: File) {

    const caption = texto.trim() || undefined

    void onEnviarMidia(file, caption)

    if (caption) onTextoChange('')

  }



  function abrirOuEnviarArquivo(file: File) {

    if (usaPreviewMidia(file)) {

      const cap = texto.trim()

      setLegendaPreview(cap)

      if (cap) onTextoChange('')

      setMidiaPendente(file)

      return

    }

    enviarArquivoDireto(file)

  }



  function handleFileSelecionado(e: React.ChangeEvent<HTMLInputElement>) {

    const file = e.target.files?.[0]

    e.target.value = ''

    if (!file || enviando) return

    abrirOuEnviarArquivo(file)

  }



  function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {

    if (enviando || midiaPendente) return

    const files = Array.from(e.clipboardData?.items ?? [])

      .filter((item) => item.kind === 'file')

      .map((item) => item.getAsFile())

      .filter((file): file is File => Boolean(file))

    if (files.length === 0) return



    e.preventDefault()

    abrirOuEnviarArquivo(files[0])

  }



  async function confirmarMidiaPendente(file: File, caption: string) {

    await onEnviarMidia(file, caption || undefined)

    setMidiaPendente(null)

    setLegendaPreview('')

  }



  return (

    <>

      {midiaPendente && (

        <ChatInternoMidiaPreviewOverlay

          arquivo={midiaPendente}

          legendaInicial={legendaPreview}

          enviando={enviando}

          onCancel={() => {

            setMidiaPendente(null)

            setLegendaPreview('')

          }}

          onConfirm={confirmarMidiaPendente}

        />

      )}



      <div className="shrink-0 border-t border-slate-200 bg-white px-3 py-3 dark:border-slate-800 dark:bg-slate-900 md:px-5 lg:px-6">

        {gravando && (

          <div className="mb-2">

            <WhatsappGravadorAudioInline

              disabled={acoesBloqueadas}

              onConcluido={(file) => {

                setGravando(false)

                enviarArquivoDireto(file)

              }}

              onCancelar={() => setGravando(false)}

            />

          </div>

        )}



        <input

          ref={fileInputRef}

          type="file"

          className="hidden"

          accept={tipoPicker ? ACCEPT_ANEXO[tipoPicker] : undefined}

          onChange={handleFileSelecionado}

        />



        <div className="flex items-end gap-1.5 rounded-2xl bg-slate-100 p-2 shadow-inner dark:bg-slate-950 sm:gap-2">

          <div className="relative shrink-0" ref={menuRef}>

            <button

              type="button"

              disabled={acoesBloqueadas}

              aria-label="Anexos"

              title="Anexos"

              onClick={() => setMenuAberto((o) => !o)}

              className="flex h-10 w-10 items-center justify-center rounded-full text-xl text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"

            >

              +

            </button>

            {menuAberto && (

              <div className="absolute bottom-full left-0 z-20 mb-2 min-w-[11rem] rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">

                {MENU_ANEXOS.map((item) => (

                  <button

                    key={item.id}

                    type="button"

                    className="block w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"

                    onClick={() => abrirPicker(item.id)}

                  >

                    {item.label}

                  </button>

                ))}

              </div>

            )}

          </div>



          <div className="relative shrink-0" ref={emojiRef}>

            <button

              type="button"

              disabled={acoesBloqueadas}

              title="Emoji"

              aria-label="Emoji"

              aria-expanded={painelEmojiAberto}

              onClick={() => setPainelEmojiAberto((o) => !o)}

              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-lg text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"

            >

              😊

            </button>

            {painelEmojiAberto && (

              <ChatInternoEmojiPanel

                disabled={acoesBloqueadas}

                onInserirEmoji={inserirEmojiNoCursor}

                onFechar={() => setPainelEmojiAberto(false)}

              />

            )}

          </div>



          <textarea

            ref={textareaRef}

            value={texto}

            onChange={(e) => onTextoChange(e.target.value)}

            placeholder={placeholder}

            rows={1}

            disabled={campoBloqueado}

            className="max-h-32 min-h-[40px] min-w-0 flex-1 resize-none break-words border-0 bg-transparent p-2 text-base outline-none ring-0 focus:border-0 focus:outline-none focus:ring-0 dark:text-slate-100 placeholder:text-slate-400"

            onKeyDown={(e) => {

              if (e.key === 'Enter' && !e.shiftKey) {

                e.preventDefault()

                enviar()

              }

            }}

            onPaste={handlePaste}

          />



          {temTexto ? (

            <Button

              onClick={enviar}

              disabled={acoesBloqueadas || !temTexto}

              className="h-10 w-10 shrink-0 rounded-full bg-cyan-600 p-0 text-white shadow-lg shadow-cyan-600/30 hover:bg-cyan-700 disabled:opacity-50"

              aria-label={labelEnviar}

              title={labelEnviar}

            >

              {enviando ? '…' : '➤'}

            </Button>

          ) : (

            <button

              type="button"

              disabled={acoesBloqueadas || gravando}

              aria-label="Gravar áudio"

              title="Gravar áudio"

              onClick={() => setGravando(true)}

              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-lg text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"

            >

              🎤

            </button>

          )}

        </div>

      </div>

    </>

  )

}



function ChatInternoEmojiPanel({

  disabled,

  onInserirEmoji,

  onFechar,

}: {

  disabled: boolean

  onInserirEmoji: (emoji: string) => void

  onFechar: () => void

}) {

  const panelRef = useRef<HTMLDivElement>(null)



  useEffect(() => {

    const onDoc = (e: MouseEvent) => {

      if (panelRef.current && !panelRef.current.contains(e.target as Node)) onFechar()

    }

    document.addEventListener('mousedown', onDoc)

    return () => document.removeEventListener('mousedown', onDoc)

  }, [onFechar])



  return (

    <div

      ref={panelRef}

      className="absolute bottom-full left-0 z-30 mb-2 w-[min(20rem,calc(100vw-2rem))] rounded-xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"

    >

      <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold text-slate-600 dark:border-slate-800 dark:text-slate-300">

        Emoji

      </div>

      <div className="grid max-h-48 grid-cols-8 gap-0.5 overflow-y-auto p-2">

        {WHATSAPP_EMOJIS.map((e) => (

          <button

            key={e}

            type="button"

            disabled={disabled}

            className="flex h-9 w-9 items-center justify-center rounded-lg text-xl hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800"

            onClick={() => {
              onInserirEmoji(e)
            }}

          >

            {e}

          </button>

        ))}

      </div>

    </div>

  )

}


