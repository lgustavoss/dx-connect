import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { portalCliente, type PortalCliente } from '../api/client'

interface PortalAuthContextValue {
  user: PortalCliente.Me | null
  loading: boolean
  login: (email: string, senha: string, lembrarMe?: boolean) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  applyTokens: (tokens: PortalCliente.Token, lembrarMe?: boolean) => Promise<void>
}

const PortalAuthContext = createContext<PortalAuthContextValue | null>(null)

export function PortalAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PortalCliente.Me | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!portalCliente.hasSession()) {
      setUser(null)
      return
    }
    const me = await portalCliente.me()
    setUser(me)
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        if (portalCliente.hasSession()) {
          const me = await portalCliente.me()
          if (!cancelled) setUser(me)
        }
      } catch {
        if (!cancelled) {
          portalCliente.clearSession()
          setUser(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const applyTokens = useCallback(
    async (tokens: PortalCliente.Token, lembrarMe = true) => {
      portalCliente.setSession(tokens, lembrarMe)
      await refreshUser()
    },
    [refreshUser],
  )

  const login = useCallback(
    async (email: string, senha: string, lembrarMe = true) => {
      const tokens = await portalCliente.login(email.trim().toLowerCase(), senha)
      await applyTokens(tokens, lembrarMe)
    },
    [applyTokens],
  )

  const logout = useCallback(() => {
    portalCliente.clearSession()
    setUser(null)
  }, [])

  return (
    <PortalAuthContext.Provider value={{ user, loading, login, logout, refreshUser, applyTokens }}>
      {children}
    </PortalAuthContext.Provider>
  )
}

export function usePortalAuth(): PortalAuthContextValue {
  const ctx = useContext(PortalAuthContext)
  if (!ctx) {
    throw new Error('usePortalAuth deve ser usado dentro de PortalAuthProvider')
  }
  return ctx
}
