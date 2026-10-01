export type DiaKey = 'seg' | 'ter' | 'qua' | 'qui' | 'sex' | 'sab' | 'dom'

export type HorarioDia = {
  ativo: boolean
  inicio: string
  fim: string
  intervaloInicio: string
  intervaloFim: string
}

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

function dia(ativo: boolean, inicio: string, fim: string, intervaloInicio = '', intervaloFim = ''): HorarioDia {
  return { ativo, inicio, fim, intervaloInicio, intervaloFim }
}

export function horarioSemanaPadrao(): HorarioSemana {
  return {
    seg: dia(true, '08:00', '18:00'),
    ter: dia(true, '08:00', '18:00'),
    qua: dia(true, '08:00', '18:00'),
    qui: dia(true, '08:00', '18:00'),
    sex: dia(true, '08:00', '18:00'),
    sab: dia(false, '08:00', '12:00'),
    dom: dia(false, '08:00', '12:00'),
  }
}

export function horarioSemanaFromApi(
  raw: Record<
    string,
    { ativo?: boolean; inicio?: string; fim?: string; intervalo_inicio?: string | null; intervalo_fim?: string | null }
  > | null | undefined,
): HorarioSemana {
  const vazio = dia(false, '08:00', '18:00')
  const base = horarioSemanaPadrao()
  if (!raw) return base
  for (const { key } of DIAS_SEMANA) {
    const d = raw[key]
    if (!d) continue
    base[key] = {
      ativo: d.ativo ?? vazio.ativo,
      inicio: d.inicio ?? vazio.inicio,
      fim: d.fim ?? vazio.fim,
      intervaloInicio: d.intervalo_inicio ?? '',
      intervaloFim: d.intervalo_fim ?? '',
    }
  }
  return base
}

function minutosHhmm(valor: string): number | null {
  const m = /^(\d{2}):(\d{2})/.exec(valor)
  if (!m) return null
  return Number(m[1]) * 60 + Number(m[2])
}

/** Minutos previstos de trabalho no dia, já sem o intervalo. Null se o dia estiver incompleto. */
export function minutosPrevistosDia(d: HorarioDia): number | null {
  if (!d.ativo) return null
  const ini = minutosHhmm(d.inicio)
  const fim = minutosHhmm(d.fim)
  if (ini == null || fim == null || ini >= fim) return null
  const iIni = minutosHhmm(d.intervaloInicio)
  const iFim = minutosHhmm(d.intervaloFim)
  const pausa = iIni != null && iFim != null && iFim > iIni ? iFim - iIni : 0
  return Math.max(0, fim - ini - pausa)
}

export function horarioSemanaParaApi(
  semana: HorarioSemana,
): Record<string, { ativo: boolean; inicio: string; fim: string; intervalo_inicio?: string; intervalo_fim?: string }> {
  const out: Record<
    string,
    { ativo: boolean; inicio: string; fim: string; intervalo_inicio?: string; intervalo_fim?: string }
  > = {}
  for (const { key } of DIAS_SEMANA) {
    const d = semana[key]
    const row: { ativo: boolean; inicio: string; fim: string; intervalo_inicio?: string; intervalo_fim?: string } = {
      ativo: d.ativo,
      inicio: d.inicio,
      fim: d.fim,
    }
    if (d.intervaloInicio || d.intervaloFim) {
      row.intervalo_inicio = d.intervaloInicio
      row.intervalo_fim = d.intervaloFim
    }
    out[key] = row
  }
  return out
}

export function rotuloHorasPrevistas(minutos: number): string {
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  if (m === 0) return `${h}h`
  return `${h}h${String(m).padStart(2, '0')}`
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
    const temIntervalo = Boolean(d.intervaloInicio || d.intervaloFim)
    if (temIntervalo) {
      if (!d.intervaloInicio || !d.intervaloFim) {
        return `${label}: informe início e fim do intervalo.`
      }
      if (d.intervaloInicio >= d.intervaloFim) {
        return `${label}: o intervalo deve começar antes de terminar.`
      }
      if (d.intervaloInicio <= d.inicio || d.intervaloFim >= d.fim) {
        return `${label}: o intervalo precisa ficar dentro do horário de trabalho.`
      }
    }
  }
  return null
}
