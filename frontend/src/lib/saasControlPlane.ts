/** Flag Vite para atalhos públicos (landing) do control-plane SaaS. */
export function isSaasControlPlaneFrontend(): boolean {
  const raw = (import.meta.env.VITE_SAAS_CONTROL_PLANE as string | undefined)?.trim().toLowerCase()
  return raw === '1' || raw === 'true' || raw === 'yes'
}

export const SAAS_LICENCAS_PATH = '/saas/licencas'

const DEFAULT_BASE_DOMAIN = 'deskrudder.com.br'

/** Domínio base das instâncias (ex.: deskrudder.com.br). */
export function saasBaseDomain(override?: string | null): string {
  const fromEnv = (import.meta.env.VITE_SAAS_PROVISION_BASE_DOMAIN as string | undefined)?.trim()
  const raw = (override || fromEnv || DEFAULT_BASE_DOMAIN).trim().replace(/^\.+/, '')
  return raw || DEFAULT_BASE_DOMAIN
}

/** URL pública canónica a partir do slug (único campo escolhido pelo ops/cliente). */
export function urlInstanciaFromSlug(slug: string | null | undefined, baseDomain?: string | null): string {
  const s = (slug || '').trim().toLowerCase()
  if (!s) return ''
  return `https://${s}.${saasBaseDomain(baseDomain)}/`
}

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

export function labelAprovacao(status: string | null | undefined): string {
  switch (status) {
    case 'pendente':
      return 'Pendente'
    case 'aprovado':
      return 'Aprovado'
    case 'rejeitado':
      return 'Rejeitado'
    default:
      return '—'
  }
}

export function badgeClassAprovacao(status: string | null | undefined): string {
  switch (status) {
    case 'aprovado':
      return 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-600/15 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-600/30'
    case 'pendente':
      return 'bg-amber-50 text-amber-900 ring-1 ring-amber-600/20 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-600/30'
    case 'rejeitado':
      return 'bg-red-50 text-red-800 ring-1 ring-red-600/15 dark:bg-red-950/40 dark:text-red-300 dark:ring-red-600/30'
    default:
      return 'bg-slate-100 text-slate-600 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-400'
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

/** Normaliza URL pública para abrir em nova aba. */
export function hrefInstanciaCliente(url: string | null | undefined): string | null {
  const raw = (url || '').trim()
  if (!raw) return null
  if (/^https?:\/\//i.test(raw)) return raw
  return `https://${raw}`
}

/** Em local, a URL pública (*.deskrudder.com.br) não resolve DNS — usar a API na porta. */
export function hrefAcessoLocalApi(apiPort: number | null | undefined): string | null {
  if (apiPort == null || !Number.isFinite(apiPort) || apiPort < 1) return null
  return `http://127.0.0.1:${apiPort}/health`
}

export function isAmbienteLocalBrowser(): boolean {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1'
}

/** Melhor link para abrir a instância (local → porta API; produção → URL pública). */
export function hrefAcessoCliente(opts: {
  instanciaUrl?: string | null
  slug?: string | null
  apiPort?: number | null
  baseDomain?: string | null
}): { href: string; label: string; modo: 'local' | 'publico' } | null {
  const urlPublica =
    hrefInstanciaCliente(opts.instanciaUrl) ||
    hrefInstanciaCliente(urlInstanciaFromSlug(opts.slug, opts.baseDomain))

  if (isAmbienteLocalBrowser()) {
    const local = hrefAcessoLocalApi(opts.apiPort)
    if (local) {
      return {
        href: local,
        label: `http://127.0.0.1:${opts.apiPort}/health`,
        modo: 'local',
      }
    }
  }

  if (!urlPublica) return null
  return { href: urlPublica, label: urlPublica, modo: 'publico' }
}
