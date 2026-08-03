import { Button } from '../ui/Button'
import { PRESET_OPCOES, type PresetPeriodo } from './dashboardMetrics'

type Props = {
  preset: PresetPeriodo
  de: string
  ate: string
  onPreset: (p: Exclude<PresetPeriodo, 'custom'>) => void
  onCustom: () => void
  onDeChange: (v: string) => void
  onAteChange: (v: string) => void
}

/**
 * Filtro de período reutilizável (#599).
 * Semana = segunda → domingo (até hoje se a semana ainda não acabou).
 */
export function DashboardPeriodoFiltro({
  preset,
  de,
  ate,
  onPreset,
  onCustom,
  onDeChange,
  onAteChange,
}: Props) {
  return (
    <>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Período">
        {PRESET_OPCOES.map((op) => (
          <Button
            key={op.id}
            type="button"
            variant={preset === op.id ? 'primary' : 'secondary'}
            onClick={() => onPreset(op.id)}
          >
            {op.label}
          </Button>
        ))}
        <Button type="button" variant={preset === 'custom' ? 'primary' : 'secondary'} onClick={onCustom}>
          Personalizado
        </Button>
      </div>
      {preset === 'custom' ? (
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            De
            <input
              type="date"
              value={de}
              onChange={(e) => onDeChange(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            Até
            <input
              type="date"
              value={ate}
              onChange={(e) => onAteChange(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
          </label>
        </div>
      ) : null}
    </>
  )
}
