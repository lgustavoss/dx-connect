import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'
import { APP_NAME } from '../../brand'
import { PortalBrandLogo } from './PortalBrandLogo'

const STORAGE_KEY = 'portal-sidebar-expanded'
const COPYRIGHT_YEAR = new Date().getFullYear()

type NavItem = {
  to: string
  label: string
  end?: boolean
  icon: ReactNode
  socioOnly?: boolean
}

const icons = {
  tickets: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
    </svg>
  ),
  chats: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  ),
  users: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  help: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  novo: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  ),
  logout: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
    </svg>
  ),
}

const NAV_ITEMS: NavItem[] = [
  { to: '/portal/tickets', label: 'Chamados', end: true, icon: icons.tickets },
  { to: '/portal/chats', label: 'Atendimentos', end: true, icon: icons.chats },
  { to: '/portal/equipe', label: 'Usuários', icon: icons.users, socioOnly: true },
  { to: '/portal/ajuda', label: 'Ajuda', icon: icons.help },
]

export function readPortalSidebarExpanded(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== '0'
  } catch {
    return true
  }
}

export function writePortalSidebarExpanded(expanded: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, expanded ? '1' : '0')
  } catch {
    /* storage indisponível */
  }
}

type Props = {
  expanded: boolean
  mobileOpen: boolean
  isSocio: boolean
  userNome: string
  userRole: string
  exibirMarcaDeskrudder?: boolean
  onLogout: () => void
  onMobileClose: () => void
}

function NavItemLink({
  item,
  expanded,
  onNavigate,
}: {
  item: NavItem
  expanded: boolean
  onNavigate?: () => void
}) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={!expanded ? item.label : undefined}
      onClick={onNavigate}
      className={({ isActive }) =>
        [
          'flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors touch-manipulation',
          isActive
            ? 'bg-white/15 text-[var(--portal-sidebar-text)] ring-1 ring-white/25'
            : 'text-[var(--portal-sidebar-text)]/80 hover:bg-white/10 hover:text-[var(--portal-sidebar-text)]',
          !expanded ? 'md:justify-center md:gap-0 md:px-2' : '',
        ].join(' ')
      }
    >
      {item.icon}
      <span className={expanded ? 'min-w-0 truncate' : 'min-w-0 truncate md:hidden'}>{item.label}</span>
    </NavLink>
  )
}

