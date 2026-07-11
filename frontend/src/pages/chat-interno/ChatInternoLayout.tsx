import { Link, Outlet, useLocation } from 'react-router-dom'

export function ChatInternoLayout() {
  const loc = useLocation()
  const emThread = /\/chat-interno\/(setor\/\d+|\d+)/.test(loc.pathname)

  if (emThread) {
    return (
      <div className="h-full w-full animate-in fade-in duration-300">
        <Outlet />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-10 pt-2 animate-in fade-in slide-in-from-top-1 duration-500">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 dark:border-slate-800 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-white shadow-lg shadow-violet-600/20">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M17 8h1a4 4 0 0 1 0 8h-1" />
              <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
              <line x1="6" x2="6" y1="2" y2="4" />
              <line x1="10" x2="10" y1="2" y2="4" />
              <line x1="14" x2="14" y1="2" y2="4" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">Chat interno</h1>
            <p className="text-sm font-medium text-slate-500">Conversas entre atendentes e comunicados por setor</p>
          </div>
        </div>
        <Link
          to="/chat-interno"
          className="text-sm font-semibold text-violet-600 hover:text-violet-700 dark:text-violet-400"
        >
          Atualizar inbox
        </Link>
      </header>
      <Outlet />
    </div>
  )
}
