import { useEffect, useState } from 'react'
import { KbConsultaPanel } from './KbConsultaPanel'
import { Button } from './ui/Button'
import { MODAL_PANEL_SCROLLABLE } from '../lib/modalPanel'

type Props = {
  open: boolean
  onClose: () => void
  onInserirReferencia?: (texto: string) => void
  disabled?: boolean
}

export function KbConsultaModal({ open, onClose, onInserirReferencia, disabled }: Props) {
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="kb-consulta-title"
      onClick={onClose}
    >
      <div
        className={MODAL_PANEL_SCROLLABLE}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 id="kb-consulta-title" className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              Ajuda
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Consulte manuais publicados durante o atendimento.
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={onClose} disabled={disabled}>
            Fechar
          </Button>
        </div>
        <KbConsultaPanel onInserirReferencia={onInserirReferencia} showInserir={Boolean(onInserirReferencia)} />
      </div>
    </div>
  )
}

type ButtonProps = {
  disabled?: boolean
  onInserirReferencia?: (texto: string) => void
}

export function KbConsultaButton({ disabled, onInserirReferencia }: ButtonProps) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 text-xs sm:text-sm"
      >
        <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
          />
        </svg>
        Consultar manuais
      </Button>
      <KbConsultaModal
        open={open}
        onClose={() => setOpen(false)}
        onInserirReferencia={
          onInserirReferencia
            ? (texto) => {
                onInserirReferencia(texto)
                setOpen(false)
              }
            : undefined
        }
        disabled={disabled}
      />
    </>
  )
}
