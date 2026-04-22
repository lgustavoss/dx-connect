import { Outlet, useLocation, Link } from 'react-router-dom'

export function WhatsappLayout() {
  const loc = useLocation()
  
  // Se estiver dentro de um chat específico, renderiza apenas o conteúdo (foco total)
  if (/\/whatsapp\/c\//.test(loc.pathname)) {
    return <Outlet />
  }

  const isHistorico = loc.pathname.includes('/whatsapp/historico')

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-10 animate-in fade-in duration-500">
      {/* Header Dinâmico */}
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            WhatsApp
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {isHistorico
              ? 'Consulte o registro completo de atendimentos finalizados.'
              : 'Gerencie sua fila de espera e conversas em andamento.'}
          </p>
        </div>

        {/* Navegação por Abas (Tabs) */}
        <nav className="flex items-center rounded-xl bg-slate-100 p-1 dark:bg-slate-800/50">
          <Link
            to="/whatsapp/atendendo"
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
              !isHistorico
                ? 'bg-white text-cyan-600 shadow-sm dark:bg-slate-700 dark:text-cyan-400'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${!isHistorico ? 'bg-cyan-500' : 'bg-transparent'}`} />
            Atendendo
          </Link>
          <Link
            to="/whatsapp/historico"
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
              isHistorico
                ? 'bg-white text-cyan-600 shadow-sm dark:bg-slate-700 dark:text-cyan-400'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${isHistorico ? 'bg-cyan-500' : 'bg-transparent'}`} />
            Histórico
          </Link>
        </nav>
      </div>

      {/* Área de Conteúdo com transição suave */}
      <div className="relative min-h-[400px]">
        <Outlet />
      </div>
    </div>
  )
}