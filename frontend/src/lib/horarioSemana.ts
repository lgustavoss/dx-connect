export type DiaKey = 'seg' | 'ter' | 'qua' | 'qui' | 'sex' | 'sab' | 'dom'

export type HorarioDia = { ativo: boolean; inicio: string; fim: string }

export type HorarioSemana = Record<DiaKey, HorarioDia>

export const DIAS_SEMANA: Array<{ key: DiaKey; label: string }> = [
  { key: 'seg', label: 'Segunda' },
  { key: 'ter', label: 'Terça' },
  { key: 'qua', label: 'Quarta' },
  { key: 'qui', label: 'Quinta' },
  { key: 'sex', label: 'Sexta' },
  { key: 'sab', label: 'Sábado' },
  { key: 'dom', label: 'Domingo' },
]

export function horarioSemanaPadrao(): HorarioSemana {
  return {
    seg: { ativo: true, inicio: '08:00', fim: '18:00' },
    ter: { ativo: true, inicio: '08:00', fim: '18:00' },
    qua: { ativo: true, inicio: '08:00', fim: '18:00' },
    qui: { ativo: true, inicio: '08:00', fim: '18:00' },
    sex: { ativo: true, inicio: '08:00', fim: '18:00' },
    sab: { ativo: false, inicio: '08:00', fim: '12:00' },
    dom: { ativo: false, inicio: '08:00', fim: '12:00' },
  }
}

export function horarioSemanaFromApi(
  raw: Record<string, { ativo?: boolean; inicio?: string; fim?: string }> | null | undefined,
): HorarioSemana {
  const base = horarioSemanaPadrao()
  if (!raw) return base
  for (const { key } of DIAS_SEMANA) {
    const d = raw[key]
    if (!d) continue
    base[key] = {
      ativo: d.ativo ?? base[key].ativo,
      inicio: d.inicio ?? base[key].inicio,
      fim: d.fim ?? base[key].fim,
    }
  }
  return base
}

/** Retorna mensagem de erro ou null se válido. */
export function validarHorarioSemana(semana: HorarioSemana): string | null {
  for (const { key, label } of DIAS_SEMANA) {
    const d = semana[key]
    if (!d.ativo) continue
    if (!d.inicio || !d.fim) {
      return `${label}: informe início e fim quando o dia estiver aberto.`
    }
    if (d.inicio >= d.fim) {
      return `${label}: horário de início deve ser anterior ao fim.`
    }
  }
  return null
}
