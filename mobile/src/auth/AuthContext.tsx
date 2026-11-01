import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import {
  ApiError,
  type AtendenteMe,
  atendentes,
  atendentesMe,
  clearSessionAndSlug,
  getStoredSlug,
  loginNaInstancia,
} from '../api/client'
import { DEFAULT_SLUG, normalizeSlug, pingHealth } from '../lib/instance'
import { registrarDispositivo, revogarDispositivo } from '../lib/push'

type AuthState = {
  ready: boolean
  slug: string
  me: AtendenteMe | null
}

type AuthContextValue = AuthState & {
  entrar: (slug: string, email: string, senha: string) => Promise<void>
  trocarSenha: (senhaAtual: string, senhaNova: string) => Promise<void>
  sair: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [slug, setSlug] = useState(DEFAULT_SLUG)
  const [me, setMe] = useState<AtendenteMe | null>(null)

  useEffect(() => {
    let cancelled = false
    const watchdog = setTimeout(() => {
      if (!cancelled) setReady(true)
    }, 8000)
    ;(async () => {
      try {
        const stored = await getStoredSlug()
        if (stored && !cancelled) setSlug(stored)
        if (stored) {
          const perfil = await atendentesMe()
          if (!cancelled) {
            setMe(perfil)
            void registrarDispositivo()
          }
        }
      } catch {
        if (!cancelled) setMe(null)
      } finally {
        clearTimeout(watchdog)
        if (!cancelled) setReady(true)
      }
    })()
    return () => {
      cancelled = true
      clearTimeout(watchdog)
    }
  }, [])

  const entrar = useCallback(async (slugRaw: string, email: string, senha: string) => {
    const normalized = normalizeSlug(slugRaw)
    if (!normalized) {
      throw new ApiError('Instância inválida. Use o slug (ex.: duplexsoft).', 0, null)
    }
    await pingHealth(normalized)
    await loginNaInstancia(normalized, email, senha)
    const perfil = await atendentesMe()
    setSlug(normalized)
    setMe(perfil)
    void registrarDispositivo()
  }, [])

  const trocarSenha = useCallback(async (senhaAtual: string, senhaNova: string) => {
    const atualizado = await atendentes.trocarSenha(senhaAtual, senhaNova)
    setMe(atualizado)
  }, [])

  const sair = useCallback(async () => {
    await revogarDispositivo()
    await clearSessionAndSlug()
    setMe(null)
    setSlug(DEFAULT_SLUG)
  }, [])

  const value = useMemo(
    () => ({ ready, slug, me, entrar, trocarSenha, sair }),
    [ready, slug, me, entrar, trocarSenha, sair],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth fora do AuthProvider')
  return ctx
}
