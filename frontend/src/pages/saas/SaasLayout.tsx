import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { BrandLogo } from '../../brand'
import { useAuth } from '../../contexts/AuthContext'
import { useTheme } from '../../contexts/ThemeContext'
import { ThemeToggle } from '../../components/ThemeToggle'
import { PageLoading } from '../../components/ui/PageLoading'
import { SemPermissao } from '../SemPermissao'
import { isSaasControlPlaneFrontend, SAAS_LICENCAS_PATH } from '../../lib/saasControlPlane'
import { system } from '../../api/client'

const logoutIcon = (
  <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
)

const menuIcon = (
  <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

const chevronIcon = (
  <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
)

const usersIcon = (
  <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M17 20h5v-2a4 4 0 00-4-4h-1M9 20H4v-2a4 4 0 014-4h1m4-4a4 4 0 100-8 4 4 0 000 8zm6 4a3 3 0 100-6 3 3 0 000 6z"
    />
  </svg>
)

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
    isActive
      ? 'bg-sky-50 text-sky-800 ring-1 ring-sky-600/20 dark:bg-sky-500/15 dark:text-sky-100 dark:ring-sky-400/30'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white',
  ].join(' ')

function perfilExibicao(user: { role?: string; saas_setor_nomes?: string[] } | null | undefined): string {
  const nomes = (user?.saas_setor_nomes ?? []).map((n) => n.trim()).filter(Boolean)
  if (nomes.length > 0) return nomes.join(' · ')
  const role = user?.role
  if (role === 'admin') return 'Administrador'
  if (role === 'atendente') return 'Atendente'
  if (role === 'comercial') return 'Comercial'
  if (role === 'saas_ops') return 'Ops SaaS'
  return role?.trim() || '—'
}

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
  const equipePath =
    location.pathname.startsWith('/saas/usuarios') ||
    location.pathname.startsWith('/saas/setores') ||
    location.pathname.startsWith('/saas/conta')
  const [equipeOpen, setEquipeOpen] = useState(equipePath)
  const [planeOk, setPlaneOk] = useState<boolean | null>(null)
  const [versionLabel, setVersionLabel] = useState<string | null>(() => {
    const fromEnv =
      (import.meta.env.VITE_APP_VERSION_DISPLAY as string | undefined)?.trim() ||
      (import.meta.env.VITE_APP_VERSION as string | undefined)?.trim()
    return fromEnv ? (fromEnv.startsWith('v') ? fromEnv : `v${fromEnv}`) : null
  })
  const logoOnDark = resolved === 'dark'
  const cargoLabel = perfilExibicao(user)
  const menuExpandido = sidebarExpanded || sidebarMobileOpen

  useEffect(() => {
    if (equipePath) setEquipeOpen(true)
  }, [equipePath])

  useEffect(() => {
    let cancelled = false
    if (loading || user?.must_change_password) {
      return () => {
        cancelled = true
      }
    }
    system
      .info()
      .then((info) => {
        if (cancelled) return
        if (info.version_display) setVersionLabel(info.version_display)
        setPlaneOk(isSaasControlPlaneFrontend() || Boolean(info.saas_control_plane))
      })
      .catch(() => {
        if (!cancelled) setPlaneOk(isSaasControlPlaneFrontend())
      })
    return () => {
      cancelled = true
    }
  }, [loading, user?.must_change_password])

  if (loading) {
    return <PageLoading fullscreen label="Carregando painel SaaS…" />
  }
  if (!user) {
    return <Navigate to="/login/admin" replace state={{ from: location }} />
  }
  if (user.must_change_password) {
    return <Navigate to="/alterar-senha" replace />
  }
  if (!isSaasOps) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-slate-50 p-6 dark:bg-slate-950">
        <SemPermissao
          title="Este painel é exclusivo da equipe SaaS DeskRudder."
          detail="Use o login do atendimento (/login) para tickets e chat, ou entre com a conta ops em /login/admin."
          voltarPara="/login"
          voltarLabel="Ir para login do atendimento"
        />
      </div>
    )
  }
  if (planeOk === null) {
    return <PageLoading fullscreen label="Carregando painel SaaS…" />
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
          className={`flex h-16 min-h-[64px] shrink-0 items-center border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 ${sidebarExpanded ? 'px-4' : 'justify-center md:px-2'}`}
        >
          <BrandLogo
            variant={sidebarExpanded ? 'full' : 'mark'}
            size={sidebarExpanded ? 'sidebar' : 'sm'}
            markVariant={logoOnDark ? 'onDark' : 'default'}
            className={sidebarExpanded ? 'min-w-0 w-full' : 'min-w-0'}
          />
        </div>
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3" onClick={() => setSidebarMobileOpen(false)}>
          <NavLink to={SAAS_LICENCAS_PATH} className={navLinkClass} end={false}>
            <span className="truncate">{menuExpandido ? 'Licenças' : 'Lic'}</span>
          </NavLink>
          <NavLink to="/saas/planos" className={navLinkClass}>
            <span className="truncate">{menuExpandido ? 'Planos' : 'Plan'}</span>
          </NavLink>
          <NavLink to="/saas/leads" className={navLinkClass}>
            <span className="truncate">{menuExpandido ? 'Leads comerciais' : 'Leads'}</span>
          </NavLink>
          <NavLink to="/saas/solicitacoes" className={navLinkClass}>
            <span className="truncate">{menuExpandido ? 'Sugestões' : 'Sug'}</span>
          </NavLink>

          {menuExpandido ? (
            <div className="mt-2" onClick={(e) => e.stopPropagation()}>
              <button
                type="button"
                onClick={() => setEquipeOpen((o) => !o)}
                className={[
                  'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition touch-manipulation min-h-[44px]',
                  equipePath
                    ? 'text-slate-800 dark:text-slate-100'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white',
                ].join(' ')}
                aria-expanded={equipeOpen}
                aria-controls="saas-nav-equipe"
              >
                {usersIcon}
                <span className="min-w-0 flex-1 truncate">Equipe</span>
                <span className={`shrink-0 text-slate-400 transition-transform ${equipeOpen ? 'rotate-180' : ''}`}>
                  {chevronIcon}
                </span>
              </button>
              <ul
                id="saas-nav-equipe"
                className={`min-w-0 space-y-0.5 overflow-hidden transition-all duration-200 ${
                  equipeOpen ? 'mt-1 max-h-56 opacity-100' : 'max-h-0 opacity-0'
                }`}
                role="group"
              >
                <li className="min-w-0 border-l border-slate-200 pl-3 ml-4 dark:border-slate-700">
                  <NavLink
                    to="/saas/usuarios"
                    className={navLinkClass}
                    onClick={() => setSidebarMobileOpen(false)}
                  >
                    <span className="truncate">Usuários</span>
                  </NavLink>
                </li>
                <li className="min-w-0 border-l border-slate-200 pl-3 ml-4 dark:border-slate-700">
                  <NavLink
                    to="/saas/setores"
                    className={navLinkClass}
                    onClick={() => setSidebarMobileOpen(false)}
                  >
                    <span className="truncate">Setores</span>
                  </NavLink>
                </li>
                <li className="min-w-0 border-l border-slate-200 pl-3 ml-4 dark:border-slate-700">
                  <NavLink to="/saas/conta" className={navLinkClass} onClick={() => setSidebarMobileOpen(false)}>
                    <span className="truncate">Minha conta</span>
                  </NavLink>
                </li>
              </ul>
            </div>
          ) : (
            <>
              <div className="my-2 hidden border-t border-slate-200 dark:border-slate-800 md:block" />
              <NavLink to="/saas/usuarios" className={navLinkClass} title="Usuários">
                <span className="truncate">Usr</span>
              </NavLink>
              <NavLink to="/saas/setores" className={navLinkClass} title="Setores">
                <span className="truncate">Set</span>
              </NavLink>
              <NavLink to="/saas/conta" className={navLinkClass} title="Minha conta">
                <span className="truncate">Conta</span>
              </NavLink>
            </>
          )}
        </nav>
        <div className={`shrink-0 border-t border-slate-200 p-2 dark:border-slate-800 ${sidebarExpanded ? '' : 'md:px-2'}`}>
          {menuExpandido ? (
            <div className="flex items-center gap-3 px-3 py-2 text-slate-600 dark:text-slate-400">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 text-xs font-semibold text-white shadow-sm shadow-cyan-500/25">
                {user.nome?.charAt(0)?.toUpperCase() ?? '?'}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{user.nome}</p>
                <p className="truncate text-xs text-slate-500 dark:text-slate-400">{cargoLabel}</p>
              </div>
            </div>
          ) : null}
          <button
            type="button"
            onClick={handleLogout}
            title="Sair"
            className={`mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-slate-100 active:bg-slate-200 touch-manipulation min-h-[44px] dark:text-slate-400 dark:hover:bg-slate-800 dark:active:bg-slate-700 ${
              menuExpandido ? '' : 'md:justify-center md:px-2'
            }`}
          >
            {logoutIcon}
            <span className={menuExpandido ? 'min-w-0 truncate' : 'min-w-0 truncate md:hidden'}>Sair</span>
          </button>
          <NavLink
            to="/saas/sobre"
            title="Sobre / novidades"
            onClick={() => setSidebarMobileOpen(false)}
            className={({ isActive }) =>
              [
                'mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:hover:text-slate-200',
                menuExpandido ? '' : 'md:justify-center md:px-2',
                isActive ? 'bg-slate-100 text-slate-800 dark:bg-slate-800/80 dark:text-slate-100' : '',
              ].join(' ')
            }
          >
            <span className={`truncate ${menuExpandido ? '' : 'md:text-[10px]'}`}>
              {menuExpandido
                ? versionLabel
                  ? `Sobre · ${versionLabel}`
                  : 'Sobre'
                : versionLabel || 'Sobre'}
            </span>
          </NavLink>
        </div>
      </aside>

      <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden md:col-start-2">
        <header className="z-30 flex h-16 min-h-[64px] w-full shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-4 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:gap-3 md:px-6">
          <button
            type="button"
            onClick={() => {
              if (typeof window !== 'undefined' && window.innerWidth >= 768) {
                setSidebarExpanded((e) => !e)
              } else {
                setSidebarMobileOpen((o) => !o)
              }
            }}
            className="flex size-10 shrink-0 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 active:bg-slate-200 touch-manipulation dark:text-slate-300 dark:hover:bg-slate-800 md:size-9"
            aria-label="Abrir ou recolher menu"
          >
            {menuIcon}
          </button>
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-sm font-semibold uppercase tracking-[0.08em] text-sky-800 dark:text-sky-200">
              Painel admin SaaS
            </p>
            <p className="hidden truncate text-xs text-slate-500 dark:text-slate-400 sm:block">
              Licenças, planos, leads e sugestões
            </p>
          </div>
          <ThemeToggle />
          <div className="hidden min-w-0 max-w-[12rem] shrink text-right leading-tight sm:block md:max-w-[16rem]">
            <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{user.nome}</p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{cargoLabel}</p>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
