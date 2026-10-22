import type { ReactNode } from 'react'

type FormSectionProps = {
  title: string
  description?: ReactNode
  /** Ação à direita do título, como “Marcar todas”. */
  action?: ReactNode
  children: ReactNode
  className?: string
  /** Sem cabeçalho com borda — só o título pequeno (ex.: sub-blocos). */
  compact?: boolean
  /** Cabeçalho clicável com chevron; o corpo some quando `expanded` é falso. */
  expanded?: boolean
  onToggle?: () => void
}

export function FormSection({
  title,
  description,
  action,
  children,
  className = '',
  compact = false,
  expanded,
  onToggle,
}: FormSectionProps) {
  if (compact) {
    return (
      <section className={className}>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </h3>
        <div className="space-y-4">{children}</div>
      </section>
    )
  }

  const collapsible = typeof onToggle === 'function'
  const aberto = expanded ?? true
  const chevron = collapsible ? (
    <svg
      className={`size-5 shrink-0 text-slate-400 transition-transform duration-200 dark:text-slate-500 ${aberto ? 'rotate-180' : ''}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  ) : null

  const titulo = (
    <div className="min-w-0">
      <h3 className="text-sm font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3>
      {description && (!collapsible || aberto) ? (
        <div className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">{description}</div>
      ) : null}
    </div>
  )

  const lateral = action || chevron ? (
    <div className="flex shrink-0 items-center gap-2">
      {action}
      {chevron}
    </div>
  ) : null

  return (
    <section
      className={`rounded-2xl border border-slate-200/90 bg-slate-50/35 p-4 sm:p-5 dark:border-slate-800/55 dark:bg-slate-900/40 ${className}`}
    >
      {collapsible ? (
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={aberto}
          className={`flex w-full items-start justify-between gap-3 rounded-lg text-left transition-colors hover:bg-slate-100/60 dark:hover:bg-white/5 ${
            aberto ? 'mb-4 border-b border-slate-200/80 pb-3 dark:border-slate-800/55' : ''
          }`}
        >
          {titulo}
          {lateral}
        </button>
      ) : (
        <header className="mb-4 flex items-start justify-between gap-3 border-b border-slate-200/80 pb-3 dark:border-slate-800/55">
          {titulo}
          {lateral}
        </header>
      )}
      {!collapsible || aberto ? <div className="space-y-4 sm:space-y-5">{children}</div> : null}
    </section>
  )
}
