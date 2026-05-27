/**
 * Tenant numérico a partir do host: ``{tenantId}.connect.exemplo.com``.
 * Em dev (localhost), usa VITE_DEFAULT_TENANT_ID ou 1.
 */
export function resolveTenantIdFromHostname(hostname?: string): number {
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

/** URL de acesso sugerida para o tenant (subdomínio). */
export function tenantAppOrigin(tenantId: number): string | null {
  const base = (import.meta.env.VITE_CONNECT_APP_BASE_DOMAIN as string | undefined)?.trim()
  if (!base) return null
  const proto = window.location.protocol === 'https:' ? 'https' : 'http'
  return `${proto}://${tenantId}.${base}`
}
