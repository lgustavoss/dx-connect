import { NavLink, Outlet, useLocation } from 'react-router-dom'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-t-lg px-4 py-2 text-sm font-medium transition-colors ${
    isActive
      ? 'border border-b-0 border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
      : 'border border-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800/80'
  }`

export function WhatsappLayout() {
  const loc = useLocation()
  if (/\/whatsapp\/c\//.test(loc.pathname)) {
    return <Outlet />
  }
  return (
    <div className="mx-auto max-w-6xl space-y-4 pb-10">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Chats WhatsApp</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Fila de espera, seus atendimentos ativos e histórico de conversas encerradas.
        </p>
      </div>
      <div className="flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-700">
        <NavLink to="/whatsapp/fila" className={tabClass} end>
          Fila
        </NavLink>
        <NavLink to="/whatsapp/meus" className={tabClass}>
          Meus chats
        </NavLink>
        <NavLink to="/whatsapp/historico" className={tabClass}>
          Histórico
        </NavLink>
      </div>
      <Outlet />
    </div>
  )
}
