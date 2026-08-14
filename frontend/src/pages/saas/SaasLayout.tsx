import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { BrandLogo } from '../../brand'
import { useAuth } from '../../contexts/AuthContext'
import { useTheme } from '../../contexts/ThemeContext'
import { ThemeToggle } from '../../components/ThemeToggle'
import { PageLoading } from '../../components/ui/PageLoading'
import { SemPermissao } from '../SemPermissao'
import { isSaasControlPlaneFrontend, SAAS_LICENCAS_PATH } from '../../lib/saasControlPlane'
import { system } from '../../api/client'

const menuIcon = (
  <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
    isActive
      ? 'bg-sky-50 text-sky-800 ring-1 ring-sky-600/20 dark:bg-sky-500/15 dark:text-sky-100 dark:ring-sky-400/30'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white',
  ].join(' ')

/**
 * Shell dedicado do control-plane SaaS — sem tickets/chat do painel de atendimento.
 * Respeita o tema claro/escuro (ThemeToggle), como o Layout de atendimento.
 */
export function SaasLayout() {
  const { user, loading, logout, isSaasOps } = useAuth()
  const { resolved } = useTheme()
  const location = useLocation()
  const [sidebarExpanded, setSidebarExpanded] = useState(true)
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false)
  const [planeOk, setPlaneOk] = useState<boolean | null>(null)
  const logoOnDark = resolved === 'dark'

  useEffect(() => {
    let cancelled = false
    if (isSaasControlPlaneFrontend()) {
      setPlaneOk(true)
      return () => {
        cancelled = true
      }
    }
    system
      .info()
      .then((info) => {
        if (!cancelled) setPlaneOk(Boolean(info.saas_control_plane))
      })
      .catch(() => {
        if (!cancelled) setPlaneOk(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading || planeOk === null) {
    return <PageLoading fullscreen label="Carregando painel SaaS…" />
  }
  if (!user) {
    return <Navigate to="/login/admin" replace state={{ from: location }} />
  }
  if (!isSaasOps) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-slate-50 p-6 dark:bg-slate-950">
        <SemPermissao
          title="Este painel é exclusivo da equipa SaaS DeskRudder."
          detail="Use o login do atendimento (/login) para tickets e chat, ou entre com a conta ops em /login/admin."
          voltarPara="/login"
          voltarLabel="Ir para login do atendimento"
        />
      </div>
    )
  }
  if (!planeOk) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-slate-50 p-6 dark:bg-slate-950">
        <SemPermissao
          title="Painel SaaS não disponível nesta instância."
          detail="Ative SAAS_CONTROL_PLANE no backend (e VITE_SAAS_CONTROL_PLANE no frontend em local)."
          voltarPara="/login/admin"
          voltarLabel="Voltar ao login admin"
        />
      </div>
    )
  }

  const sidebarW = sidebarExpanded ? '260px' : '80px'

  function handleLogout() {
    logout()
    window.location.replace('/login/admin')
  }

  return (
    <div
      className="flex h-dvh max-h-dvh min-h-0 overflow-hidden bg-gradient-to-b from-slate-50 to-slate-100/90 dark:from-slate-950 dark:to-slate-900/95 md:grid md:grid-cols-[var(--saas-sidebar-w)_minmax(0,1fr)] md:transition-[grid-template-columns] md:duration-200"
      style={{ ['--saas-sidebar-w' as string]: sidebarW }}
    >
      {sidebarMobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/40 dark:bg-black/60 md:hidden"
          aria-label="Fechar menu"
          onClick={() => setSidebarMobileOpen(false)}
        />
      ) : null}

      <aside
        className={[
          'z-50 flex h-full flex-col border-r border-slate-200 bg-white text-slate-800 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100',
          'fixed inset-y-0 left-0 w-[min(280px,88vw)] transition-transform md:static md:w-auto md:translate-x-0',
          sidebarMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        ].join(' ')}
      >
        <div
          className={`flex items-center gap-3 border-b border-slate-200 px-4 py-4 dark:border-slate-800 ${sidebarExpanded ? '' : 'md:justify-center'}`}
        >
          <BrandLogo
            variant={sidebarExpanded ? 'full' : 'mark'}
            size="sm"
            markVariant={logoOnDark ? 'onDark' : 'default'}
            className="min-w-0"
          />
        </div>
        <div
          className={`border-b border-slate-200 px-4 py-3 dark:border-slate-800 ${sidebarExpanded ? '' : 'md:px-2 md:text-center'}`}
        >
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-sky-700 dark:text-sky-300/90">
            {sidebarExpanded ? 'Painel admin SaaS' : 'SaaS'}
          </p>
          {sidebarExpanded ? (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">Licenças, planos e leads</p>
          ) : null}
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3" onClick={() => setSidebarMobileOpen(false)}>
          <NavLink to={SAAS_LICENCAS_PATH} className={navLinkClass} end={false}>
            <span className="truncate">{sidebarExpanded || sidebarMobileOpen ? 'Licenças' : 'Lic'}</span>
          </NavLink>
          <NavLink to="/saas/planos" className={navLinkClass}>
            <span className="truncate">{sidebarExpanded || sidebarMobileOpen ? 'Planos' : 'Plan'}</span>
          </NavLink>
          <NavLink to="/saas/leads" className={navLinkClass}>
            <span className="truncate">{sidebarExpanded || sidebarMobileOpen ? 'Leads comerciais' : 'Leads'}</span>
          </NavLink>
          <NavLink to="/saas/sobre" className={navLinkClass}>
            <span className="truncate">{sidebarExpanded || sidebarMobileOpen ? 'Sobre' : 'Info'}</span>
          </NavLink>
        </nav>
        <div className="border-t border-slate-200 p-3 dark:border-slate-800">
          {sidebarExpanded || sidebarMobileOpen ? (
            <div className="mb-3 px-1">
              <p className="truncate text-sm font-medium text-slate-900 dark:text-white">{user.nome}</p>
              <p className="truncate text-xs text-slate-500">Ops SaaS</p>
            </div>
          ) : null}
          <button
            type="button"
            onClick={handleLogout}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white"
          >
            {sidebarExpanded || sidebarMobileOpen ? 'Sair' : '⎋'}
          </button>
        </div>
      </aside>

      <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden md:col-start-2">
        <header className="z-30 flex h-16 shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-4 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:px-6">
          <button
            type="button"
            onClick={() => {
              if (typeof window !== 'undefined' && window.innerWidth >= 768) {
                setSidebarExpanded((e) => !e)
              } else {
                setSidebarMobileOpen((o) => !o)
              }
            }}
            className="flex size-10 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 md:size-9"
            aria-label="Abrir ou recolher menu"
          >
            {menuIcon}
          </button>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-200">
              Control-plane DeskRudder
            </p>
          </div>
          <ThemeToggle />
          <Link
            to="/login"
            className="hidden rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-slate-200 sm:inline"
          >
            Painel atendimento
          </Link>
        </header>
        <main className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
