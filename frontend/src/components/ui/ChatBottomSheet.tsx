import { useEffect, useId, useRef, type ReactNode } from 'react'

type Props = {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** Classe extra no painel (ex. max-w). */
  panelClassName?: string
  /** z-index do overlay (default 110). */
  zClassName?: string
}

/**
 * Folha inferior no mobile + modal centrado no desktop.
 * Backdrop absorve toques (composer do chat fica inacessível) — #752 / #754.
 */
export function ChatBottomSheet({
  open,
  title,
  onClose,
  children,
  panelClassName = '',
  zClassName = 'z-[110]',
}: Props) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    if (!open) return
    panelRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onCloseRef.current()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  if (!open) return null

  return (
    <div
      className={`fixed inset-0 ${zClassName} flex items-end justify-center bg-slate-900/50 p-0 backdrop-blur-sm md:items-center md:p-4`}
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`flex max-h-[min(90dvh,var(--vv-height,90dvh))] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl outline-none ring-1 ring-slate-200 md:max-h-[min(92dvh,var(--vv-height,92dvh))] md:rounded-2xl dark:bg-slate-900 dark:ring-slate-800 ${panelClassName}`}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-100 px-4 py-3 dark:border-slate-800 sm:px-6 sm:py-4">
          <h3 id={titleId} className="text-lg font-bold text-slate-900 dark:text-white">
            {title}
          </h3>
          <button
            type="button"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg text-xl text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            onClick={onClose}
            aria-label="Fechar"
          >
            &times;
          </button>
        </div>
        <div className="dx-scrollbar min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6">{children}</div>
      </div>
    </div>
  )
}
