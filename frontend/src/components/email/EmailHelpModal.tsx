import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Button } from '../ui/Button'

type Props = {
  open: boolean
  title: string
  steps: string[]
  onClose: () => void
}

export function EmailHelpModal({ open, title, steps, onClose }: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div
      className="fixed inset-0 z-[700] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="email-help-modal-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-[1px]"
        onClick={onClose}
        aria-label="Fechar ajuda"
      />
      <div className="relative max-h-[min(85vh,640px)] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-600 dark:bg-slate-900 md:max-w-2xl md:max-h-[min(88vh,720px)] xl:max-w-4xl xl:max-h-[min(90vh,800px)]">
        <h2 id="email-help-modal-title" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          {title}
        </h2>
        <ol className="mt-4 list-decimal space-y-2.5 pl-5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          {steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
        <div className="mt-6 flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

/** Botão circular «?» ao lado de rótulos. */
export function EmailHelpIconButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex size-7 shrink-0 items-center justify-center rounded-full border border-slate-300 bg-white text-sm font-semibold text-slate-600 shadow-sm transition-colors hover:border-sky-400 hover:bg-sky-50 hover:text-sky-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-sky-500 dark:hover:bg-slate-800/80 dark:hover:text-sky-200"
      aria-label={label}
    >
      ?
    </button>
  )
}
