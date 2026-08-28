type Props = {
  rows?: number
}

/** Placeholder da tabela enquanto carrega Minhas solicitações no Sobre. */
export function SolicitacoesMelhoriaListaSkeleton({ rows = 4 }: Props) {
  return (
    <div className="divide-y divide-slate-100 dark:divide-slate-800" aria-busy="true" aria-label="Carregando solicitações">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex flex-wrap items-center gap-4 px-4 py-4 sm:px-6">
          <div className="h-5 w-20 animate-pulse rounded-full bg-slate-100 dark:bg-slate-800" />
          <div className="h-4 w-24 animate-pulse rounded bg-slate-100 font-mono dark:bg-slate-800" />
          <div className="min-w-[12rem] flex-1 space-y-2">
            <div className="h-4 w-full max-w-md animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
            <div className="h-3 w-32 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
          </div>
          <div className="h-5 w-28 animate-pulse rounded-full bg-slate-100 dark:bg-slate-800" />
          <div className="h-4 w-24 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
        </div>
      ))}
    </div>
  )
}
