import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'

const icons: Record<string, React.ReactNode> = {
  dashboard: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
  tickets: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
    </svg>
  ),
  clientes: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  ),
  redes: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  ),
  empresas: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  ),
  funcionarios: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  configuracoes: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  setores: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  ),
  atendentes: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  status: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
    </svg>
  ),
  logout: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
    </svg>
  ),
  menu: (
    <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  ),
  chevronDown: (
    <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  ),
  chevronRight: (
    <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
}

interface NavLink {
  to: string
  label: string
  icon: string
}

interface NavGroup {
  type: 'group'
  id: string
  label: string
  icon: string
  adminOnly?: boolean
  children: NavLink[]
}

interface NavItemLink {
  type: 'link'
  to: string
  label: string
  icon: string
}

type NavItem = NavItemLink | NavGroup

const navStructure: NavItem[] = [
  { type: 'link', to: '/', label: 'Dashboard', icon: 'dashboard' },
  { type: 'link', to: '/tickets', label: 'Tickets', icon: 'tickets' },
  {
    type: 'group',
    id: 'clientes',
    label: 'Clientes',
    icon: 'clientes',
    adminOnly: true,
    children: [
      { to: '/redes', label: 'Redes', icon: 'redes' },
      { to: '/empresas', label: 'Empresas', icon: 'empresas' },
      { to: '/funcionarios-rede', label: 'Funcionários da rede', icon: 'funcionarios' },
    ],
  },
  {
    type: 'group',
    id: 'configuracoes',
    label: 'Configurações',
    icon: 'configuracoes',
    adminOnly: true,
    children: [
      { to: '/setores', label: 'Setores', icon: 'setores' },
      { to: '/atendentes', label: 'Atendentes', icon: 'atendentes' },
      { to: '/tipos-negocio', label: 'Tipos de negócio', icon: 'configuracoes' },
      { to: '/status-ticket', label: 'Status de ticket', icon: 'status' },
      { to: '/auditoria', label: 'Auditoria', icon: 'configuracoes' },
    ],
  },
]

function isPathInGroup(pathname: string, children: NavLink[]): boolean {
  return children.some(
    (c) => pathname === c.to || (c.to !== '/' && pathname.startsWith(c.to))
  )
}

interface SidebarProps {
  expanded: boolean
  mobileOpen: boolean
  onMobileClose: () => void
  isAdmin: boolean
  userNome: string
  userRole: string
  onLogout: () => void
}

