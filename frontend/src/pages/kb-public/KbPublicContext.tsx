import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { kbPublic, type Kb } from '../../api/client'

const SIDEBAR_KEY = 'kb-public-sidebar-collapsed'

type KbPublicContextValue = {
  branding: Kb.PublicBranding | null
  categorias: Kb.Category[]
  categoriasLoading: boolean
  sidebarCollapsed: boolean
  setSidebarCollapsed: (v: boolean) => void
  toggleSidebar: () => void
}

const KbPublicContext = createContext<KbPublicContextValue | null>(null)

const FALLBACK_BRANDING: Kb.PublicBranding = {
  nome_exibicao: 'Central de ajuda',
  portal_titulo: 'Central de ajuda',
  logo_url: null,
  texto_boas_vindas: null,
  cor_primaria: '#0D9488',
  cor_header: '#0B2D4A',
  cor_sidebar: '#0B2D4A',
  cor_texto_header: '#FFFFFF',
  cor_texto_corpo: '#0F172A',
  cor_fundo: '#F8FAFC',
  cor_link: '#0D9488',
  exibir_marca_deskrudder: true,
  feedback_habilitado: true,
  chat_habilitado: false,
}

export function KbPublicProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<Kb.PublicBranding | null>(null)
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [categoriasLoading, setCategoriasLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsedState] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) === '1'
    } catch {
      return false
    }
  })

  function setSidebarCollapsed(v: boolean) {
    setSidebarCollapsedState(v)
    try {
      localStorage.setItem(SIDEBAR_KEY, v ? '1' : '0')
    } catch {
      /* storage indisponível */
    }
  }

  function toggleSidebar() {
    setSidebarCollapsedState((prev) => {
      const next = !prev
      try {
        localStorage.setItem(SIDEBAR_KEY, next ? '1' : '0')
      } catch {
        /* storage indisponível */
      }
      return next
    })
  }

  useEffect(() => {
    kbPublic
      .branding()
      .then(setBranding)
      .catch(() => setBranding(FALLBACK_BRANDING))
  }, [])

  useEffect(() => {
    kbPublic
      .listCategories()
      .then(setCategorias)
      .catch(() => setCategorias([]))
      .finally(() => setCategoriasLoading(false))
  }, [])

  const value = useMemo(
    () => ({
      branding,
      categorias,
      categoriasLoading,
      sidebarCollapsed,
      setSidebarCollapsed,
      toggleSidebar,
    }),
    [branding, categorias, categoriasLoading, sidebarCollapsed],
  )

  return <KbPublicContext.Provider value={value}>{children}</KbPublicContext.Provider>
}

export function useKbPublic() {
  const ctx = useContext(KbPublicContext)
  if (!ctx) throw new Error('useKbPublic deve ser usado dentro de KbPublicProvider')
  return ctx
}

export function useKbPublicBranding(): Kb.PublicBranding {
  const { branding } = useKbPublic()
  return branding ?? FALLBACK_BRANDING
}
