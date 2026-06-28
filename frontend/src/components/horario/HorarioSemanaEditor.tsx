import { DIAS_SEMANA, type HorarioSemana } from '../../lib/horarioSemana'

type Props = {
  value: HorarioSemana
  onChange: (next: HorarioSemana) => void
}

export function HorarioSemanaEditor({ value, onChange }: Props) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800/80">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50/70 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800/30 dark:text-slate-400">
          <tr>
            <th className="px-4 py-3">Dia</th>
            <th className="px-4 py-3">Aberto</th>
            <th className="px-4 py-3">Início</th>
            <th className="px-4 py-3">Fim</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {DIAS_SEMANA.map((d) => (
            <tr key={d.key} className="bg-white/40 dark:bg-slate-900/20">
              <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-100">{d.label}</td>
              <td className="px-4 py-3">
                <input
                  type="checkbox"
                  checked={value[d.key].ativo}
                  onChange={(e) =>
                    onChange({ ...value, [d.key]: { ...value[d.key], ativo: e.target.checked } })
                  }
                />
              </td>
              <td className="px-4 py-3">
                <input
                  type="time"
                  value={value[d.key].inicio}
                  disabled={!value[d.key].ativo}
                  onChange={(e) =>
                    onChange({ ...value, [d.key]: { ...value[d.key], inicio: e.target.value } })
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 disabled:opacity-50"
                />
              </td>
              <td className="px-4 py-3">
                <input
                  type="time"
                  value={value[d.key].fim}
                  disabled={!value[d.key].ativo}
                  onChange={(e) =>
                    onChange({ ...value, [d.key]: { ...value[d.key], fim: e.target.value } })
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 disabled:opacity-50"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
