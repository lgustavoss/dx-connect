import { Button } from '../ui/Button'

type Props = {
  rotulo: string
  onLimpar: () => void
}

export function DashboardFiltroAtivo({ rotulo, onLimpar }: Props) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-cyan-200 bg-cyan-50 px-4 py-3 dark:border-cyan-800/60 dark:bg-cyan-950/30">
      <p className="text-sm text-slate-700 dark:text-slate-200">
        Filtrando por: <span className="font-semibold">{rotulo}</span>
      </p>
      <Button type="button" variant="ghost" className="text-sm" onClick={onLimpar}>
        Limpar filtro
      </Button>
    </div>
  )
}
