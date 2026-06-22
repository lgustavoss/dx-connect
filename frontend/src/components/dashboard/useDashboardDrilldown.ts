import { useCallback, useMemo, useState } from 'react'

export type DashboardDrill = {
  tipo: string
  valor: string
  rotulo: string
} | null

const ROTULOS_TIPO: Record<string, string> = {
  atendente: 'Atendente',
  empresa: 'Empresa',
  rede: 'Rede',
  motivo: 'Motivo',
  status: 'Status',
  prioridade: 'Prioridade',
  canal: 'Canal',
  nota: 'Nota',
  estado: 'Situação',
  encerramento: 'Encerramento',
}

export function useDashboardDrilldown() {
  const [drill, setDrill] = useState<DashboardDrill>(null)

  const toggle = useCallback((tipo: string, valor: string, rotulo: string) => {
    setDrill((prev) =>
      prev?.tipo === tipo && prev?.valor === valor ? null : { tipo, valor, rotulo },
    )
  }, [])

  const limpar = useCallback(() => setDrill(null), [])

  const isSelected = useCallback(
    (tipo: string, valor: string) => drill?.tipo === tipo && drill?.valor === valor,
    [drill],
  )

  const apiParams = useMemo(
    () =>
      drill
        ? { drill_tipo: drill.tipo, drill_valor: drill.valor }
        : ({} as { drill_tipo?: string; drill_valor?: string }),
    [drill],
  )

  const rotuloFiltro = drill
    ? `${ROTULOS_TIPO[drill.tipo] ?? drill.tipo}: ${drill.rotulo}`
    : null

  const hasSelection = drill != null

  return useMemo(
    () => ({
      drill,
      toggle,
      limpar,
      isSelected,
      hasSelection,
      apiParams,
      rotuloFiltro,
    }),
    [drill, toggle, limpar, isSelected, hasSelection, apiParams, rotuloFiltro],
  )
}

/** Destaca a barra selecionada e atenua as demais quando há filtro ativo. */
export function corDrill(base: string, selected: boolean, hasSelection: boolean): string {
  if (!hasSelection) return base
  return selected ? base : '#334155'
}
