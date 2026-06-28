import type { ReactNode } from 'react'

type FormSectionProps = {
  title: string
  description?: ReactNode
  children: ReactNode
  className?: string
  /** Sem cabeçalho com borda — só o título pequeno (ex.: sub-blocos). */
  compact?: boolean
}

export function FormSection({ title, description, children, className = '', compact = false }: FormSectionProps) {
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

  return (
    <section
      className={`rounded-2xl border border-slate-200/90 bg-slate-50/35 p-4 sm:p-5 dark:border-slate-800/55 dark:bg-slate-900/40 ${className}`}
    >
      <header className="mb-4 border-b border-slate-200/80 pb-3 dark:border-slate-800/55">
        <h3 className="text-sm font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3>
        {description ? (
          <div className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">{description}</div>
        ) : null}
      </header>
      <div className="space-y-4 sm:space-y-5">{children}</div>
    </section>
  )
}
