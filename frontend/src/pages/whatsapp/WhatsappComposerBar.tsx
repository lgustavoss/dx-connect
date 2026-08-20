import { useEffect, useRef, useState, type ClipboardEvent } from 'react'
import { Button } from '../../components/ui/Button'
import { KbConsultaButton } from '../../components/KbConsultaModal'
import { RespostasProntasPicker } from '../../components/RespostasProntasPicker'
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
  /** Setor do chat para respostas prontas; omitir esconde o botão. */
  setorId?: number | null
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
  setorId,
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
  const enviandoLocalRef = useRef(false)

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

  useEffect(() => {
    if (!enviando) enviandoLocalRef.current = false
  }, [enviando])

  const temTexto = texto.trim().length > 0
  /** Não incluir `enviando`: disabled no textarea remove o foco (#539). */
  const campoBloqueado = encerrado || !podeDigitar
  const acoesBloqueadas = campoBloqueado || enviando || enviandoLocalRef.current

  function enviar() {
    if (acoesBloqueadas || !temTexto || enviandoLocalRef.current) return
    enviandoLocalRef.current = true
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

  const btnIcon =
    'flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800'

  return (
    <div className="relative space-y-2">
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

      {/*
        Mobile (#750): [+] [ campo … sticker=prontas ] [KB] [mic/send]
        Desktop: mantém emoji separado à esquerda do campo.
      */}
      <div className="flex min-w-0 items-end gap-1 rounded-2xl bg-slate-100 p-1.5 shadow-inner dark:bg-slate-900 sm:gap-1.5 sm:p-2">
        <div className="relative shrink-0" ref={menuRef}>
          <button
            type="button"
            disabled={acoesBloqueadas || modoInterno || !podeEnviar}
            aria-label="Anexos"
            title={modoInterno ? 'Anexos indisponíveis em modo interno' : 'Anexos'}
            onClick={() => {
              setPainelEmojiAberto(false)
              setMenuAberto((o) => !o)
            }}
            className={`${btnIcon} text-xl`}
          >
            +
          </button>
          {menuAberto && (
            <div className="absolute bottom-full left-0 z-20 mb-2 min-w-[12rem] rounded-xl border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              {MENU_ANEXOS.map((item) => (
                <button
                  key={item.tipo}
                  type="button"
                  className="block w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                  onClick={() => {
                    setMenuAberto(false)
                    onEscolherAnexo(item.tipo)
                  }}
                >
                  {item.label}
                </button>
              ))}
              <button
                type="button"
                className="block w-full border-t border-slate-100 px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 md:hidden dark:border-slate-800 dark:text-slate-200 dark:hover:bg-slate-800"
                onClick={() => {
                  setMenuAberto(false)
                  setPainelEmojiAberto(true)
                }}
              >
                Emoji e figurinhas
              </button>
            </div>
          )}
        </div>

        {/* Emoji visível só no desktop; no mobile vai no menu + */}
        <div className="relative hidden shrink-0 md:block" ref={emojiRef}>
          <button
            type="button"
            disabled={acoesBloqueadas || modoInterno || !podeEnviar}
            title="Emoji e figurinhas"
            aria-label="Emoji e figurinhas"
            aria-expanded={painelEmojiAberto}
            onClick={() => setPainelEmojiAberto((o) => !o)}
            className={`${btnIcon} text-lg`}
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

        {/* Campo + sticker (prontas) dentro no mobile */}
        <div className="relative flex min-h-[44px] min-w-0 flex-1 items-end rounded-xl bg-white px-1 dark:bg-slate-950/60">
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
                    ? 'Mensagem'
                    : 'Somente comentários internos…')
            }
            rows={1}
            disabled={campoBloqueado}
            className="max-h-32 min-h-[44px] min-w-0 flex-1 resize-none border-0 bg-transparent px-2 py-2.5 text-base leading-6 outline-none ring-0 focus:border-0 focus:outline-none focus:ring-0 sm:text-sm dark:text-slate-100 placeholder:text-slate-400"
            onKeyDown={(e) => {
              if (e.key !== 'Enter' || e.shiftKey) return
              const tecladoFisico = window.matchMedia('(min-width: 768px)').matches
              if (!tecladoFisico) return
              e.preventDefault()
              if (!acoesBloqueadas && temTexto) enviar()
            }}
            onPaste={handlePaste}
          />
          {setorId != null && (
            <div className="relative shrink-0 self-end pb-0.5 md:hidden">
              <RespostasProntasPicker
                setorId={setorId}
                modoComposer
                varianteSticker
                disabled={acoesBloqueadas || modoInterno || !podeEnviar}
                onInserir={inserirEmojiNoCursor}
              />
            </div>
          )}
        </div>

        {/* Desktop: prontas e KB como antes; mobile: KB à direita do campo */}
        {setorId != null && (
          <div className="relative hidden shrink-0 md:block">
            <RespostasProntasPicker
              setorId={setorId}
              modoComposer
              disabled={acoesBloqueadas || modoInterno || !podeEnviar}
              onInserir={inserirEmojiNoCursor}
            />
          </div>
        )}

        {onInserirReferenciaKb && (
          <KbConsultaButton
            disabled={encerrado}
            modoComposer
            onInserirReferencia={podeDigitar ? onInserirReferenciaKb : undefined}
          />
        )}

        {/* Painel emoji aberto a partir do menu + (mobile) */}
        {painelEmojiAberto && (
          <div className="absolute bottom-full left-2 z-30 mb-2 md:hidden">
            <WhatsappEmojiFigurinhaPanel
              disabled={acoesBloqueadas || modoInterno || !podeEnviar}
              onInserirEmoji={inserirEmojiNoCursor}
              onEnviarFigurinha={onEnviarFigurinha}
              onFechar={() => setPainelEmojiAberto(false)}
            />
          </div>
        )}

        {temTexto ? (
          <Button
            onClick={enviar}
            disabled={acoesBloqueadas || !temTexto}
            className="h-10 w-10 shrink-0 rounded-full bg-cyan-600 p-0 text-white shadow-lg shadow-cyan-600/30 hover:bg-cyan-700 disabled:opacity-50"
            aria-label={enviando ? 'A enviar' : 'Enviar'}
            aria-busy={enviando}
          >
            {enviando ? (
              <span className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              '➤'
            )}
          </Button>
        ) : (
          <button
            type="button"
            disabled={acoesBloqueadas || modoInterno || !podeEnviar || gravando}
            aria-label="Gravar áudio"
            title="Gravar áudio"
            onClick={() => setGravando(true)}
            className={`${btnIcon} text-lg`}
          >
            🎤
          </button>
        )}
      </div>
    </div>
  )
}
