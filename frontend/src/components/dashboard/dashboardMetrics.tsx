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

export function formatarCsatMedia(media: number | null): string {
  if (media == null) return '—'
  return `${media.toFixed(1).replace('.', ',')} ★`
}

export function formatarPct(valor: number | null): string {
  if (valor == null) return '—'
  return `${valor.toFixed(1).replace('.', ',')}%`
}

export type PresetPeriodo = '7' | '30' | '90' | 'custom'

export const PRESET_DIAS: Record<Exclude<PresetPeriodo, 'custom'>, number> = {
  '7': 7,
  '30': 30,
  '90': 90,
}

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function addDays(base: Date, dias: number): Date {
  const d = new Date(base)
  d.setDate(d.getDate() + dias)
  return d
}
