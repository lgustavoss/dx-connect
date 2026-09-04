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
import { isCapacitorNative } from '../lib/capacitorNative'
import { AlertaDesktopPermissaoBanner } from './AlertaDesktopPermissaoBanner'
import { AlertaFilaAudioBanner } from './AlertaFilaAudioBanner'
import { PwaInstallBanner } from './PwaInstallBanner'
import { WebPushOptInBanner } from './WebPushOptInBanner'
import { PontoAlertasBanner } from './PontoAlertasBanner'
import { useVisualViewportCss } from '../hooks/useVisualViewportCss'
import { useWebPushSession } from '../hooks/useWebPush'
import { lerTicketAtivoSession, TICKET_ATIVO_EVENT } from '../lib/ticketAtivo'
import { CHAT_ATIVO_EVENT, lerChatAtivoSession } from '../lib/chatAtivo'

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
  const { user, logout, isAdmin, isComercialOuAdmin, isFinanceiroOuAdmin } = useAuth()
  const { subscribe } = useEventStream()
  const location = useLocation()
  useVisualViewportCss()
  const [sidebarExpanded, setSidebarExpanded] = useState(true)
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false)
  const { resolved } = useTheme()
  const logoOnDark = resolved === 'dark'

  const notificacoesEnabled = Boolean(user && !user.must_change_password)
  useAlertaFilaSemResponsavel(notificacoesEnabled)
  useWebPushSession(notificacoesEnabled)

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
  const naListaTickets = location.pathname === '/tickets' || location.pathname === '/tickets/'
  const [ticketDetalheAberto, setTicketDetalheAberto] = useState(
    () => naListaTickets && lerTicketAtivoSession() != null,
  )
  useEffect(() => {
    const sync = () => {
      const naLista = location.pathname === '/tickets' || location.pathname === '/tickets/'
      setTicketDetalheAberto(naLista && lerTicketAtivoSession() != null)
    }
    sync()
    window.addEventListener(TICKET_ATIVO_EVENT, sync)
    return () => window.removeEventListener(TICKET_ATIVO_EVENT, sync)
  }, [location.pathname])

  /** Conversa aberta no hub — ocultar chrome da app só no celular (#753 / #S202608-0007). */
  const [chatDetalheAberto, setChatDetalheAberto] = useState(
    () => isChatHub && lerChatAtivoSession() != null,
  )
  useEffect(() => {
    const sync = () => {
      const noHub = location.pathname.startsWith('/chat')
      const setorInterno = /\/chat\/interno\/setor\/\d+/.test(location.pathname)
      setChatDetalheAberto(noHub && (lerChatAtivoSession() != null || setorInterno))
    }
    sync()
    window.addEventListener(CHAT_ATIVO_EVENT, sync)
    return () => window.removeEventListener(CHAT_ATIVO_EVENT, sync)
  }, [location.pathname])

  const ocultarHeaderMobile = chatDetalheAberto
  const scrollInternoNaPagina =
    /^\/tickets\/\d+\/?$/.test(location.pathname) ||
    location.pathname === '/tickets/novo' ||
    ticketDetalheAberto ||
    isChatHub ||
    location.pathname === '/sobre/nova-solicitacao'

  return (
    <div
      className="grid h-[var(--vv-height,100dvh)] max-h-[var(--vv-height,100dvh)] min-h-0 w-full min-w-0 grid-cols-1 overflow-hidden bg-gradient-to-b from-slate-50 to-slate-100/90 dark:from-slate-950 dark:to-slate-900/95 md:grid-cols-[var(--sidebar-w)_minmax(0,1fr)] md:transition-[grid-template-columns] md:duration-200 md:ease-out"
      style={
        {
          ['--sidebar-w' as never]: sidebarW,
          marginTop: 'var(--vv-offset-top, 0px)',
          paddingTop: isCapacitorNative() ? 'env(safe-area-inset-top, 0px)' : undefined,
        } as React.CSSProperties
      }
    >
      <Sidebar
        expanded={sidebarExpanded}
        mobileOpen={sidebarMobileOpen}
        onMobileClose={() => setSidebarMobileOpen(false)}
        isAdmin={isAdmin ?? false}
        isComercialOuAdmin={isComercialOuAdmin ?? false}
        isFinanceiroOuAdmin={isFinanceiroOuAdmin ?? false}
        userNome={user?.nome ?? ''}
        userRole={perfilExibicao(user?.role)}
        onLogout={logout}
      />

      <div className="flex h-full min-h-0 min-w-0 w-full flex-col overflow-hidden md:col-start-2 md:row-start-1">
        {/* Com conversa aberta, esconde a barra só no celular (#996 / #S202608-0007). */}
        <header
          className={`z-30 flex h-16 min-h-[64px] w-full min-w-0 shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-4 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:gap-3 md:px-6 ${
            ocultarHeaderMobile ? 'max-md:hidden' : ''
          }`}
        >
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
          <div className="hidden min-w-0 max-w-[7rem] shrink text-right sm:block md:max-w-[10rem] lg:max-w-none">
            <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{user?.nome}</p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{perfilExibicao(user?.role)}</p>
          </div>
        </header>

        {notificacoesEnabled && !isCapacitorNative() && !ocultarHeaderMobile ? <PwaInstallBanner enabled /> : null}
        {notificacoesEnabled && !ocultarHeaderMobile ? <AlertaDesktopPermissaoBanner enabled /> : null}
        {notificacoesEnabled && !ocultarHeaderMobile ? <AlertaFilaAudioBanner enabled /> : null}
        {notificacoesEnabled && !ocultarHeaderMobile ? <WebPushOptInBanner enabled /> : null}
        <PontoAlertasBanner />

        <main className="min-h-0 min-w-0 w-full flex-1 overflow-hidden">
          <div
            className={
              scrollInternoNaPagina
                ? isChatHub
                  ? 'flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden'
                  : 'flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden px-4 pt-4 md:px-6 md:pt-6'
                : 'dx-scrollbar h-full min-h-0 w-full min-w-0 overflow-x-hidden overflow-y-auto p-4 md:p-6'
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
