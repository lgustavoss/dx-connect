import { useRef } from 'react'
import { Button } from '../ui/Button'

type Props = {
  texto: string
  onTextoChange: (v: string) => void
  onEnviar: () => void
  enviando: boolean
  placeholder?: string
  labelEnviar?: string
}

export function ChatInternoComposer({
  texto,
  onTextoChange,
  onEnviar,
  enviando,
  placeholder = 'Escreva uma mensagem…',
  labelEnviar = 'Enviar',
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const temTexto = texto.trim().length > 0
  const desabilitado = enviando || !temTexto

  function enviar() {
    if (desabilitado) return
    onEnviar()
  }

  return (
    <div className="flex items-end gap-2 border-t border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
      <textarea
        ref={textareaRef}
        value={texto}
        rows={2}
        placeholder={placeholder}
        disabled={enviando}
        className="max-h-32 min-h-[44px] flex-1 resize-y rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none ring-cyan-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        onChange={(e) => onTextoChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            enviar()
          }
        }}
      />
      <Button type="button" onClick={enviar} disabled={desabilitado} className="shrink-0">
        {enviando ? 'Enviando…' : labelEnviar}
      </Button>
    </div>
  )
}
