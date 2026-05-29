type Props = {
  label: string
  value: string | null | undefined
  mono?: boolean
  multiline?: boolean
}

export function DetailRow({ label, value, mono, multiline }: Props) {
  const v = value?.trim()
  return (
    <div className="grid grid-cols-1 gap-0.5 border-b border-slate-100 py-3 last:border-0 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-6 sm:py-3.5 dark:border-slate-800">
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">{label}</dt>
      <dd
        className={`text-sm leading-relaxed text-slate-800 dark:text-slate-100 ${mono ? 'font-mono' : ''} ${multiline ? 'whitespace-pre-wrap' : ''}`}
      >
        {v ? v : '—'}
      </dd>
    </div>
  )
}
