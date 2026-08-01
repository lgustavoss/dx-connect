import { useState, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation } from 'react-router-dom'
import { system } from '../api/client'
import { BrandLogo } from '../brand'
import { useTheme } from '../contexts/ThemeContext'

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
  chat: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
      />
    </svg>
  ),
  chatInbox: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M20 13V7a2 2 0 00-2-2H6a2 2 0 00-2 2v6m16 0v3a2 2 0 01-2 2H6a2 2 0 01-2-2v-3m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
      />
    </svg>
  ),
  chatHistory: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  equipeOnline: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
      />
    </svg>
  ),
  whatsapp: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
      />
    </svg>
  ),
  auditoria: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  ),
  saas: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
      />
    </svg>
  ),
  tiposNegocio: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
      />
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
  notificacoes: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.75}
        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
      />
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
  ajuda: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
      />
    </svg>
  ),
  ajudaConsultar: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  ),
  ajudaCategorias: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
      />
    </svg>
  ),
  ajudaArtigos: (
    <svg className="size-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
      />
    </svg>
  ),
}

interface NavLink {
  to: string
  label: string
  icon: string
  adminOnly?: boolean
  /** Só na instância comercial (control-plane SaaS). */
  saasOnly?: boolean
}

interface NavGroup {
  type: 'group'
  id: string
  label: string
  icon: string
  adminOnly?: boolean
  saasOnly?: boolean
  /** Ex.: conversa aberta `/whatsapp/c/:id` mantém o grupo Chat ativo */
  extraActivePrefixes?: string[]
  children: NavLink[]
}

interface NavItemLink {
  type: 'link'
  to: string
  label: string
  icon: string
  /** Mantém o item ativo em rotas filhas (ex.: `/chat/c/:id`) */
  activePrefix?: string
  adminOnly?: boolean
  saasOnly?: boolean
}

type NavItem = NavItemLink | NavGroup

const navStructure: NavItem[] = [
  { type: 'link', to: '/', label: 'Dashboard', icon: 'dashboard' },
  {
    type: 'link',
    to: '/equipe/online',
    label: 'Equipe online',
    icon: 'equipeOnline',
    adminOnly: true,
  },
  { type: 'link', to: '/tickets', label: 'Tickets', icon: 'tickets' },
  { type: 'link', to: '/chat/atendendo', label: 'Chat', icon: 'chat', activePrefix: '/chat/' },
  { type: 'link', to: '/whatsapp/historico', label: 'Atendimentos', icon: 'chatHistory' },
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
    id: 'ajuda',
    label: 'Ajuda',
    icon: 'ajuda',
    extraActivePrefixes: ['/ajuda/artigos/', '/ajuda/categorias'],
    children: [
      { to: '/ajuda/consultar', label: 'Consultar', icon: 'ajudaConsultar' },
      { to: '/ajuda/categorias', label: 'Categorias', icon: 'ajudaCategorias', adminOnly: true },
      { to: '/ajuda/artigos', label: 'Artigos', icon: 'ajudaArtigos', adminOnly: true },
    ],
  },
  {
    type: 'group',
    id: 'configuracoes',
    label: 'Configurações',
    icon: 'configuracoes',
    adminOnly: true,
    extraActivePrefixes: [
      '/configuracoes/',
      '/setores',
      '/atendentes',
      '/status-ticket',
      '/respostas-prontas',
      '/tipos-negocio',
      '/auditoria',
    ],
    children: [
      { to: '/configuracoes/atendimento', label: 'Atendimento', icon: 'setores' },
      { to: '/configuracoes/cadastros', label: 'Cadastros', icon: 'tiposNegocio' },
      { to: '/configuracoes/sistema', label: 'Sistema', icon: 'configuracoes' },
    ],
  },
]

function navGroupMatchesPath(pathname: string, group: NavGroup): boolean {
  if (
    group.children.some((c) => pathname === c.to || (c.to !== '/' && pathname.startsWith(c.to)))
  ) {
    return true
  }
  return group.extraActivePrefixes?.some((prefix) => pathname.startsWith(prefix)) ?? false
}

