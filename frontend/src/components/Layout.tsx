import { useEffect, useState } from 'react'
import { Outlet, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Sidebar } from './Sidebar'
import { ThemeToggle } from './ThemeToggle'
import { NavbarNotificacoes } from './NavbarNotificacoes'
import { useAlertaFilaSemResponsavel, setChatInternoAlertUserId } from '../hooks/useAlertaFilaSemResponsavel'
import { EventStreamProvider, useEventStream } from '../contexts/EventStreamContext'
import { BrandLogo } from '../brand'
import { useTheme } from '../contexts/ThemeContext'
import { AlertaDesktopPermissaoBanner } from './AlertaDesktopPermissaoBanner'

function perfilExibicao(role: string | undefined): string {
  if (role === 'admin') return 'Administrador'
  if (role === 'atendente') return 'Atendente'
  if (role === 'comercial') return 'Comercial'
  if (role === 'saas_ops') return 'Ops SaaS'
  return role?.trim() || '—'
}

const menuIcon = (
  <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

function LayoutInner() {
  const { user, logout, isAdmin, isComercialOuAdmin } = useAuth()
  const { subscribe } = useEventStream()
  const location = useLocation()
  const [sidebarExpanded, setSidebarExpanded] = useState(true)
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false)
  const { resolved } = useTheme()
  const logoOnDark = resolved === 'dark'

  const notificacoesEnabled = Boolean(user && !user.must_change_password)
  useAlertaFilaSemResponsavel(notificacoesEnabled)

  useEffect(() => {
    setChatInternoAlertUserId(user?.id ?? null)
    return () => setChatInternoAlertUserId(null)
  }, [user?.id])

  useEffect(() => {
    return subscribe('sessao.encerrada', () => {
      logout()
    })
  }, [subscribe, logout])

  if (user?.must_change_password && location.pathname !== '/alterar-senha') {
    return <Navigate to="/alterar-senha" replace />
  }

  const sidebarW = sidebarExpanded ? '280px' : '80px'
  const isChatHub = location.pathname.startsWith('/chat')
  const scrollInternoNaPagina =
    /^\/tickets\/\d+\/?$/.test(location.pathname) ||
    location.pathname === '/tickets/novo' ||
    isChatHub

  return (
    <div
      className="flex h-dvh max-h-dvh min-h-0 overflow-hidden bg-gradient-to-b from-slate-50 to-slate-100/90 dark:from-slate-950 dark:to-slate-900/95 md:grid md:grid-cols-[var(--sidebar-w)_minmax(0,1fr)] md:transition-[grid-template-columns] md:duration-200 md:ease-out"
      style={
        {
          ['--sidebar-w' as never]: sidebarW,
        } as React.CSSProperties
      }
    >
      <Sidebar
        expanded={sidebarExpanded}
        mobileOpen={sidebarMobileOpen}
        onMobileClose={() => setSidebarMobileOpen(false)}
        isAdmin={isAdmin ?? false}
        isComercialOuAdmin={isComercialOuAdmin ?? false}
        userNome={user?.nome ?? ''}
        userRole={perfilExibicao(user?.role)}
        onLogout={logout}
      />

      <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden md:col-start-2 md:row-start-1">
          <header className="z-30 flex h-16 min-h-[64px] shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-4 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:gap-3 md:px-6">
            <button
              type="button"
              onClick={() => {
                if (typeof window !== 'undefined' && window.innerWidth >= 768) {
                  setSidebarExpanded((e) => !e)
                } else {
                  setSidebarMobileOpen((o) => !o)
                }
              }}
              className="flex size-10 shrink-0 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 active:bg-slate-200 dark:text-slate-400 dark:hover:bg-slate-800 dark:active:bg-slate-700 touch-manipulation md:size-9"
              aria-label="Abrir ou recolher menu"
              aria-expanded={sidebarMobileOpen}
            >
              {menuIcon}
            </button>

            <div className="flex items-center gap-2 overflow-hidden rounded-lg md:hidden">
              <BrandLogo variant="full" size="sm" markVariant={logoOnDark ? 'onDark' : 'default'} className="min-w-0" />
            </div>

            <div className="min-w-0 flex-1" />
            <NavbarNotificacoes enabled={notificacoesEnabled} />
            <ThemeToggle />
            <div className="hidden min-w-0 text-right sm:block">
              <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{user?.nome}</p>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400">{perfilExibicao(user?.role)}</p>
            </div>
          </header>

          {notificacoesEnabled ? <AlertaDesktopPermissaoBanner enabled /> : null}

          <main className="min-h-0 flex-1 overflow-hidden">
            <div
              className={
                scrollInternoNaPagina
                  ? isChatHub
                    ? 'flex h-full min-h-0 flex-col overflow-hidden'
                    : 'flex h-full min-h-0 flex-col overflow-hidden px-4 pt-4 md:px-6 md:pt-6'
                  : 'h-full min-h-0 overflow-x-hidden overflow-y-auto p-4 md:p-6'
              }
            >
              <Outlet />
            </div>
          </main>
      </div>
    </div>
  )
}

export function Layout() {
  const { user } = useAuth()
  const notificacoesEnabled = Boolean(user && !user.must_change_password)

  return (
    <EventStreamProvider enabled={notificacoesEnabled}>
      <LayoutInner />
    </EventStreamProvider>
  )
}
