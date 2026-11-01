import { Platform } from 'react-native'

const SLUG_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/
const RESERVED = new Set(['www', 'api', 'mail', 'ftp', 'cdn', 'static', 'app', 'admin', 'status', 'portal'])
const APEX = 'deskrudder.com.br'

export const DEFAULT_SLUG = 'duplexsoft'
/** Só no `expo start --web`: o browser não fala com a API de produção (CORS). */
export const WEB_API_PROXY = 'http://localhost:8788'

export function normalizeSlug(raw: string): string | null {
  const slug = raw.trim().toLowerCase()
  if (slug === 'local') return 'local'
  if (!slug || !SLUG_RE.test(slug) || RESERVED.has(slug)) return null
  return slug
}

export function usesWebApiProxy(): boolean {
  return Platform.OS === 'web'
}

export function instanceHeaders(slug: string): Record<string, string> {
  const normalized = normalizeSlug(slug)
  if (!normalized || !usesWebApiProxy()) return {}
  return { 'X-Instance-Slug': normalized }
}

/** Origem da API (sem /v1). No web devolve o proxy local; no celular a API real. */
export function apiOriginFromSlug(slug: string): string {
  const normalized = normalizeSlug(slug)
  if (!normalized) {
    throw new Error('Instância inválida')
  }
  if (usesWebApiProxy()) return WEB_API_PROXY
  if (normalized === 'local') {
    return Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000'
  }
  return `https://api-${normalized}.${APEX}`
}

/** URL pública da API (para mostrar no perfil), nunca o proxy. */
export function publicApiOriginFromSlug(slug: string): string {
  const normalized = normalizeSlug(slug)
  if (!normalized) return slug
  if (normalized === 'local') return 'http://127.0.0.1:8000'
  return `https://api-${normalized}.${APEX}`
}

export async function pingHealth(slug: string): Promise<void> {
  const origin = apiOriginFromSlug(slug)
  const res = await fetch(`${origin.replace(/\/+$/, '')}/health`, {
    headers: { Accept: 'application/json', ...instanceHeaders(slug) },
  })
  if (!res.ok) {
    throw new Error(`Instância indisponível (HTTP ${res.status})`)
  }
}
