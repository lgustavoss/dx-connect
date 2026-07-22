import { Link, Outlet } from 'react-router-dom'
import { kbPublic } from '../../api/client'
import { KbPublicProvider, useKbPublic, useKbPublicBranding } from './KbPublicContext'
import { KbPublicSidebar } from './KbPublicSidebar'
import { KbPublicChatWidget } from './KbPublicChatWidget'

const menuIcon = (
  <svg className="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

function KbPublicShell() {
  const branding = useKbPublicBranding()
  const { sidebarCollapsed, toggleSidebar } = useKbPublic()

  return (
    <div
      className="kb-public-portal flex min-h-dvh flex-col"
      data-theme="light"
      style={{
        backgroundColor: branding.cor_fundo,
        color: branding.cor_texto_corpo,
        colorScheme: 'light',
        ['--kb-accent' as string]: branding.cor_primaria,
        ['--kb-header' as string]: branding.cor_header,
        ['--kb-link' as string]: branding.cor_link,
        ['--kb-body-text' as string]: branding.cor_texto_corpo,
      }}
    >
      <header
        className="relative shrink-0 border-b border-black/10 shadow-sm"
        style={{ backgroundColor: branding.cor_header }}
      >
        <div className="flex h-14 items-center px-3 sm:px-4">
          <div className="z-10 flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors hover:bg-white/10"
              style={{ color: branding.cor_texto_header }}
              aria-label={sidebarCollapsed ? 'Expandir menu de categorias' : 'Recolher menu de categorias'}
              aria-expanded={!sidebarCollapsed}
            >
              {menuIcon}
            </button>
            {branding.logo_url ? (
              <Link to="/kb" className="flex shrink-0 items-center no-underline" title={branding.nome_exibicao}>
                <img
                  src={kbPublic.logoAssetUrl()}
                  alt={branding.nome_exibicao}
                  className="h-10 max-h-10 w-auto max-w-[200px] object-contain object-left sm:h-11 sm:max-h-11"
                />
              </Link>
            ) : null}
          </div>

          <h1
            className="pointer-events-none absolute inset-x-0 truncate px-24 text-center text-base font-semibold tracking-tight sm:text-lg"
            style={{ color: branding.cor_texto_header }}
          >
            {branding.portal_titulo}
          </h1>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <KbPublicSidebar />
        <main className="min-w-0 flex-1 overflow-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-4xl">
            <Outlet />
          </div>
        </main>
      </div>

      <footer className="shrink-0 border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        Central de ajuda fornecida por{' '}
        <span className="font-medium" style={{ color: branding.cor_primaria }}>
          DeskRudder
        </span>
      </footer>
      <KbPublicChatWidget />
    </div>
  )
}

export function KbPublicLayout() {
  return (
    <KbPublicProvider>
      <KbPublicShell />
    </KbPublicProvider>
  )
}
