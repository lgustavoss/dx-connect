import { MARKETING_SITE_URL } from '../brand/tokens'
import { mensagemErroApi } from '../api/errorMessage'

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

export const LOGIN_ACCOUNT_STORAGE_KEY = 'deskrudder-login-account'

/** Hostname do site comercial (sem www). */
export function marketingApexHost(): string {
  try {
    return new URL(MARKETING_SITE_URL).hostname.replace(/^www\./i, '').toLowerCase()
  } catch {
    return 'deskrudder.com.br'
  }
}

/** True na landing comercial (apex / www), não em subdomínio de cliente. */
export function isMarketingHost(hostname = typeof window !== 'undefined' ? window.location.hostname : ''): boolean {
  const host = hostname.toLowerCase()
  const apex = marketingApexHost()
  return host === apex || host === `www.${apex}`
}

/** Normaliza e valida slug da conta (subdomínio). Retorna null se inválido. */
export function normalizeClientSlug(raw: string): string | null {
  const slug = raw.trim().toLowerCase()
  if (!slug || !SLUG_RE.test(slug) || RESERVED_SLUGS.has(slug)) return null
  return slug
}

/** Origem HTTPS do painel do cliente: https://{slug}.deskrudder.com.br */
export function clientAppOrigin(slug: string): string {
  const normalized = normalizeClientSlug(slug)
  if (!normalized) {
    throw new Error('Conta inválida')
  }
  return `https://${normalized}.${marketingApexHost()}`
}

/** API da instância: https://api-{slug}.deskrudder.com.br */
export function clientApiOrigin(slug: string): string {
  const normalized = normalizeClientSlug(slug)
  if (!normalized) {
    throw new Error('Conta inválida')
  }
  return `https://api-${normalized}.${marketingApexHost()}`
}

export type ClientLoginTokens = {
  access_token: string
  refresh_token?: string | null
  must_change_password?: boolean
}

/** Autentica na API do cliente a partir da apex (CORS). */
export async function loginAgainstClientInstance(
  slug: string,
  email: string,
  senha: string,
): Promise<ClientLoginTokens> {
  const apiOrigin = clientApiOrigin(slug)
  let res: Response
  try {
    res = await fetch(`${apiOrigin}/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email, senha }),
    })
  } catch {
    throw new Error(
      'Não foi possível contactar o painel desta conta. Verifique o identificador ou tente mais tarde.',
    )
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    let msg = mensagemErroApi(body, res.status)
    if (res.status === 401 || msg.startsWith('Não foi possível concluir')) {
      msg = 'E-mail ou senha inválidos.'
    }
    if (res.status === 404 || res.status >= 502) {
      msg = 'Conta não encontrada ou temporariamente indisponível.'
    }
    throw new Error(msg)
  }
  if (!body || typeof (body as ClientLoginTokens).access_token !== 'string') {
    throw new Error('Resposta de login inválida.')
  }
  return body as ClientLoginTokens
}

/** URL no subdomínio que recebe a sessão via fragmento (não vai para logs do servidor). */
export function buildSessionHandoffUrl(
  slug: string,
  tokens: ClientLoginTokens,
  lembrarMe: boolean,
): string {
  const params = new URLSearchParams()
  params.set('access_token', tokens.access_token)
  if (tokens.refresh_token) params.set('refresh_token', tokens.refresh_token)
  params.set('lembrar', lembrarMe ? '1' : '0')
  if (tokens.must_change_password) params.set('must_change_password', '1')
  return `${clientAppOrigin(slug)}/auth/sessao#${params.toString()}`
}

export function readRememberedAccount(): string {
  try {
    return localStorage.getItem(LOGIN_ACCOUNT_STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function writeRememberedAccount(slug: string): void {
  try {
    localStorage.setItem(LOGIN_ACCOUNT_STORAGE_KEY, slug)
  } catch {
    /* storage indisponível */
  }
}
