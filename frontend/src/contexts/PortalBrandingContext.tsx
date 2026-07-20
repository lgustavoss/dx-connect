import { createContext, useContext, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { kbPublic, portalCliente, type PortalCliente } from '../api/client'

const FALLBACK: PortalCliente.PublicBranding = {
  nome_exibicao: 'Portal do cliente',
  portal_titulo: 'Portal do cliente',
  logo_url: null,
  texto_boas_vindas: 'Acompanhe e abra chamados da sua empresa com a equipe de suporte.',
  cor_primaria: '#0D9488',
  cor_header: '#0B2D4A',
  cor_sidebar: '#0B2D4A',
  cor_texto_header: '#FFFFFF',
  cor_texto_corpo: '#0F172A',
  cor_fundo: '#F8FAFC',
  cor_link: '#0D9488',
  exibir_marca_deskrudder: true,
  chat_habilitado: false,
}

type PortalBrandingContextValue = {
  branding: PortalCliente.PublicBranding
  loading: boolean
}

const PortalBrandingContext = createContext<PortalBrandingContextValue | null>(null)

export function portalBrandingStyleVars(b: PortalCliente.PublicBranding): CSSProperties {
  const sidebar = b.cor_sidebar || b.cor_header
  return {
    backgroundColor: b.cor_fundo,
    color: b.cor_texto_corpo,
    ['--portal-primary' as string]: b.cor_primaria,
    ['--portal-header' as string]: b.cor_header,
    ['--portal-sidebar' as string]: sidebar,
    ['--portal-header-text' as string]: b.cor_texto_header,
    ['--portal-sidebar-text' as string]: b.cor_texto_header,
    ['--portal-body' as string]: b.cor_texto_corpo,
    ['--portal-bg' as string]: b.cor_fundo,
    ['--portal-link' as string]: b.cor_link,
  }
}

function mergeBranding(data: Partial<PortalCliente.PublicBranding>): PortalCliente.PublicBranding {
  const merged = {
    ...FALLBACK,
    ...data,
    chat_habilitado: Boolean(data.chat_habilitado),
  }
  merged.cor_sidebar = data.cor_sidebar || data.cor_header || FALLBACK.cor_sidebar
  return merged
}

export function PortalBrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<PortalCliente.PublicBranding | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    portalCliente
      .branding()
      .then(async (data) => {
        if (cancelled) return
        let chat = Boolean((data as { chat_habilitado?: boolean }).chat_habilitado)
        if (!('chat_habilitado' in data) || (data as { chat_habilitado?: boolean }).chat_habilitado == null) {
          try {
            const kb = await kbPublic.branding()
            chat = Boolean(kb.chat_habilitado)
          } catch {
            chat = false
          }
        }
        setBranding(mergeBranding({ ...data, chat_habilitado: chat }))
      })
      .catch(() => {
        if (!cancelled) setBranding(FALLBACK)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const resolved = branding ?? FALLBACK

  useEffect(() => {
    document.title = resolved.portal_titulo
  }, [resolved.portal_titulo])

  const value = useMemo(
    () => ({
      branding: resolved,
      loading,
    }),
    [resolved, loading],
  )

  return (
    <PortalBrandingContext.Provider value={value}>
      <div
        className="portal-cliente min-h-dvh"
        data-theme="light"
        style={{ ...portalBrandingStyleVars(resolved), colorScheme: 'light' }}
      >
        {children}
      </div>
    </PortalBrandingContext.Provider>
  )
}

export function usePortalBranding(): PortalCliente.PublicBranding {
  const ctx = useContext(PortalBrandingContext)
  if (!ctx) throw new Error('usePortalBranding deve ser usado dentro de PortalBrandingProvider')
  return ctx.branding
}

export function usePortalBrandingLoading(): boolean {
  const ctx = useContext(PortalBrandingContext)
  return ctx?.loading ?? true
}
