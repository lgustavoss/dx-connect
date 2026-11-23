/**
 * Origem da API a partir do host do painel.
 * `{slug}.deskrudder.com.br` → `https://api-{slug}.deskrudder.com.br`.
 * Hosts fora do apex DeskRudder (legado) não são alvo de runtime.
 */

const RESERVED_SLUGS = new Set([
  'www',
  'api',
  'mail',
  'ftp',
  'cdn',
  'static',
  'app',
  'admin',
  'status',
  'portal',
])

const SLUG_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/

export const DESKRUDDER_APEX = 'deskrudder.com.br'

export function normalizeClientSlug(raw: string): string | null {
  const slug = raw.trim().toLowerCase()
  if (!slug || !SLUG_RE.test(slug) || RESERVED_SLUGS.has(slug)) return null
  return slug
}

export function clientAppOrigin(slug: string, apex = DESKRUDDER_APEX): string {
  const normalized = normalizeClientSlug(slug)
  if (!normalized) {
    throw new Error('Conta inválida')
  }
  return `https://${normalized}.${apex}`
}

export function clientApiOrigin(slug: string, apex = DESKRUDDER_APEX): string {
  const normalized = normalizeClientSlug(slug)
  if (!normalized) {
    throw new Error('Conta inválida')
  }
  return `https://api-${normalized}.${apex}`
}

/** Hostname de API ou painel que o produto não pode mais chamar. */
export function isLegacyRuntimeHost(hostname: string): boolean {
  const host = hostname.trim().toLowerCase().replace(/\.$/, '')
  if (!host) return false
  return host === 'duplexsoft.com.br' || host.endsWith('.duplexsoft.com.br')
}

/** Descarta URL de build que ainda aponta para host legado (ou que não é http/https). */
export function sanitizeBakedApiUrl(url: string | undefined | null): string | undefined {
  const trimmed = url?.trim()
  if (!trimmed) return undefined
  try {
    const parsed = new URL(trimmed)
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return undefined
    if (isLegacyRuntimeHost(parsed.hostname)) return undefined
    return trimmed.replace(/\/+$/, '')
  } catch {
    return undefined
  }
}

/**
 * API do painel quando a página está em `{slug}.<apex>`.
 * Apex, www, localhost e host de API (`api`, `api-*`) devolvem null — aí vale o `VITE_API_URL` saneado.
 */
export function apiOriginFromPanelHost(hostname: string, apex = DESKRUDDER_APEX): string | null {
  const host = hostname.trim().toLowerCase().replace(/\.$/, '')
  const base = apex.trim().toLowerCase().replace(/^\.+/, '')
  if (!host || !base) return null
  if (host === 'localhost' || host === '127.0.0.1') return null
  if (host === base || host === `www.${base}`) return null
  const suffix = `.${base}`
  if (!host.endsWith(suffix)) return null
  const slug = host.slice(0, -suffix.length)
  if (!slug || slug.includes('.') || slug.startsWith('api-')) return null
  try {
    return clientApiOrigin(slug, base)
  } catch {
    return null
  }
}
