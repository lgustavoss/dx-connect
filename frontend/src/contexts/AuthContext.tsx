import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { atendentes, clearAuthToken, getAuthToken, ApiError, type Atendentes } from '../api/client'

interface AuthContextValue {
  user: Atendentes.Atendente | null
  loading: boolean
  login: (email: string, senha: string, lembrarMe?: boolean) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  isAdmin: boolean
  isComercialOuAdmin: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Atendentes.Atendente | null>(null)
  const [loading, setLoading] = useState(true)
  const refreshSeq = useRef(0)

  const refreshUser = useCallback(async () => {
    const seq = ++refreshSeq.current
    const token = getAuthToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await atendentes.me()
      if (seq !== refreshSeq.current) return
      setUser(me)
    } catch (e) {
      if (seq !== refreshSeq.current) return
      setUser(null)
      // 401 em /me: o api() já redireciona e limpa tokens; não limpar de novo evita corrida com Strict Mode.
      if (e instanceof ApiError && e.status === 403) {
        clearAuthToken()
      }
    } finally {
      if (seq === refreshSeq.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = useCallback(async (email: string, senha: string, lembrarMe = true) => {
    const { auth } = await import('../api/client')
    const res = await auth.login(email, senha)
    clearAuthToken()
    if (lembrarMe) {
      localStorage.setItem('token', res.access_token)
      if (res.refresh_token) localStorage.setItem('refresh_token', res.refresh_token)
    } else {
      sessionStorage.setItem('token', res.access_token)
      if (res.refresh_token) sessionStorage.setItem('refresh_token', res.refresh_token)
    }
    await refreshUser()
  }, [refreshUser])

  const logout = useCallback(() => {
    clearAuthToken()
    setUser(null)
  }, [])

  const value: AuthContextValue = {
    user,
    loading,
    login,
    logout,
    refreshUser,
    isAdmin: user?.role === 'admin',
    isComercialOuAdmin: user?.role === 'admin' || user?.role === 'comercial',
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
