import { useEffect, useRef, useState } from 'react'

import { WHATSAPP_EMOJIS } from '../../lib/whatsappEmojis'

type Tab = 'emoji' | 'figurinha'

type Props = {
  disabled: boolean
  onInserirEmoji: (emoji: string) => void
  onEnviarFigurinha: (file: File) => void
  onFechar: () => void
}

export function WhatsappEmojiFigurinhaPanel({ disabled, onInserirEmoji, onEnviarFigurinha, onFechar }: Props) {
  const [tab, setTab] = useState<Tab>('emoji')
  const panelRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

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
      <div className="flex border-b border-slate-100 dark:border-slate-800">
        {(['emoji', 'figurinha'] as const).map((t) => (
          <button
            key={t}
            type="button"
            disabled={disabled}
            onClick={() => setTab(t)}
            className={`flex-1 px-3 py-2 text-xs font-semibold ${
              tab === t
                ? 'border-b-2 border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'
            }`}
          >
            {t === 'emoji' ? 'Emoji' : 'Figurinha'}
          </button>
        ))}
      </div>

      {tab === 'emoji' ? (
        <div className="grid max-h-48 grid-cols-8 gap-0.5 overflow-y-auto p-2">
          {WHATSAPP_EMOJIS.map((e) => (
            <button
              key={e}
              type="button"
              disabled={disabled}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-xl hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800"
              onClick={() => {
                onInserirEmoji(e)
                onFechar()
              }}
            >
              {e}
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-2 p-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Envie um ficheiro WebP ou PNG (tamanho típico de figurinha WhatsApp).
          </p>
          <button
            type="button"
            disabled={disabled}
            className="w-full rounded-lg border border-dashed border-slate-300 px-3 py-4 text-sm font-medium text-slate-700 hover:border-cyan-400 hover:bg-cyan-50 disabled:opacity-40 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-cyan-950/30"
            onClick={() => fileRef.current?.click()}
          >
            Escolher figurinha…
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/webp,image/png,.webp,.png"
            className="hidden"
            onChange={(ev) => {
              const file = ev.target.files?.[0]
              if (file) {
                onEnviarFigurinha(file)
                onFechar()
              }
              ev.target.value = ''
            }}
          />
        </div>
      )}
    </div>
  )
}
