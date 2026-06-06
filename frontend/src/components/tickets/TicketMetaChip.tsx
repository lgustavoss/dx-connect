type Props = {
  label: string
  value: string
  onClick: () => void
  disabled?: boolean
}

export function TicketMetaChip({ label, value, onClick, disabled }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex shrink-0 items-center gap-1 rounded-full border border-slate-200/90 bg-slate-50/80 px-2.5 py-1 text-left text-[11px] shadow-sm transition-[transform,colors] hover:border-slate-300 hover:bg-slate-100/90 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800/70 dark:hover:border-slate-500 dark:hover:bg-slate-800 touch-manipulation sm:gap-1.5 sm:px-3 sm:py-1.5 sm:text-xs"
    >
      <span className="shrink-0 font-medium text-slate-500 dark:text-slate-400">{label}</span>
      <span className="max-w-[7.5rem] truncate font-semibold text-slate-800 sm:max-w-[10rem] dark:text-slate-100">
        {value}
      </span>
    </button>
  )
}
