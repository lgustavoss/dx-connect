import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useColorScheme } from 'react-native'

import { coresClaro, coresEscuro, type Cores } from './brand'
import { storageGet, storageSet } from './storage'

/** Mesma chave e valores do painel web (`light` | `dark` | `system`). */
const CHAVE_TEMA = 'deskrudder-theme'

export type PreferenciaTema = 'light' | 'dark' | 'system'
export type TemaResolvido = 'light' | 'dark'

function resolver(preferencia: PreferenciaTema, sistema: 'light' | 'dark' | null | undefined): TemaResolvido {
  if (preferencia === 'system') return sistema === 'dark' ? 'dark' : 'light'
  return preferencia
}

type ValorTema = {
  preferencia: PreferenciaTema
  tema: TemaResolvido
  cores: Cores
  definir: (preferencia: PreferenciaTema) => void
  /** Alterna claro/escuro gravando preferência explícita (como no web). */
  alternar: () => void
}

const TemaContexto = createContext<ValorTema | null>(null)

export function TemaProvider({ children }: { children: ReactNode }) {
  const sistema = useColorScheme()
  const [preferencia, setPreferencia] = useState<PreferenciaTema>('system')
  const [carregado, setCarregado] = useState(false)

  useEffect(() => {
    let vivo = true
    void storageGet(CHAVE_TEMA).then((salvo) => {
      if (!vivo) return
      if (salvo === 'light' || salvo === 'dark' || salvo === 'system') setPreferencia(salvo)
      setCarregado(true)
    })
    return () => {
      vivo = false
    }
  }, [])

  const definir = useCallback((nova: PreferenciaTema) => {
    setPreferencia(nova)
    void storageSet(CHAVE_TEMA, nova)
  }, [])

  const tema = resolver(preferencia, sistema)

  const alternar = useCallback(() => {
    definir(tema === 'dark' ? 'light' : 'dark')
  }, [definir, tema])

  const cores = tema === 'dark' ? coresEscuro : coresClaro

  const valor = useMemo<ValorTema>(
    () => ({ preferencia, tema, cores, definir, alternar }),
    [preferencia, tema, cores, definir, alternar],
  )

  // Evita piscar o tema claro em quem preferiu escuro.
  if (!carregado) return null

  return <TemaContexto.Provider value={valor}>{children}</TemaContexto.Provider>
}

export function useTema(): ValorTema {
  const contexto = useContext(TemaContexto)
  if (!contexto) throw new Error('useTema precisa estar dentro de TemaProvider')
  return contexto
}

export function useCores(): Cores {
  return useTema().cores
}
