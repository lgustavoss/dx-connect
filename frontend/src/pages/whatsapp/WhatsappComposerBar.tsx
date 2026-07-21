import { useEffect, useRef, useState, type ClipboardEvent } from 'react'
import { Button } from '../../components/ui/Button'
import { KbConsultaButton } from '../../components/KbConsultaModal'
import type { TipoAnexoPicker } from './WhatsappBarraAnexos'
import { WhatsappGravadorAudioInline } from './WhatsappGravadorAudioInline'
import { WhatsappEmojiFigurinhaPanel } from './WhatsappEmojiFigurinhaPanel'

type Props = {
  texto: string
  onTextoChange: (v: string) => void
  onEnviar: () => void
  onEnviarInterno?: () => void
  onEscolherAnexo: (tipo: TipoAnexoPicker) => void
  onAudioGravado: (file: File) => void
  onInserirEmoji: (emoji: string) => void
  onEnviarFigurinha: (file: File) => void
  /** Ctrl+V / colar ficheiro do clipboard (imagem, etc.) */
  onColarArquivo?: (file: File) => void
  enviando: boolean
  encerrado: boolean
  podeEnviar: boolean
  modoInterno: boolean
  podeDigitar: boolean
  onInserirReferenciaKb?: (ref: string) => void
  /** Incrementar para focar o textarea (ex.: após Responder). */
  focoPedidoEm?: number
  /** Placeholder customizado (ex.: pós-inatividade a classificar). */
  placeholder?: string
}

type MenuAnexo = { tipo: TipoAnexoPicker; label: string }

const MENU_ANEXOS: MenuAnexo[] = [
  { tipo: 'documento', label: 'Documento' },
  { tipo: 'imagem', label: 'Fotos e imagens' },
  { tipo: 'video', label: 'Vídeo' },
  { tipo: 'audio', label: 'Áudio (ficheiro)' },
]

export function WhatsappComposerBar({
  texto,
  onTextoChange,
  onEnviar,
  onEnviarInterno,
  onEscolherAnexo,
  onAudioGravado,
  onInserirEmoji,
  onEnviarFigurinha,
  onColarArquivo,
  enviando,
  encerrado,
  podeEnviar,
  modoInterno,
  podeDigitar,
  onInserirReferenciaKb,
  focoPedidoEm,
  placeholder,
}: Props) {
  const [menuAberto, setMenuAberto] = useState(false)
  const [painelEmojiAberto, setPainelEmojiAberto] = useState(false)
  const [gravando, setGravando] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const emojiRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!menuAberto) return
    const onDoc = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuAberto(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [menuAberto])

  useEffect(() => {
    if (focoPedidoEm == null || focoPedidoEm <= 0) return
    requestAnimationFrame(() => textareaRef.current?.focus())
  }, [focoPedidoEm])

  const temTexto = texto.trim().length > 0
  /** Não incluir `enviando`: disabled no textarea remove o foco (#539). */
  const campoBloqueado = encerrado || !podeDigitar
  const acoesBloqueadas = campoBloqueado || enviando

  function enviar() {
    if (acoesBloqueadas || !temTexto) return
    if (modoInterno && onEnviarInterno) onEnviarInterno()
    else onEnviar()
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  function inserirEmojiNoCursor(emoji: string) {
    const el = textareaRef.current
    if (!el) {
      onInserirEmoji(emoji)
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

  function handlePaste(e: ClipboardEvent<HTMLTextAreaElement>) {
    if (acoesBloqueadas || modoInterno || !podeEnviar || !onColarArquivo) return
    const files = Array.from(e.clipboardData?.items ?? [])
      .filter((item) => item.kind === 'file')
      .map((item) => item.getAsFile())
      .filter((file): file is File => Boolean(file))
    if (files.length === 0) return
    e.preventDefault()
    onColarArquivo(files[0])
  }

  return (
    <div className="space-y-2">
      {gravando && podeEnviar && !encerrado && (
        <WhatsappGravadorAudioInline
          disabled={enviando}
          onConcluido={(file) => {
            setGravando(false)
            onAudioGravado(file)
          }}
          onCancelar={() => setGravando(false)}
        />
      )}

      <div className="flex min-w-0 items-end gap-1 rounded-2xl bg-slate-100 p-1.5 shadow-inner dark:bg-slate-900 sm:gap-2 sm:p-2">
        <div className="relative shrink-0" ref={menuRef}>
          <button
            type="button"
            disabled={acoesBloqueadas || modoInterno || !podeEnviar}
            aria-label="Anexos"
            title={modoInterno ? 'Anexos indisponíveis em modo interno' : 'Anexos'}
            onClick={() => setMenuAberto((o) => !o)}
            className="flex h-10 w-10 items-center justify-center rounded-full text-xl text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            +
          </button>
          {menuAberto && (
            <div className="absolute bottom-full left-0 z-20 mb-2 min-w-[11rem] rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              {MENU_ANEXOS.map((item) => (
                <button
                  key={item.tipo}
                  type="button"
                  className="block w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                  onClick={() => {
                    setMenuAberto(false)
                    onEscolherAnexo(item.tipo)
                  }}
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
            disabled={acoesBloqueadas || modoInterno || !podeEnviar}
            title="Emoji e figurinhas"
            aria-label="Emoji e figurinhas"
            aria-expanded={painelEmojiAberto}
            onClick={() => setPainelEmojiAberto((o) => !o)}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-lg text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            😊
          </button>
          {painelEmojiAberto && (
            <WhatsappEmojiFigurinhaPanel
              disabled={acoesBloqueadas || modoInterno || !podeEnviar}
              onInserirEmoji={inserirEmojiNoCursor}
              onEnviarFigurinha={onEnviarFigurinha}
              onFechar={() => setPainelEmojiAberto(false)}
            />
          )}
        </div>

        {onInserirReferenciaKb && (
          <KbConsultaButton
            disabled={encerrado}
            modoComposer
            onInserirReferencia={podeDigitar ? onInserirReferenciaKb : undefined}
          />
        )}

        <textarea
          ref={textareaRef}
          value={texto}
          onChange={(e) => onTextoChange(e.target.value)}
          placeholder={
            placeholder ??
            (encerrado
              ? 'Apenas leitura…'
              : modoInterno
                ? 'Comentário interno…'
                : podeEnviar
                  ? 'Escreva uma mensagem…'
                  : 'Somente comentários internos…')
          }
          rows={1}
          disabled={campoBloqueado}
          className="max-h-32 min-h-[44px] min-w-0 flex-1 resize-none border-0 bg-transparent px-2 py-2.5 text-base outline-none ring-0 focus:border-0 focus:outline-none focus:ring-0 sm:text-sm dark:text-slate-100 placeholder:text-slate-400"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              if (!acoesBloqueadas && temTexto) enviar()
            }
          }}
          onPaste={handlePaste}
        />

        {temTexto ? (
          <Button
            onClick={enviar}
            disabled={acoesBloqueadas || !temTexto}
            className="h-10 w-10 shrink-0 rounded-full bg-cyan-600 p-0 text-white shadow-lg shadow-cyan-600/30 hover:bg-cyan-700 disabled:opacity-50"
            aria-label="Enviar"
          >
            {enviando ? '…' : '➤'}
          </Button>
        ) : (
          <button
            type="button"
            disabled={acoesBloqueadas || modoInterno || !podeEnviar || gravando}
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
  )
}
