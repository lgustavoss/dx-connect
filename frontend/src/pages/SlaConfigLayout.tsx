import { NavLink, Outlet } from 'react-router-dom'

const SUB_TABS = [
  { to: '/configuracoes/equipa/sla/politicas', label: 'Políticas' },
  { to: '/configuracoes/equipa/sla/calendarios', label: 'Calendários' },
] as const

export function SlaConfigLayout() {
  return (
    <div className="space-y-4">
      <nav
        className="inline-flex flex-wrap rounded-2xl bg-slate-100/90 p-1 ring-1 ring-slate-200/60 dark:bg-slate-800/60 dark:ring-slate-700/80"
        aria-label="Seções de SLA"
      >
        {SUB_TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/80 dark:bg-slate-700 dark:text-slate-50 dark:ring-slate-600/50'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
