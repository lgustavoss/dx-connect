import { type ReactNode } from 'react'

type Props = {
  title: string
  badge?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
}

/** Card com cabeçalho clicável para recolher o conteúdo (acordeão independente). */
export function CollapsibleCard({ title, badge, open, onOpenChange, children }: Props) {
  return (
    <details
      className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/95 dark:shadow-none dark:ring-1 dark:ring-white/5"
      open={open}
      onToggle={(e) => {
        const next = e.currentTarget.open
        if (next !== open) onOpenChange(next)
      }}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-6 py-4 marker:content-none [&::-webkit-details-marker]:hidden">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          {title}
          {badge ? (
            <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">{badge}</span>
          ) : null}
        </h2>
        <span
          className={`shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        >
          ▾
        </span>
      </summary>
      <div className="border-t border-slate-200 px-6 py-4 dark:border-slate-800">{children}</div>
    </details>
  )
}
