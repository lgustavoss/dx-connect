/** Flag Vite para atalhos públicos (landing) do control-plane SaaS. */
export function isSaasControlPlaneFrontend(): boolean {
  const raw = (import.meta.env.VITE_SAAS_CONTROL_PLANE as string | undefined)?.trim().toLowerCase()
  return raw === '1' || raw === 'true' || raw === 'yes'
}

export const SAAS_LICENCAS_PATH = '/saas/licencas'

export const STATUS_CLIENTE_SAAS = [
  { value: 'trial', label: 'Trial' },
  { value: 'ativo', label: 'Ativo' },
  { value: 'suspenso', label: 'Suspenso' },
  { value: 'churn', label: 'Churn' },
] as const

export type StatusClienteSaaS = (typeof STATUS_CLIENTE_SAAS)[number]['value']

export function labelStatusClienteSaaS(status: string): string {
  return STATUS_CLIENTE_SAAS.find((s) => s.value === status)?.label ?? status
}

export function labelProvisionamento(status: string | null | undefined): string {
  switch (status) {
    case 'pendente':
      return 'Pendente'
    case 'em_progresso':
      return 'Em progresso'
    case 'aguardando_ops':
      return 'Aguardando ops'
    case 'sucesso':
      return 'Sucesso'
    case 'falha':
      return 'Falha'
    default:
      return '—'
  }
}

export function renovacaoAlerta(dias: number | null | undefined): 'ok' | 'risco' | 'vencido' | null {
  if (dias == null) return null
  if (dias < 0) return 'vencido'
  if (dias <= 14) return 'risco'
  return 'ok'
}

export function badgeClassStatusClienteSaaS(status: string): string {
  switch (status) {
    case 'ativo':
      return 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-600/15 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-600/30'
    case 'trial':
      return 'bg-sky-50 text-sky-800 ring-1 ring-sky-600/15 dark:bg-sky-950/40 dark:text-sky-300 dark:ring-sky-600/30'
    case 'suspenso':
      return 'bg-amber-50 text-amber-900 ring-1 ring-amber-600/20 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-600/30'
    case 'churn':
      return 'bg-slate-100 text-slate-600 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-400 dark:ring-slate-600/40'
    default:
      return 'bg-slate-100 text-slate-600 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-400'
  }
}

/** Normaliza URL para abrir em nova aba. */
export function hrefInstanciaCliente(url: string | null | undefined): string | null {
  const raw = (url || '').trim()
  if (!raw) return null
  if (/^https?:\/\//i.test(raw)) return raw
  return `https://${raw}`
}
