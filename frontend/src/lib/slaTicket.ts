export type SlaEstadoResumido = 'dentro' | 'em_risco' | 'violado' | 'cumprido'

export interface SlaMetaDetalhe {
  meta_minutos: number | null
  vence_em: string | null
  vence_em_efetivo?: string | null
  cumprido_em: string | null
  estado: string
  percentual_decorrido: number | null
}

export interface TicketSlaDetalhe {
  ticket_id: number
  sla_policy_id: number | null
  sla_violado: boolean
  inicio_em: string
  usa_horario_comercial: boolean
  primeira_resposta: SlaMetaDetalhe
  resolucao: SlaMetaDetalhe
}

const ROTULOS: Record<string, string> = {
  dentro: 'Dentro do SLA',
  em_risco: 'SLA em risco',
  violado: 'SLA violado',
  cumprido: 'SLA cumprido',
  sem_meta: 'Sem meta',
}

export function rotuloSlaEstado(estado: string | null | undefined): string | null {
  if (!estado) return null
  return ROTULOS[estado] ?? estado
}

export function classeBadgeSla(estado: string | null | undefined): string {
  switch (estado) {
    case 'violado':
      return 'bg-red-50 text-red-800 ring-1 ring-inset ring-red-200 dark:bg-red-950/40 dark:text-red-200 dark:ring-red-800/60'
    case 'em_risco':
      return 'bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-800/50'
    case 'cumprido':
      return 'bg-emerald-50 text-emerald-800 ring-1 ring-inset ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-800/50'
    case 'dentro':
      return 'bg-emerald-50/70 text-emerald-900 ring-1 ring-inset ring-emerald-200/80 dark:bg-emerald-950/30 dark:text-emerald-100 dark:ring-emerald-800/40'
    default:
      return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
  }
}

export function formatMinutosSla(min: number | null | undefined, comercial: boolean): string {
  if (min == null || min <= 0) return '—'
  const suf = comercial ? ' úteis' : ''
  if (min < 60) return `${min} min${suf}`
  const h = Math.floor(min / 60)
  const rest = min % 60
  if (rest === 0) return `${h}h${suf}`
  return `${h}h ${rest}min${suf}`
}

function diffMinutos(iso: string | null | undefined, agora = Date.now()): number | null {
  if (!iso) return null
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return null
  return Math.round((t - agora) / 60000)
}

export function textoCountdownSla(meta: SlaMetaDetalhe, comercial: boolean): string {
  if (meta.estado === 'cumprido') return 'Cumprido'
  if (meta.estado === 'violado') {
    const ref = meta.vence_em_efetivo ?? meta.vence_em
    const atraso = diffMinutos(ref)
    if (atraso != null && atraso < 0) {
      const min = Math.abs(atraso)
      if (min < 60) return `Violado há ${min} min`
      const h = Math.floor(min / 60)
      const m = min % 60
      return m > 0 ? `Violado há ${h}h ${m}min` : `Violado há ${h}h`
    }
    return 'Violado'
  }
  const ref = meta.vence_em_efetivo ?? meta.vence_em
  const rest = diffMinutos(ref)
  if (rest == null) return '—'
  if (rest <= 0) return 'Prazo esgotado'
  const tipo = comercial ? 'úteis' : 'restantes'
  if (rest < 60) return `${rest} min ${tipo}`
  const h = Math.floor(rest / 60)
  const m = rest % 60
  return m > 0 ? `${h}h ${m}min ${tipo}` : `${h}h ${tipo}`
}

export function tooltipSlaMeta(nome: string, meta: SlaMetaDetalhe, comercial: boolean): string {
  const metaTxt = formatMinutosSla(meta.meta_minutos, comercial)
  const estado = rotuloSlaEstado(meta.estado) ?? meta.estado
  return `${nome}: meta ${metaTxt} · ${estado}`
}
