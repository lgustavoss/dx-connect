import { useEffect, useRef, useState } from 'react'
import { Button } from '../ui/Button'
import { WHATSAPP_EMOJIS } from '../../lib/whatsappEmojis'

type Props = {
  arquivo: File
  legendaInicial?: string
  onConfirm: (file: File, caption: string) => void | Promise<void>
  onCancel: () => void
  enviando?: boolean
}

export function ChatInternoMidiaPreviewOverlay({ arquivo, legendaInicial = '', onConfirm, onCancel, enviando }: Props) {
  const [legenda, setLegenda] = useState(legendaInicial)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [emojiAberto, setEmojiAberto] = useState(false)
  const legendaRef = useRef<HTMLTextAreaElement>(null)
  const emojiRef = useRef<HTMLDivElement>(null)

  const isImagem = arquivo.type.startsWith('image/')
  const isVideo = arquivo.type.startsWith('video/')

  useEffect(() => {
    const url = URL.createObjectURL(arquivo)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [arquivo])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !enviando) onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel, enviando])

  useEffect(() => {
    if (!emojiAberto) return
    const onDoc = (e: MouseEvent) => {
      if (emojiRef.current && !emojiRef.current.contains(e.target as Node)) setEmojiAberto(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [emojiAberto])

  async function confirmar() {
    if (enviando) return
    await onConfirm(arquivo, legenda.trim())
  }

  function inserirEmoji(emoji: string) {
    const el = legendaRef.current
    if (!el) {
      setLegenda((v) => v + emoji)
      return
    }
    const start = el.selectionStart ?? legenda.length
    const end = el.selectionEnd ?? legenda.length
    const next = `${legenda.slice(0, start)}${emoji}${legenda.slice(end)}`
    setLegenda(next)
    requestAnimationFrame(() => {
      el.focus()
      const pos = start + emoji.length
      el.setSelectionRange(pos, pos)
    })
  }

  return (
    <div className="absolute inset-0 z-50 flex flex-col bg-[#0b141a] text-white">
      <header className="flex shrink-0 items-center px-3 py-3 sm:px-4">
        <button
          type="button"
          disabled={enviando}
          onClick={onCancel}
          className="flex h-10 w-10 items-center justify-center rounded-full text-2xl text-white/90 hover:bg-white/10 disabled:opacity-40"
          aria-label="Fechar"
        >
          ×
        </button>
      </header>

      <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden px-4 py-2">
        {previewUrl && isImagem && (
          <img src={previewUrl} alt="" className="max-h-full max-w-full object-contain" />
        )}
        {previewUrl && isVideo && (
          <video src={previewUrl} controls className="max-h-full max-w-full rounded-lg" />
        )}
      </div>

      <footer className="shrink-0 border-t border-white/10 bg-[#0b141a] px-3 py-3 sm:px-4">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <div className="relative min-w-0 flex-1">
            <textarea
              ref={legendaRef}
              value={legenda}
              onChange={(e) => setLegenda(e.target.value)}
              placeholder="Digite uma mensagem"
              rows={1}
              disabled={enviando}
              className="max-h-24 min-h-[44px] w-full resize-none rounded-2xl border border-white/10 bg-[#1f2c34] px-4 py-3 pr-12 text-base text-white placeholder:text-white/40 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/40"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void confirmar()
                }
              }}
            />
            <div className="absolute bottom-2 right-2" ref={emojiRef}>
              <button
                type="button"
                disabled={enviando}
                onClick={() => setEmojiAberto((o) => !o)}
                className="flex h-8 w-8 items-center justify-center rounded-full text-lg hover:bg-white/10 disabled:opacity-40"
                aria-label="Emoji"
              >
                😊
              </button>
              {emojiAberto && (
                <div className="absolute bottom-full right-0 z-10 mb-2 w-64 rounded-xl border border-white/10 bg-[#1f2c34] p-2 shadow-xl">
                  <div className="grid max-h-40 grid-cols-8 gap-0.5 overflow-y-auto">
                    {WHATSAPP_EMOJIS.map((e) => (
                      <button
                        key={e}
                        type="button"
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-lg hover:bg-white/10"
                        onClick={() => inserirEmoji(e)}
                      >
                        {e}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <Button
            onClick={() => void confirmar()}
            disabled={enviando}
            className="h-12 w-12 shrink-0 rounded-full bg-cyan-600 p-0 text-xl text-white shadow-lg hover:bg-cyan-500 disabled:opacity-50"
            aria-label="Enviar"
            title="Enviar"
          >
            {enviando ? '…' : '➤'}
          </Button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl truncate text-center text-xs text-white/40">
          {arquivo.name || (isImagem ? 'Imagem' : isVideo ? 'Vídeo' : 'Arquivo')}
        </p>
      </footer>
    </div>
  )
}
