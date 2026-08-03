import type { ReactNode } from 'react'
import { Card } from '../ui/Card'

export function DicaMetrica({ texto }: { texto: string }) {
  return (
    <span
      className="ml-1.5 inline-flex h-4 w-4 shrink-0 cursor-help items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold leading-none text-slate-600 dark:bg-slate-700 dark:text-slate-300"
      title={texto}
      aria-label={texto}
    >
      ?
    </span>
  )
}

export function MetricCard({
  label,
  dica,
  value,
  hint,
  borderClass,
  children,
}: {
  label: string
  dica?: string
  value?: string
  hint?: string
  borderClass: string
  children?: ReactNode
}) {
  return (
    <Card className={`flex flex-col ${borderClass}`}>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
        {label}
        {dica ? <DicaMetrica texto={dica} /> : null}
      </p>
      {value != null ? (
        <p className="mt-1 text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
      ) : null}
      {children}
      {hint ? (
        <p className={`text-xs text-slate-500 dark:text-slate-400 ${value != null || children ? 'mt-1' : 'mt-2'}`}>
          {hint}
        </p>
      ) : null}
    </Card>
  )
}

export function formatarHoras(valor: number | null): string {
  if (valor == null) return '—'
  if (valor < 1) return `${Math.round(valor * 60)} min`
  return `${valor.toFixed(1).replace('.', ',')} h`
}

export function formatarDiaCurto(iso: string): string {
  const [, m, day] = iso.split('-')
  return `${day}/${m}`
}

export function formatarDiaCompleto(iso: string): string {
  const [y, m, day] = iso.split('-')
  return `${day}/${m}/${y}`
}

/** Intervalo efetivo para subtítulo do dashboard (#599). */
export function formatarIntervaloPeriodo(deIso: string, ateIso: string): string {
  if (deIso === ateIso) return formatarDiaCompleto(deIso)
  const [dy] = deIso.split('-')
  const [ay] = ateIso.split('-')
  if (dy === ay) return `${formatarDiaCurto(deIso)}–${formatarDiaCompleto(ateIso)}`
  return `${formatarDiaCompleto(deIso)}–${formatarDiaCompleto(ateIso)}`
}

export function formatarCsatMedia(media: number | null): string {
  if (media == null) return '—'
  return `${media.toFixed(1).replace('.', ',')} ★`
}

export function formatarPct(valor: number | null): string {
  if (valor == null) return '—'
  return `${valor.toFixed(1).replace('.', ',')}%`
}

/** Presets de calendário (#599). Semana = segunda → domingo. */
export type PresetPeriodo = 'hoje' | 'esta_semana' | 'este_mes' | 'mes_passado' | 'custom'

export const PRESET_OPCOES: { id: Exclude<PresetPeriodo, 'custom'>; label: string }[] = [
  { id: 'hoje', label: 'Hoje' },
  { id: 'esta_semana', label: 'Esta semana' },
  { id: 'este_mes', label: 'Este mês' },
  { id: 'mes_passado', label: 'Mês passado' },
]

/** Data civil local (YYYY-MM-DD) — evita deslocamento UTC de toISOString(). */
export function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function addDays(base: Date, dias: number): Date {
  const d = new Date(base.getFullYear(), base.getMonth(), base.getDate())
  d.setDate(d.getDate() + dias)
  return d
}

export function parseIsoDateLocal(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function boundsForPreset(
  preset: Exclude<PresetPeriodo, 'custom'>,
  ref: Date = new Date(),
): { de: string; ate: string } {
  const hoje = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate())
  if (preset === 'hoje') {
    const iso = isoDate(hoje)
    return { de: iso, ate: iso }
  }
  if (preset === 'esta_semana') {
    // Monday = 0 in ISO; getDay() Sunday=0 → convert
    const weekday = (hoje.getDay() + 6) % 7
    const inicio = addDays(hoje, -weekday)
    return { de: isoDate(inicio), ate: isoDate(hoje) }
  }
  if (preset === 'este_mes') {
    const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
    return { de: isoDate(inicio), ate: isoDate(hoje) }
  }
  // mes_passado
  const primeiroEste = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
  const ultimoPassado = addDays(primeiroEste, -1)
  const primeiroPassado = new Date(ultimoPassado.getFullYear(), ultimoPassado.getMonth(), 1)
  return { de: isoDate(primeiroPassado), ate: isoDate(ultimoPassado) }
}
