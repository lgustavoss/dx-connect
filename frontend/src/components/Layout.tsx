import { useState } from 'react'
import { Outlet, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Sidebar } from './Sidebar'
import { ThemeToggle } from './ThemeToggle'

const menuIcon = (
  <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

export function Layout() {
  const { user, logout, isAdmin } = useAuth()
  const location = useLocation()
  const [sidebarExpanded, setSidebarExpanded] = useState(true)
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false)

  if (user?.must_change_password && location.pathname !== '/alterar-senha') {
    return <Navigate to="/alterar-senha" replace />
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100/90 dark:from-slate-950 dark:to-slate-900/95">
      <Sidebar
        expanded={sidebarExpanded}
        mobileOpen={sidebarMobileOpen}
        onMobileClose={() => setSidebarMobileOpen(false)}
        isAdmin={isAdmin ?? false}
        userNome={user?.nome ?? ''}
        userRole={user?.role ?? ''}
        onLogout={logout}
      />

      {/* Área principal: no mobile ocupa 100%; no desktop margem = largura do sidebar */}
      <div
        className={`min-h-screen transition-[margin-left] duration-200 ease-out ${
          sidebarExpanded ? 'md:ml-[280px]' : 'md:ml-[72px]'
        }`}
      >
          {/* Top bar: mobile-first, área de toque generosa */}
          <header className="sticky top-0 z-30 flex h-14 min-h-[56px] items-center gap-2 border-b border-slate-200/90 bg-white/95 px-4 shadow-sm backdrop-blur-sm dark:border-slate-800/90 dark:bg-slate-950/90 md:gap-3 md:px-6">
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
            
            {/* Logo DX Connect visível apenas no mobile */}
            <div className="flex items-center overflow-hidden rounded-lg gap-2 md:hidden">
              <img
                src="/dx-connect-mark.png"
                alt=""
                width={32}
                height={32}
                className="size-8 shrink-0 object-contain dark:brightness-0 dark:invert dark:opacity-95"
                decoding="async"
                aria-hidden
              />
              <span className="truncate text-sm font-semibold leading-tight">
                <span className="bg-gradient-to-r from-cyan-600 to-blue-600 bg-clip-text font-bold text-transparent">DX</span>
                <span className="font-medium text-slate-700 dark:text-slate-200"> Connect</span>
              </span>
            </div>
            
            <div className="min-w-0 flex-1" />
            <ThemeToggle />
            <div className="hidden min-w-0 text-right sm:block">
              <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{user?.nome}</p>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400">{user?.role}</p>
            </div>
          </header>

          <main className="p-4 md:p-6">
            <Outlet />
          </main>
      </div>
    </div>
  )
}