export function PortalSidebar({
  expanded,
  mobileOpen,
  isSocio,
  userNome,
  userRole,
  exibirMarcaDeskrudder = true,
  onLogout,
  onMobileClose,
}: Props) {
  const items = NAV_ITEMS.filter((item) => !item.socioOnly || isSocio)
  const initial = userNome?.trim()?.charAt(0)?.toUpperCase() || '?'

  const sidebarContent = (
    <>
      <div
        className={`flex h-16 min-h-[64px] shrink-0 items-center border-b border-white/10 ${expanded ? 'px-3' : 'justify-center md:px-2'}`}
      >
        {expanded ? (
          <PortalBrandLogo className="h-8 w-auto max-w-[11rem] object-contain" />
        ) : (
          <PortalBrandLogo className="h-8 w-auto max-w-[2.5rem] object-contain md:mx-auto" />
        )}
      </div>

      <nav
        className={`dx-scrollbar min-w-0 flex-1 overflow-x-hidden overflow-y-auto py-3 px-2 ${!expanded ? 'md:px-2' : ''}`}
        aria-label="Menu do portal"
      >
        <ul className={`min-w-0 space-y-0.5 px-2 ${!expanded ? 'md:px-0' : ''}`}>
          {items.map((item) => (
            <li key={item.to} className="w-full min-w-0">
              <NavItemLink item={item} expanded={expanded} onNavigate={onMobileClose} />
            </li>
          ))}
          <li className="w-full min-w-0 pt-1">
            <NavLink
              to="/portal/tickets/novo"
              title={!expanded ? 'Novo chamado' : undefined}
              onClick={onMobileClose}
              className={({ isActive }) =>
                [
                  'flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors touch-manipulation',
                  isActive
                    ? 'bg-[var(--portal-primary)] text-white shadow-sm'
                    : 'border border-white/25 text-[var(--portal-sidebar-text)] hover:bg-white/10',
                  !expanded ? 'md:justify-center md:gap-0 md:px-2' : '',
                ].join(' ')
              }
            >
              {icons.novo}
              <span className={expanded ? 'min-w-0 truncate' : 'min-w-0 truncate md:hidden'}>
                Novo chamado
              </span>
            </NavLink>
          </li>
        </ul>
      </nav>

      <div className={`shrink-0 border-t border-white/10 p-2 ${!expanded ? 'md:px-2' : ''}`}>
        <div
          className={`flex items-center gap-3 px-3 py-2 ${expanded ? 'opacity-100' : 'md:hidden'}`}
          style={{ color: 'var(--portal-sidebar-text)' }}
        >
          <span
            className="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white shadow-sm"
            style={{ backgroundColor: 'var(--portal-primary)' }}
            aria-hidden
          >
            {initial}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{userNome}</p>
            <p className="truncate text-xs opacity-75">{userRole}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            onMobileClose()
            onLogout()
          }}
          title="Sair"
          className={[
            'mt-2 flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors hover:bg-white/10 active:bg-white/15 touch-manipulation',
            expanded ? '' : 'md:justify-center md:px-2',
          ].join(' ')}
          style={{ color: 'var(--portal-sidebar-text)' }}
        >
          {icons.logout}
          <span className={expanded ? 'min-w-0 truncate' : 'min-w-0 truncate md:hidden'}>Sair</span>
        </button>
        {exibirMarcaDeskrudder ? (
          <p
            className={[
              'mt-2 px-3 py-1 text-[11px] leading-snug opacity-60',
              expanded ? 'text-left' : 'md:px-1 md:text-center md:text-[9px]',
            ].join(' ')}
            style={{ color: 'var(--portal-sidebar-text)' }}
            title={APP_NAME}
          >
            {expanded ? (
              <>
                © {COPYRIGHT_YEAR} {APP_NAME}
              </>
            ) : (
              <>
                <span className="hidden md:inline">© {COPYRIGHT_YEAR}</span>
                <span className="md:hidden">
                  © {COPYRIGHT_YEAR} {APP_NAME}
                </span>
              </>
            )}
          </p>
        ) : null}
      </div>
    </>
  )

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-200 md:hidden ${
          mobileOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        aria-hidden
        onClick={onMobileClose}
      />

      <aside
        className={[
          'fixed inset-0 z-50 flex h-full min-w-0 max-w-[100vw] flex-col overflow-x-hidden shadow-xl transition-transform duration-200 ease-out',
          'md:sticky md:top-0 md:col-start-1 md:row-start-1 md:z-40 md:h-dvh md:max-h-dvh md:max-w-none md:w-full md:translate-x-0 md:self-start md:overflow-hidden md:border-r md:border-black/10 md:shadow-none',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        ].join(' ')}
        style={{
          backgroundColor: 'var(--portal-sidebar)',
          color: 'var(--portal-sidebar-text)',
        }}
        aria-label="Menu lateral"
      >
        <div
          className="flex h-14 shrink-0 items-center justify-between border-b border-white/10 px-4 md:hidden"
          style={{ backgroundColor: 'var(--portal-sidebar)' }}
        >
          <span className="text-sm font-semibold" style={{ color: 'var(--portal-sidebar-text)' }}>
            Menu
          </span>
          <button
            type="button"
            onClick={onMobileClose}
            className="inline-flex size-10 items-center justify-center rounded-lg hover:bg-white/10"
            style={{ color: 'var(--portal-sidebar-text)' }}
            aria-label="Fechar menu"
          >
            ×
          </button>
        </div>
        {sidebarContent}
      </aside>
    </>
  )
}
