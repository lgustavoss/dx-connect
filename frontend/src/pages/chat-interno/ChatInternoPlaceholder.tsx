export function ChatInternoPlaceholder() {
  return (
    <div className="flex h-full min-h-[280px] flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-100 text-cyan-600 dark:bg-cyan-950/50 dark:text-cyan-400">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <path d="M17 8h1a4 4 0 0 1 0 8h-1" />
          <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
        </svg>
      </div>
      <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Selecione uma conversa</h2>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        Escolha um chat na lista ao lado ou inicie uma nova conversa com um colega.
      </p>
    </div>
  )
}
