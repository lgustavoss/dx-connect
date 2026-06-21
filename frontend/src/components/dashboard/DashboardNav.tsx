import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'

const VIEWS = [
  { id: 'geral', to: '/', label: 'Visão geral', end: true },
  { id: 'tickets', to: '/dashboard/tickets', label: 'Tickets', end: false },
  { id: 'chats', to: '/dashboard/chats', label: 'WhatsApp', end: false },
] as const

export type DashboardViewId = (typeof VIEWS)[number]['id']

const TAB_CLASS =
  'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 dark:focus:ring-offset-slate-950'

type DashboardNavProps = {
  actions?: ReactNode
}

export function dashboardViewFromPath(pathname: string): DashboardViewId {
  if (pathname.startsWith('/dashboard/tickets')) return 'tickets'
  if (pathname.startsWith('/dashboard/chats')) return 'chats'
  return 'geral'
}

export function DashboardNav({ actions }: DashboardNavProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <nav
        className="inline-flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-800/50"
        aria-label="Navegação entre dashboards"
      >
        {VIEWS.map((view) => (
          <NavLink
            key={view.id}
            to={view.to}
            end={view.end}
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
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  )
}
