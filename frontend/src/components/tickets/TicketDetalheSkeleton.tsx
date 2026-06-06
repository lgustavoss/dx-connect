function Pulse({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200/90 dark:bg-slate-800/70 ${className}`} aria-hidden />
}

export function TicketDetalheSkeleton() {
  return (
    <div
      className="-m-4 flex h-full min-h-0 flex-col overflow-hidden md:-m-6"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Carregando ticket"
    >
      <div className="shrink-0 border-b border-slate-200/70 bg-white dark:border-slate-700/70 dark:bg-slate-950 sm:rounded-b-2xl sm:border sm:border-t-0">
        <div className="mx-auto max-w-6xl space-y-3 px-3 py-2.5 sm:px-5 sm:py-4 lg:py-5">
          <Pulse className="h-4 w-16" />
          <div className="flex items-start justify-between gap-3">
            <Pulse className="h-6 w-32 lg:h-8 lg:w-40" />
            <div className="hidden gap-2 lg:flex">
              <Pulse className="h-9 w-14" />
              <Pulse className="h-9 w-16" />
            </div>
          </div>
          <Pulse className="h-5 w-full max-w-xl sm:h-6" />
          <Pulse className="h-4 w-2/3 max-w-sm" />
          <div className="flex gap-2 overflow-hidden pt-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <Pulse key={i} className="h-7 w-20 shrink-0 rounded-full" />
            ))}
          </div>
          <Pulse className="h-3 w-40" />
          <div className="border-t border-slate-100 pt-2 lg:hidden dark:border-slate-800">
            <div className="grid grid-cols-2 gap-1.5">
              <Pulse className="h-9 w-full" />
              <Pulse className="h-9 w-full" />
            </div>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl space-y-4 px-3 py-3 sm:space-y-6 sm:px-5 sm:py-4 md:px-6">
          <div className="rounded-xl border border-slate-200/90 bg-white p-4 dark:border-slate-700/80 dark:bg-slate-950/40">
            <Pulse className="mb-3 h-4 w-28" />
            <div className="space-y-3">
              <Pulse className="h-16 w-full rounded-xl" />
              <Pulse className="h-16 w-full rounded-xl" />
              <Pulse className="h-24 w-full rounded-xl" />
            </div>
          </div>
          <div className="rounded-xl border border-slate-200/90 bg-white p-4 dark:border-slate-700/80 dark:bg-slate-950/40">
            <Pulse className="mb-3 h-4 w-24" />
            <Pulse className="h-28 w-full rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  )
}
