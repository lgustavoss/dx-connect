import { useCallback, useState } from 'react'
import {
  boundsForPreset,
  type PresetPeriodo,
} from '../components/dashboard/dashboardMetrics'

const DEFAULT_PRESET: Exclude<PresetPeriodo, 'custom'> = 'este_mes'

/** Estado partilhado do filtro de período dos dashboards (#599). */
export function useDashboardPeriodo(initial: Exclude<PresetPeriodo, 'custom'> = DEFAULT_PRESET) {
  const inicial = boundsForPreset(initial)
  const [preset, setPreset] = useState<PresetPeriodo>(initial)
  const [de, setDe] = useState(inicial.de)
  const [ate, setAte] = useState(inicial.ate)

  const aplicarPreset = useCallback((p: Exclude<PresetPeriodo, 'custom'>) => {
    setPreset(p)
    const b = boundsForPreset(p)
    setDe(b.de)
    setAte(b.ate)
  }, [])

  const marcarCustom = useCallback(() => {
    setPreset('custom')
  }, [])

  const onDeChange = useCallback((v: string) => {
    setPreset('custom')
    setDe(v)
  }, [])

  const onAteChange = useCallback((v: string) => {
    setPreset('custom')
    setAte(v)
  }, [])

  return {
    preset,
    de,
    ate,
    aplicarPreset,
    marcarCustom,
    onDeChange,
    onAteChange,
  }
}
