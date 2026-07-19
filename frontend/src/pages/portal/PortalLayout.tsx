import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { PortalAuthProvider, usePortalAuth } from '../../contexts/PortalAuthContext'
import { PageLoading } from '../../components/ui/PageLoading'
import { BrandLogo } from '../../brand'

function PortalShell() {
  const { user, loading, logout } = usePortalAuth()
  const location = useLocation()

  if (loading) {
    return <PageLoading fullscreen label="Carregando portal…" />
  }
  if (!user) {
    return <Navigate to="/portal/login" replace state={{ from: location }} />
  }
  if (user.must_change_password && location.pathname !== '/portal/trocar-senha') {
    return <Navigate to="/portal/trocar-senha" replace />
  }

  const navClass = ({ isActive }: { isActive: boolean }) =>
    [
      'flex flex-1 flex-col items-center gap-0.5 rounded-xl px-2 py-2 text-[11px] font-medium transition-colors sm:flex-none sm:flex-row sm:gap-2 sm:px-3 sm:py-2 sm:text-sm',
      isActive
        ? 'bg-teal-600 text-white shadow-sm'
        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
    ].join(' ')

  return (
    <div className="portal-cliente flex min-h-dvh flex-col bg-gradient-to-b from-slate-50 via-white to-teal-50/40">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-3 px-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <BrandLogo className="h-8 w-auto shrink-0" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900">Portal do cliente</p>
              <p className="truncate text-xs text-slate-500">{user.nome}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              logout()
              window.location.replace('/portal/login')
            }}
            className="shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            Sair
          </button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-5 pb-24 sm:pb-8">
        <Outlet />
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200/80 bg-white/95 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1.5 backdrop-blur-md sm:static sm:mx-auto sm:mb-6 sm:max-w-3xl sm:rounded-2xl sm:border sm:px-3 sm:py-2 sm:shadow-sm"
        aria-label="Navegação do portal"
      >
        <div className="mx-auto flex max-w-3xl items-stretch justify-around gap-1 sm:justify-start sm:gap-2">
          <NavLink to="/portal/tickets" end className={navClass}>
            Chamados
          </NavLink>
          <NavLink to="/portal/tickets/novo" className={navClass}>
            Novo
          </NavLink>
          <NavLink to="/portal/ajuda" className={navClass}>
            Ajuda
          </NavLink>
        </div>
      </nav>
    </div>
  )
}

export function PortalLayout() {
  return (
    <PortalAuthProvider>
      <PortalShell />
    </PortalAuthProvider>
  )
}
