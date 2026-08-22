import { useEffect, useId, useRef, type ReactNode } from 'react'
import { Card } from './Card'
import { Button } from './Button'

type Props = {
  open: boolean
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'primary'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
  children?: ReactNode
  /** Oculta botões de acção (modal com acções customizadas no children). */
  hideActions?: boolean
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  variant = 'primary',
  loading = false,
  onConfirm,
  onCancel,
  children,
  hideActions = false,
}: Props) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const onCancelRef = useRef(onCancel)
  onCancelRef.current = onCancel

  useEffect(() => {
    if (!open) return
    // Só ao abrir — não refocar quando onCancel muda a cada re-render do pai (poll/SSE).
    dialogRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onCancelRef.current()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[110] flex items-end justify-center bg-slate-900/50 p-0 backdrop-blur-sm md:items-center md:p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCancel()
      }}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        className="w-full max-w-lg outline-none md:max-h-[min(92dvh,var(--vv-height,92dvh))]"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <Card className="max-h-[min(92dvh,var(--vv-height,92dvh))] animate-in zoom-in-95 overflow-y-auto rounded-b-none border-none p-0 shadow-xl ring-1 ring-slate-200 md:rounded-2xl dark:ring-slate-800">
          <div className="p-6">
            <div className="flex items-start justify-between gap-3">
              <h3 id={titleId} className="text-lg font-bold text-slate-900 dark:text-white">
                {title}
              </h3>
              <button
                type="button"
                className="text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
                onClick={onCancel}
                aria-label="Fechar"
              >
                &times;
              </button>
            </div>
            {message && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{message}</p>}
            {children && <div className="mt-4">{children}</div>}
            {!hideActions && (
              <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <Button variant="cancel" onClick={onCancel} disabled={loading}>
                  {cancelLabel}
                </Button>
                <Button
                  variant={variant === 'danger' ? 'danger' : 'primary'}
                  onClick={onConfirm}
                  loading={loading}
                >
                  {confirmLabel}
                </Button>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