function navChildrenVisible(children: NavLink[], isAdmin: boolean, saasEnabled: boolean): NavLink[] {
  return children.filter((child) => {
    if (child.adminOnly && !isAdmin) return false
    if (child.saasOnly && !saasEnabled) return false
    return true
  })
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
  const { resolved } = useTheme()
  const logoOnDark = resolved === 'dark'
  const [openGroup, setOpenGroup] = useState<string | null>(null)
  const [openFlyout, setOpenFlyout] = useState<string | null>(null)
  const [flyoutTop, setFlyoutTop] = useState<number | null>(null)
  const [versionLabel, setVersionLabel] = useState<string | null>(() => {
    const fromEnv =
      (import.meta.env.VITE_APP_VERSION_DISPLAY as string | undefined)?.trim() ||
      (import.meta.env.VITE_APP_VERSION as string | undefined)?.trim()
    return fromEnv ? (fromEnv.startsWith('v') ? fromEnv : `v${fromEnv}`) : null
  })
  const [saasEnabled, setSaasEnabled] = useState(false)

  useEffect(() => {
    let cancelled = false
    system
      .info()
      .then((info) => {
        if (cancelled) return
        if (info.version_display) setVersionLabel(info.version_display)
        setSaasEnabled(Boolean(info.saas_control_plane))
      })
      .catch(() => {
        /* fallback: env ou oculto */
      })
    return () => {
      cancelled = true
    }
  }, [])

  const closeFlyout = useCallback(() => {
    setOpenFlyout(null)
    setFlyoutTop(null)
  }, [])

  const toggleFlyout = useCallback(
    (groupId: string, anchorTop: number) => {
      if (openFlyout === groupId) {
        closeFlyout()
        return
      }
      setOpenFlyout(groupId)
      setFlyoutTop(anchorTop)
    },
    [closeFlyout, openFlyout]
  )

  const items = navStructure.filter((item) => {
    if ('adminOnly' in item && item.adminOnly && !isAdmin) return false
    if ('saasOnly' in item && item.saasOnly && !saasEnabled) return false
    return true
  }) as NavItem[]

  // Abrir grupo automaticamente quando a rota pertence a ele
  useEffect(() => {
    for (const item of navStructure) {
      if (item.type === 'group') {
        if ((!item.adminOnly || isAdmin) && (!item.saasOnly || saasEnabled)) {
          if (navGroupMatchesPath(location.pathname, item)) {
            setOpenGroup(item.id)
            return
          }
        }
      }
    }
  }, [location.pathname, isAdmin, saasEnabled])

  // No drawer mobile usamos acordeão (não flyout); evita estado do flyout “preso”
  useEffect(() => {
    if (mobileOpen) closeFlyout()
  }, [mobileOpen, closeFlyout])

  useEffect(() => {
    if (!openFlyout) return
    const onViewportChange = () => closeFlyout()
    window.addEventListener('resize', onViewportChange)
    window.addEventListener('scroll', onViewportChange, true)
    return () => {
      window.removeEventListener('resize', onViewportChange)
      window.removeEventListener('scroll', onViewportChange, true)
    }
  }, [closeFlyout, openFlyout])

  const isLinkActive = (to: string, activePrefix?: string) => {
    if (location.pathname === to) return true
    if (activePrefix && location.pathname.startsWith(activePrefix)) return true
    if (to !== '/' && location.pathname.startsWith(`${to}/`)) return true
    return false
  }

  const linkClass = (to: string, activePrefix?: string, base = '') =>
    `${base} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors touch-manipulation min-h-[44px] ${
      isLinkActive(to, activePrefix)
        ? 'bg-cyan-50 text-slate-900 ring-1 ring-cyan-200/60 dark:bg-cyan-950/35 dark:text-slate-100 dark:ring-cyan-800/50'
        : 'text-slate-600 hover:bg-slate-100 active:bg-slate-200 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:active:bg-slate-800'
    } ${!expanded ? 'md:justify-center md:gap-0 md:px-2' : ''}`

  const isGroupOpen = (id: string) => openGroup === id
  const isFlyoutOpen = (id: string) => openFlyout === id

  const openFlyoutGroup = openFlyout
    ? items.find((item): item is NavGroup => item.type === 'group' && item.id === openFlyout)
    : null

  const flyoutPortal =
    openFlyoutGroup && flyoutTop != null && typeof document !== 'undefined'
      ? createPortal(
          <>
            <div
              role="presentation"
              className="fixed inset-0 z-40 md:left-[var(--sidebar-w,80px)]"
              onClick={closeFlyout}
            />
            <ul
              className="fixed z-50 min-w-[200px] rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-slate-800"
              style={{
                left: 'calc(var(--sidebar-w, 80px) + 4px)',
                top: flyoutTop,
              }}
              role="menu"
            >
              {navChildrenVisible(openFlyoutGroup.children, isAdmin, saasEnabled).map((child) => (
                <li key={child.to} role="none">
                  <Link
                    to={child.to}
                    onClick={() => {
                      onMobileClose()
                      closeFlyout()
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
          </>,
          document.body
        )
      : null

  const sidebarContent = (
    <>
      <div
        className={`flex h-16 min-h-[64px] shrink-0 items-center border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 ${expanded ? 'px-3' : 'justify-center md:px-2'}`}
      >
        <Link
          to="/"
          onClick={onMobileClose}
          title="Início"
          className={`flex items-center overflow-visible rounded-lg ${expanded ? 'min-w-0 w-full' : 'md:w-full md:justify-center'}`}
        >
          {expanded ? (
            <BrandLogo variant="full" size="sidebar" markVariant={logoOnDark ? 'onDark' : 'default'} className="min-w-0 w-full" />
          ) : (
            <BrandLogo variant="mark" size="sm" markVariant={logoOnDark ? 'onDark' : 'default'} className="md:mx-auto" />
          )}
        </Link>
      </div>

      <nav
        className={`min-w-0 flex-1 overflow-x-hidden overflow-y-auto py-3 px-2 ${!expanded ? 'md:px-2' : ''}`}
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
                    className={linkClass(item.to, item.activePrefix)}
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
            const active = navGroupMatchesPath(location.pathname, group)

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
                      {navChildrenVisible(group.children, isAdmin, saasEnabled).map((child) => (
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
                  <div className="w-full min-w-0">
                    <button
                      type="button"
                      onClick={(e) => {
                        const top = e.currentTarget.getBoundingClientRect().top
                        toggleFlyout(group.id, top)
                      }}
                      title={group.label}
                      className={`flex w-full items-center justify-center rounded-lg py-2.5 text-slate-600 hover:bg-slate-100 min-h-[44px] px-2 dark:text-slate-400 dark:hover:bg-slate-800/80 md:px-0 ${
                        active ? 'bg-cyan-50 text-slate-900 ring-1 ring-cyan-200/60 dark:bg-cyan-950/35 dark:text-slate-100 dark:ring-cyan-800/50' : ''
                      }`}
                      aria-expanded={isFlyoutOpen(group.id)}
                      aria-haspopup="true"
                    >
                      {icons[group.icon]}
                    </button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </nav>

      <div className={`shrink-0 border-t border-slate-200 p-2 dark:border-slate-800 ${!expanded ? 'md:px-2' : ''}`}>
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
        <Link
          to="/notificacoes/preferencias"
          onClick={onMobileClose}
          title="Notificações por e-mail"
          className={`mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-slate-100 active:bg-slate-200 touch-manipulation min-h-[44px] dark:text-slate-400 dark:hover:bg-slate-800 dark:active:bg-slate-700 ${
            expanded ? '' : 'md:justify-center md:px-2'
          }`}
        >
          {icons.notificacoes}
          <span
            className={
              expanded
                ? 'min-w-0 truncate transition-all duration-200'
                : 'min-w-0 truncate transition-all duration-200 md:hidden'
            }
          >
            Notificações e-mail
          </span>
        </Link>
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
        {versionLabel ? (
          <Link
            to="/sobre"
            onClick={onMobileClose}
            title="Versão e novidades"
            className={`mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:hover:text-slate-200 ${
              expanded ? '' : 'md:justify-center md:px-2'
            }`}
          >
            <span className={`truncate font-mono tracking-tight ${expanded ? '' : 'md:text-[10px]'}`}>
              {versionLabel}
            </span>
          </Link>
        ) : null}
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

      {/* Sidebar: drawer no mobile; no desktop sticky no viewport; scroll só no nav (#188) */}
      <aside
        className={`fixed inset-0 z-50 flex h-full min-w-0 max-w-[100vw] flex-col overflow-x-hidden bg-white shadow-xl transition-[transform] duration-200 ease-out dark:bg-slate-950 max-md:transition-[transform,width] md:sticky md:top-0 md:col-start-1 md:row-start-1 md:z-40 md:h-dvh md:max-h-dvh md:max-w-none md:w-full md:translate-x-0 md:self-start md:overflow-hidden md:border-r md:border-slate-200 md:shadow-none md:dark:border-slate-800 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
        aria-label="Menu lateral"
      >
        {/* Mobile header com "voltar/fechar" */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200/90 bg-white/95 px-4 shadow-sm backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950 md:hidden">
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">Menu</span>
          <button
            type="button"
            onClick={onMobileClose}
            className="inline-flex size-10 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 active:bg-slate-200 dark:text-slate-400 dark:hover:bg-slate-800 dark:active:bg-slate-700"
            aria-label="Fechar menu"
          >
            ×
          </button>
        </div>
        {sidebarContent}
        {flyoutPortal}
      </aside>
    </>
  )
}
