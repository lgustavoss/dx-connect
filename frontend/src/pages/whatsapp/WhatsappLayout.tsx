import { Outlet, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export function WhatsappLayout() {
  const loc = useLocation()
  const { user } = useAuth()

  if (/\/whatsapp\/c\//.test(loc.pathname)) {
    return (
      <div className="h-full w-full animate-in fade-in duration-300">
        <Outlet />
      </div>
    )
  }

  const isHistorico = loc.pathname.includes('/whatsapp/historico')
  const isAvaliacoes = loc.pathname.includes('/whatsapp/avaliacoes')
  const isAtendendo = !isHistorico && !isAvaliacoes

  const tabClass = (active: boolean) =>
    `flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-bold transition-all sm:px-6 ${
      active
        ? 'bg-white text-cyan-600 shadow-sm dark:bg-slate-700 dark:text-cyan-400'
        : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
    }`

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-10 pt-4 animate-in fade-in slide-in-from-top-1 duration-500">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-600 text-white shadow-lg shadow-cyan-600/20">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">WhatsApp</h1>
              <p className="text-sm font-medium text-slate-500">
                {isAvaliacoes
                  ? 'Chats com avaliação respondida pelos clientes'
                  : isHistorico
                    ? 'Consulta de sessões finalizadas e chats em aberto'
                    : 'Operação em tempo real'}
              </p>
            </div>
          </div>
        </div>

        <nav className="inline-flex max-w-full items-center overflow-x-auto rounded-xl bg-slate-100 p-1.5 dark:bg-slate-800/60 ring-1 ring-slate-200 dark:ring-slate-800">
          <Link to="/whatsapp/atendendo" className={tabClass(isAtendendo)}>
            {isAtendendo && (
              <span className="absolute -top-1 -right-1 flex h-2 w-2">
                <span className="absolute h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
                <span className="relative h-2 w-2 rounded-full bg-cyan-500" />
              </span>
            )}
            Atendimento
          </Link>
          <Link to="/whatsapp/historico" className={tabClass(isHistorico)}>
            Histórico
          </Link>
          {user?.role === 'admin' && (
            <Link to="/whatsapp/avaliacoes" className={tabClass(isAvaliacoes)}>
              Avaliações
            </Link>
          )}
        </nav>
      </div>

      <main className="relative min-h-[500px]">
        <Outlet />
      </main>
    </div>
  )
}
