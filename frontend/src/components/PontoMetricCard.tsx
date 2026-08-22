export function PontoMetricCard({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string
  value: string
  hint?: string
  tone?: 'neutral' | 'good' | 'warn' | 'info'
}) {
  const toneCls =
    tone === 'good'
      ? 'border-emerald-200/80 bg-emerald-50/80 dark:border-emerald-900/60 dark:bg-emerald-950/30'
      : tone === 'warn'
        ? 'border-amber-200/80 bg-amber-50/80 dark:border-amber-900/60 dark:bg-amber-950/30'
        : tone === 'info'
          ? 'border-sky-200/80 bg-sky-50/80 dark:border-sky-900/60 dark:bg-sky-950/30'
          : 'border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-900/40'
  return (
    <div className={`rounded-xl border px-4 py-3 ${toneCls}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-100">{value}</p>
      {hint ? <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
    </div>
  )
}
