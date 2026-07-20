import { useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PortalAuthProvider, usePortalAuth } from '../../contexts/PortalAuthContext'
import { usePortalBranding } from '../../contexts/PortalBrandingContext'
import { PageLoading } from '../../components/ui/PageLoading'
import { PortalBrandLogo } from './PortalBrandLogo'
import { PortalChatWidget } from './PortalChatWidget'
import { PortalSidebar, readPortalSidebarExpanded, writePortalSidebarExpanded } from './PortalSidebar'

function perfilExibicao(tipo: string | undefined): string {
  if (tipo === 'socio') return 'Sócio'
  if (tipo === 'supervisor') return 'Supervisor'
  if (tipo === 'colaborador') return 'Colaborador'
  return tipo?.trim() || '—'
}

const menuIcon = (
  <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

function PortalShell() {
  const { user, loading, logout } = usePortalAuth()
  const branding = usePortalBranding()
  const location = useLocation()
  const isSocio = user?.tipo === 'socio'
  const [sidebarExpanded, setSidebarExpanded] = useState(readPortalSidebarExpanded)
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false)

  if (loading) {
    return <PageLoading fullscreen label="Carregando portal…" />
  }
  if (!user) {
    return <Navigate to="/portal/login" replace state={{ from: location }} />
  }
  if (user.must_change_password && location.pathname !== '/portal/trocar-senha') {
    return <Navigate to="/portal/trocar-senha" replace />
  }

  function handleLogout() {
    logout()
    window.location.replace('/portal/login')
  }

  function toggleSidebar() {
    if (typeof window !== 'undefined' && window.innerWidth >= 768) {
      setSidebarExpanded((prev) => {
        const next = !prev
        writePortalSidebarExpanded(next)
        return next
      })
    } else {
      setSidebarMobileOpen((o) => !o)
    }
  }

  const sidebarW = sidebarExpanded ? '280px' : '80px'
  const roleLabel = perfilExibicao(user.tipo)

  return (
    <>
      <div
        className="flex h-dvh max-h-dvh min-h-0 overflow-hidden bg-gradient-to-b from-slate-50 to-slate-100/90 md:grid md:grid-cols-[var(--portal-sidebar-w)_minmax(0,1fr)] md:transition-[grid-template-columns] md:duration-200 md:ease-out"
        style={{ ['--portal-sidebar-w' as string]: sidebarW }}
      >
        <PortalSidebar
          expanded={sidebarExpanded}
          mobileOpen={sidebarMobileOpen}
          isSocio={isSocio}
          userNome={user.nome}
          userRole={roleLabel}
          exibirMarcaDeskrudder={branding.exibir_marca_deskrudder}
          onLogout={handleLogout}
          onMobileClose={() => setSidebarMobileOpen(false)}
        />

        <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden md:col-start-2 md:row-start-1">
          <header
            className="z-30 flex h-16 min-h-[64px] shrink-0 items-center gap-2 border-b border-black/10 px-4 shadow-sm md:gap-3 md:px-6"
            style={{ backgroundColor: branding.cor_header, color: branding.cor_texto_header }}
          >
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors hover:bg-white/10 touch-manipulation md:size-9"
              style={{ color: branding.cor_texto_header }}
              aria-label="Abrir ou recolher menu"
              aria-expanded={sidebarMobileOpen || sidebarExpanded}
            >
              {menuIcon}
            </button>

            <div className="flex min-w-0 items-center overflow-hidden md:hidden">
              <PortalBrandLogo className="h-7 w-auto max-w-[9rem] object-contain" />
            </div>

            <div className="min-w-0 flex-1" />

            <div className="hidden min-w-0 text-right sm:block">
              <p className="truncate text-sm font-medium" style={{ color: branding.cor_texto_header }}>
                {user.nome}
              </p>
              <p className="truncate text-xs opacity-80" style={{ color: branding.cor_texto_header }}>
                {roleLabel}
              </p>
            </div>
          </header>

          <main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">
            <div className="mx-auto w-full max-w-4xl">
              <Outlet />
            </div>
          </main>
        </div>
      </div>

      <PortalChatWidget />
    </>
  )
}

export function PortalLayout() {
  return (
    <PortalAuthProvider>
      <PortalShell />
    </PortalAuthProvider>
  )
}
