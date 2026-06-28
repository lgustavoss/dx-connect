import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { THEME_STORAGE_KEY, THEME_STORAGE_KEY_LEGACY } from '../brand'

export type ThemePreference = 'light' | 'dark' | 'system'

function readStored(): ThemePreference {
  try {
    const v = localStorage.getItem(THEME_STORAGE_KEY) ?? localStorage.getItem(THEME_STORAGE_KEY_LEGACY)
    if (v === 'light' || v === 'dark' || v === 'system') return v
  } catch {
    /* ignore */
  }
  return 'system'
}

function systemIsDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function resolvePreference(pref: ThemePreference): 'light' | 'dark' {
  if (pref === 'system') return systemIsDark() ? 'dark' : 'light'
  return pref
}

function applyDomClass(mode: 'light' | 'dark') {
  document.documentElement.classList.toggle('dark', mode === 'dark')
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', mode === 'dark' ? '#020617' : '#f8fafc')
}

interface ThemeContextValue {
  preference: ThemePreference
  resolved: 'light' | 'dark'
  setPreference: (p: ThemePreference) => void
  /** Alterna entre claro e escuro (grava preferência explícita). */
  toggleLightDark: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(() =>
    typeof window === 'undefined' ? 'system' : readStored(),
  )

  const [resolved, setResolved] = useState<'light' | 'dark'>(() =>
    typeof window === 'undefined' ? 'light' : resolvePreference(readStored()),
  )

  const setPreference = useCallback((p: ThemePreference) => {
    setPreferenceState(p)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, p)
    } catch {
      /* ignore */
    }
    const r = resolvePreference(p)
    setResolved(r)
    applyDomClass(r)
  }, [])

  const toggleLightDark = useCallback(() => {
    const next = resolved === 'dark' ? 'light' : 'dark'
    setPreference(next)
  }, [resolved, setPreference])

  useEffect(() => {
    const r = resolvePreference(preference)
    setResolved(r)
    applyDomClass(r)
  }, [preference])

  useEffect(() => {
    if (preference !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      const r = resolvePreference('system')
      setResolved(r)
      applyDomClass(r)
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [preference])

  const value = useMemo(
    () => ({ preference, resolved, setPreference, toggleLightDark }),
    [preference, resolved, setPreference, toggleLightDark],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme deve ser usado dentro de ThemeProvider')
  return ctx
}
