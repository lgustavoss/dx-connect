export type PrioridadeTicket = 'baixa' | 'normal' | 'alta' | 'urgente'

export const PRIORIDADE_OPCOES: { value: PrioridadeTicket; label: string }[] = [
  { value: 'baixa', label: 'Baixa' },
  { value: 'normal', label: 'Normal' },
  { value: 'alta', label: 'Alta' },
  { value: 'urgente', label: 'Urgente' },
]

export function rotuloPrioridade(valor: PrioridadeTicket | string | undefined | null): string {
  const hit = PRIORIDADE_OPCOES.find((o) => o.value === valor)
  return hit?.label ?? 'Normal'
}

export function classeBadgePrioridade(valor: PrioridadeTicket | string | undefined | null): string {
  switch (valor) {
    case 'urgente':
      return 'bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-200'
    case 'alta':
      return 'bg-amber-100 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200'
    case 'baixa':
      return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
    default:
      return 'bg-sky-50 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'
  }
}
