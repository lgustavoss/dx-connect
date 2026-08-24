import type { ReactNode } from 'react'

/** Classes reutilizáveis — visual alinhado ao painel interno (minimalista). */
export const portalInputClass =
  'w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 focus:border-[var(--portal-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--portal-primary)]/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500'

export const portalPrimaryBtnClass =
  'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-[var(--portal-primary)]/30 disabled:opacity-50'

export const portalSecondaryBtnClass =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50'

/** Descartar / Cancelar — gradiente vermelho, alinhado ao Button variant=cancel (#866). */
export const portalCancelBtnClass =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-red-500 to-red-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-red-500/20 transition hover:from-red-400 hover:to-red-500 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 disabled:opacity-50'

export const portalCardClass =
  'rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:shadow-md'

export function PortalPageHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

export function PortalSegmentedControl<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T
  onChange: (v: T) => void
  options: readonly { value: T; label: string }[]
}) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100/80 p-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={[
            'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
            value === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900',
          ].join(' ')}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

export function portalUserInitials(nome: string): string {
  const parts = nome.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}
