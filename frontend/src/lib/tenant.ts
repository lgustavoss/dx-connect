/**
 * Modo legado: tenant numérico no host ``{tenantId}.connect.exemplo.com``.
 * Produção (single-tenant): uma instância por cliente; host livre (ex. slug.connect.dominio).
 */
export function isMultiTenantMode(): boolean {
  const raw = (import.meta.env.VITE_MULTI_TENANT as string | undefined)?.trim().toLowerCase()
  if (raw === 'true' || raw === '1') return true
  if (raw === 'false' || raw === '0') return false
  return false
}

export function resolveTenantIdFromHostname(hostname?: string): number {
  if (!isMultiTenantMode()) {
    return defaultTenantId()
  }
  const host = (hostname ?? window.location.hostname).toLowerCase()
  const base = (import.meta.env.VITE_CONNECT_APP_BASE_DOMAIN as string | undefined)?.trim().toLowerCase()
  if (base) {
    if (host === base) {
      return defaultTenantId()
    }
    const suffix = `.${base}`
    if (host.endsWith(suffix)) {
      const prefix = host.slice(0, -suffix.length)
      if (prefix && !prefix.includes('.') && /^\d+$/.test(prefix)) {
        return Number.parseInt(prefix, 10)
      }
    }
  }
  return defaultTenantId()
}

export function defaultTenantId(): number {
  const raw = (import.meta.env.VITE_DEFAULT_TENANT_ID as string | undefined)?.trim()
  if (raw && /^\d+$/.test(raw)) {
    return Number.parseInt(raw, 10)
  }
  return 1
}

/** URL pública do painel (single-tenant: VITE_CLIENT_APP_HOST; legado: subdomínio numérico). */
export function tenantAppOrigin(tenantId: number): string | null {
  const clientHost = (import.meta.env.VITE_CLIENT_APP_HOST as string | undefined)?.trim()
  if (clientHost) {
    const proto = window.location.protocol === 'https:' ? 'https' : 'http'
    return `${proto}://${clientHost.replace(/^https?:\/\//, '')}`
  }
  if (!isMultiTenantMode()) {
    return window.location.origin
  }
  const base = (import.meta.env.VITE_CONNECT_APP_BASE_DOMAIN as string | undefined)?.trim()
  if (!base) return null
  const proto = window.location.protocol === 'https:' ? 'https' : 'http'
  return `${proto}://${tenantId}.${base}`
}
