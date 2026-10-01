import {
  DIAS_SEMANA,
  minutosPrevistosDia,
  rotuloHorasPrevistas,
  type HorarioSemana,
} from '../../lib/horarioSemana'

type Props = {
  value: HorarioSemana
  onChange: (next: HorarioSemana) => void
  /** Intervalo do almoço e horas previstas. Só na jornada do colaborador. */
  mostrarIntervalo?: boolean
}

const inputClass =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 disabled:opacity-50'

export function HorarioSemanaEditor({ value, onChange, mostrarIntervalo = false }: Props) {
  const avisoIntervalo = mostrarIntervalo
    ? DIAS_SEMANA.some((d) => {
        const dia = value[d.key]
        const previsto = minutosPrevistosDia(dia)
        return Boolean(dia.ativo && previsto != null && previsto > 6 * 60 && !dia.intervaloInicio && !dia.intervaloFim)
      })
    : false

  return (
    <div className="space-y-2">
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800/80">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50/70 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800/30 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">Dia</th>
              <th className="px-4 py-3">Aberto</th>
              <th className="px-4 py-3">Início</th>
              <th className="px-4 py-3">Fim</th>
              {mostrarIntervalo ? (
                <>
                  <th className="px-4 py-3">Intervalo início</th>
                  <th className="px-4 py-3">Intervalo fim</th>
                  <th className="px-4 py-3">Previsto</th>
                </>
              ) : null}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
            {DIAS_SEMANA.map((d) => {
              const dia = value[d.key]
              const previsto = minutosPrevistosDia(dia)
              return (
                <tr key={d.key} className="bg-white/40 dark:bg-slate-900/20">
                  <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-100">{d.label}</td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={dia.ativo}
                      onChange={(e) =>
                        onChange({ ...value, [d.key]: { ...dia, ativo: e.target.checked } })
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="time"
                      value={dia.inicio}
                      disabled={!dia.ativo}
                      onChange={(e) => onChange({ ...value, [d.key]: { ...dia, inicio: e.target.value } })}
                      className={inputClass}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="time"
                      value={dia.fim}
                      disabled={!dia.ativo}
                      onChange={(e) => onChange({ ...value, [d.key]: { ...dia, fim: e.target.value } })}
                      className={inputClass}
                    />
                  </td>
                  {mostrarIntervalo ? (
                    <>
                      <td className="px-4 py-3">
                        <input
                          type="time"
                          value={dia.intervaloInicio}
                          disabled={!dia.ativo}
                          onChange={(e) =>
                            onChange({ ...value, [d.key]: { ...dia, intervaloInicio: e.target.value } })
                          }
                          className={inputClass}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="time"
                          value={dia.intervaloFim}
                          disabled={!dia.ativo}
                          onChange={(e) =>
                            onChange({ ...value, [d.key]: { ...dia, intervaloFim: e.target.value } })
                          }
                          className={inputClass}
                        />
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                        {previsto == null ? '—' : rotuloHorasPrevistas(previsto)}
                      </td>
                    </>
                  ) : null}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {avisoIntervalo ? (
        <p className="text-sm text-amber-800 dark:text-amber-200">
          Horário acima de 6 horas sem intervalo conta a pausa como tempo de trabalho. Informe o
          intervalo para descontar a pausa das horas previstas.
        </p>
      ) : null}
    </div>
  )
}
