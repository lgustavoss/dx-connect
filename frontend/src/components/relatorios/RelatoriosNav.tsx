import { NavLink } from 'react-router-dom'

const VIEWS = [
  { id: 'tickets', to: '/relatorios/tickets', label: 'Tickets' },
  { id: 'chats', to: '/relatorios/chats', label: 'Chats' },
] as const

const TAB_CLASS =
  'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 dark:focus:ring-offset-slate-950'

export function RelatoriosNav() {
  return (
    <nav
      className="mb-6 inline-flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-800/50"
      aria-label="Navegação entre relatórios"
    >
      {VIEWS.map((view) => (
        <NavLink
          key={view.id}
          to={view.to}
          className={({ isActive }) =>
            `${TAB_CLASS} ${
              isActive
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 shadow-sm'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            }`
          }
        >
          {view.label}
        </NavLink>
      ))}
    </nav>
  )
}