export function Sidebar({
  expanded,
  mobileOpen,
  onMobileClose,
  isAdmin,
  userNome,
  userRole,
  onLogout,
}: SidebarProps) {
  const location = useLocation()
  const [openGroup, setOpenGroup] = useState<string | null>(null)
  const [openFlyout, setOpenFlyout] = useState<string | null>(null)

  const items = navStructure.filter(
    (item) => item.type === 'link' || !('adminOnly' in item && item.adminOnly) || isAdmin
  ) as NavItem[]

  // Abrir grupo automaticamente quando a rota pertence a ele
  useEffect(() => {
    for (const item of navStructure) {
      if (item.type === 'group') {
        if (!item.adminOnly || isAdmin) {
          if (isPathInGroup(location.pathname, item.children)) {
            setOpenGroup(item.id)
            return
          }
        }
      }
    }
  }, [location.pathname, isAdmin])

  // No drawer mobile usamos acordeão (não flyout); evita estado do flyout “preso”
  useEffect(() => {
    if (mobileOpen) setOpenFlyout(null)
  }, [mobileOpen])

  const linkClass = (to: string, base = '') =>
    `${base} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors touch-manipulation min-h-[44px] ${
      location.pathname === to || (to !== '/' && location.pathname.startsWith(to))
        ? 'bg-cyan-50 text-slate-900 ring-1 ring-cyan-200/60 dark:bg-cyan-950/35 dark:text-slate-100 dark:ring-cyan-800/50'
        : 'text-slate-600 hover:bg-slate-100 active:bg-slate-200 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:active:bg-slate-800'
    } ${!expanded ? 'md:justify-center md:gap-0 md:px-2' : ''}`

  const isGroupOpen = (id: string) => openGroup === id
  const isFlyoutOpen = (id: string) => openFlyout === id

  const sidebarContent = (
    <>
      <div
        className={`flex h-14 shrink-0 items-center justify-center border-b border-slate-200 dark:border-slate-800 ${expanded ? 'px-3' : 'md:px-2'}`}
      >
        <Link
          to="/"
          onClick={onMobileClose}
          title="Início"
          className={`flex items-center overflow-hidden rounded-lg ${expanded ? 'min-w-0 flex-1 gap-2.5' : 'md:w-full md:justify-center md:gap-0'}`}
        >
          <img
            src="/dx-connect-mark.png"
            alt=""
            width={36}
            height={36}
            className="size-9 shrink-0 object-contain md:size-8 dark:brightness-0 dark:invert dark:opacity-95"
            decoding="async"
            aria-hidden
          />
          <span
            className={`min-w-0 truncate text-[0.95rem] font-semibold leading-tight transition-all duration-200 ${
              expanded ? 'opacity-100 w-auto' : 'md:hidden'
            }`}
          >
            <span className="bg-gradient-to-r from-cyan-600 to-blue-600 bg-clip-text font-bold text-transparent">DX</span>
            <span className="font-medium text-slate-700 dark:text-slate-200"> Connect</span>
          </span>
        </Link>
      </div>

      <nav
        className={`min-w-0 flex-1 overflow-y-auto py-3 px-2 max-md:overflow-x-hidden ${!expanded ? 'md:px-2' : ''}`}
        aria-label="Menu principal"
      >
        <ul className={`min-w-0 space-y-0.5 px-2 ${!expanded ? 'md:px-0' : ''}`}>
          {items.map((item) => {
            if (item.type === 'link') {
              return (
                <li key={item.to} className="w-full min-w-0">
                  <Link
                    to={item.to}
                    onClick={onMobileClose}
                    title={item.label}
                    className={linkClass(item.to)}
                  >
                    {icons[item.icon]}
                    <span
                      className={
                        expanded
                          ? 'min-w-0 truncate transition-all duration-200'
                          : 'min-w-0 truncate transition-all duration-200 md:hidden'
                      }
                    >
                      {item.label}
                    </span>
                  </Link>
                </li>
              )
            }

            // Group
            const group = item
            const open = isGroupOpen(group.id)
            const active = isPathInGroup(location.pathname, group.children)

            const menuExpandido = expanded || mobileOpen

            return (
              <li key={group.id} className="w-full min-w-0">
                {/* Mobile (drawer) ou desktop com menu largo: filhos abaixo. Desktop ícone: flyout à direita */}
                {menuExpandido ? (
                  <>
                    <button
                      type="button"
                      onClick={() => setOpenGroup(open ? null : group.id)}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors touch-manipulation min-h-[44px] ${
                        active
                          ? 'bg-cyan-50/80 text-slate-900 ring-1 ring-cyan-200/50 dark:bg-cyan-950/30 dark:text-slate-100 dark:ring-cyan-800/40'
                          : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800/80'
                      }`}
                      aria-expanded={open}
                      aria-controls={`nav-group-${group.id}`}
                    >
                      {icons[group.icon]}
                      <span className="truncate flex-1">{group.label}</span>
                      <span className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}>
                        {icons.chevronDown}
                      </span>
                    </button>
                    <ul
                      id={`nav-group-${group.id}`}
                      className={`min-w-0 overflow-hidden transition-all duration-200 ${open ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}
                      role="group"
                    >
                      {group.children.map((child) => (
                        <li key={child.to} className="min-w-0 pl-4">
                          <Link
                            to={child.to}
                            onClick={onMobileClose}
                            className={linkClass(child.to, 'flex')}
                          >
                            {icons[child.icon]}
                            <span className="truncate">{child.label}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  /* Desktop recolhido (md+): flyout à direita do ícone */
                  <div className="relative w-full min-w-0">
                    <button
                      type="button"
                      onClick={() => setOpenFlyout(isFlyoutOpen(group.id) ? null : group.id)}
                      title={group.label}
                      className={`flex w-full items-center justify-center rounded-lg py-2.5 text-slate-600 hover:bg-slate-100 min-h-[44px] px-2 dark:text-slate-400 dark:hover:bg-slate-800/80 md:px-0 ${
                        active ? 'bg-cyan-50 text-slate-900 ring-1 ring-cyan-200/60 dark:bg-cyan-950/35 dark:text-slate-100 dark:ring-cyan-800/50' : ''
                      }`}
                      aria-expanded={isFlyoutOpen(group.id)}
                      aria-haspopup="true"
                    >
                      {icons[group.icon]}
                    </button>
                    {isFlyoutOpen(group.id) && (
                      <>
                        <div
                          role="presentation"
                          className="fixed inset-0 z-40 md:left-[80px]"
                          onClick={() => setOpenFlyout(null)}
                        />
                        <ul
                          className="absolute left-full top-0 z-50 ml-1 min-w-[200px] rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
                          role="menu"
                        >
                          {group.children.map((child) => (
                            <li key={child.to} role="none">
                              <Link
                                to={child.to}
                                onClick={() => {
                                  onMobileClose()
                                  setOpenFlyout(null)
                                }}
                                className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                                role="menuitem"
                              >
                                {icons[child.icon]}
                                {child.label}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </nav>

      <div className={`border-t border-slate-200 p-2 dark:border-slate-800 ${!expanded ? 'md:px-2' : ''}`}>
        <div
          className={`flex items-center gap-3 px-3 py-2 text-slate-600 dark:text-slate-400 ${
            expanded ? 'opacity-100' : 'md:hidden'
          }`}
        >
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 text-xs font-semibold text-white shadow-sm shadow-cyan-500/25">
            {userNome?.charAt(0)?.toUpperCase() ?? '?'}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{userNome}</p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{userRole}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            onMobileClose()
            onLogout()
          }}
          title="Sair"
          className={`mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-slate-100 active:bg-slate-200 touch-manipulation min-h-[44px] dark:text-slate-400 dark:hover:bg-slate-800 dark:active:bg-slate-700 ${
            expanded ? '' : 'md:justify-center md:px-2'
          }`}
        >
          {icons.logout}
          <span
            className={
              expanded
                ? 'min-w-0 truncate transition-all duration-200'
                : 'min-w-0 truncate transition-all duration-200 md:hidden'
            }
          >
            Sair
          </span>
        </button>
      </div>
    </>
  )

  return (
    <>
      {/* Overlay mobile: bloqueia fundo (fullscreen) */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-200 md:hidden ${
          mobileOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        aria-hidden
      />

      {/* Sidebar: drawer no mobile, fixo no desktop */}
      <aside
        className={`fixed inset-0 z-50 flex h-full min-w-0 max-w-[100vw] flex-col overflow-x-hidden bg-white shadow-xl transition-[transform,width] duration-200 ease-out dark:bg-slate-950 md:inset-auto md:top-0 md:left-0 md:h-full md:max-w-none md:w-auto md:translate-x-0 md:overflow-x-visible md:shadow-none md:dark:shadow-[inset_-1px_0_0_0_rgb(30_41_59_/_0.6)] ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } ${expanded ? 'md:w-[280px]' : 'md:w-[80px]'}`}
        aria-label="Menu lateral"
      >
        {/* Mobile header com "voltar/fechar" */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200/90 bg-white/95 px-4 shadow-sm backdrop-blur-sm dark:border-slate-800/90 dark:bg-slate-950/90 md:hidden">
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">Menu</span>
          <button
            type="button"
            onClick={onMobileClose}
            className="inline-flex size-10 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 active:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800 dark:active:bg-slate-700"
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
