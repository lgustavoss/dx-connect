import { Outlet, useLocation, Link } from 'react-router-dom'

export function WhatsappLayout() {
  const loc = useLocation()
  
  // Foco total: Se estiver dentro de um chat específico, removemos a moldura do layout
  if (/\/whatsapp\/c\//.test(loc.pathname)) {
    return (
      <div className="h-full w-full animate-in fade-in duration-300">
        <Outlet />
      </div>
    )
  }

  const isHistorico = loc.pathname.includes('/whatsapp/historico')

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-10 pt-4 animate-in fade-in slide-in-from-top-1 duration-500">
      
      {/* Header e Navegação */}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-600 text-white shadow-lg shadow-cyan-600/20">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                WhatsApp
              </h1>
              <p className="text-sm font-medium text-slate-500">
                {isHistorico ? 'Revisão de atendimentos passados' : 'Operação em tempo real'}
              </p>
            </div>
          </div>
        </div>

        {/* Tabs de Navegação Estilo Segmented Control */}
        <nav className="inline-flex items-center rounded-xl bg-slate-100 p-1.5 dark:bg-slate-800/60 ring-1 ring-slate-200 dark:ring-slate-800">
          <Link
            to="/whatsapp/atendendo"
            className={`relative flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-bold transition-all ${
              !isHistorico
                ? 'bg-white text-cyan-600 shadow-sm dark:bg-slate-700 dark:text-cyan-400'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            {!isHistorico && (
              <span className="absolute -top-1 -right-1 flex h-2 w-2">
                <span className="absolute h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative h-2 w-2 rounded-full bg-cyan-500"></span>
              </span>
            )}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 9a2 2 0 0 1-2 2H6l-4 4V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/><path d="M18 9h2a2 2 0 0 1 2 2v11l-4-4h-6a2 2 0 0 1-2-2v-1"/></svg>
            Atendimento
          </Link>

          <Link
            to="/whatsapp/historico"
            className={`flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-bold transition-all ${
              isHistorico
                ? 'bg-white text-cyan-600 shadow-sm dark:bg-slate-700 dark:text-cyan-400'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Histórico
          </Link>
        </nav>
      </div>

      {/* Conteúdo Renderizado */}
      <main className="relative min-h-[500px]">
        <Outlet />
      </main>
    </div>
  )
}
