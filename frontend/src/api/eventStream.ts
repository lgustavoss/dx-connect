import {
  API_VERSION_PREFIX,
  getAuthToken,
  invalidateSessionAndRedirectToLogin,
  resolvedApiBaseUrl,
} from './client'
import { isMultiTenantMode, resolveTenantIdFromHostname } from '../lib/tenant'

export interface RealtimeEnvelope {
  type: string
  payload: Record<string, unknown>
}

export type RealtimeEventHandler = (payload: Record<string, unknown>, envelope: RealtimeEnvelope) => void

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'

function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY) || localStorage.getItem(REFRESH_TOKEN_KEY)
}

function setAccessToken(accessToken: string): void {
  if (localStorage.getItem(REFRESH_TOKEN_KEY)) {
    localStorage.setItem(TOKEN_KEY, accessToken)
    return
  }
  sessionStorage.setItem(TOKEN_KEY, accessToken)
}

async function refreshAccessTokenForStream(): Promise<string | null> {
  const refresh_token = getRefreshToken()
  if (!refresh_token) return null
  const base = resolvedApiBaseUrl()
  if (!base) return null
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (isMultiTenantMode()) {
    headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
  }
  const res = await fetch(`${base}${API_VERSION_PREFIX}/auth/refresh`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ refresh_token }),
  })
  if (!res.ok) return null
  const body = (await res.json()) as { access_token?: string }
  if (!body.access_token) return null
  setAccessToken(body.access_token)
  return body.access_token
}

export function buildEventStreamUrl(): string {
  const base = resolvedApiBaseUrl()
  if (!base) {
    throw new Error('Informe a conta da empresa para ligar ao painel.')
  }
  return `${base}${API_VERSION_PREFIX}/events/stream`
}

function authHeaders(token: string): Record<string, string> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
  if (isMultiTenantMode()) {
    headers['X-Dx-Tenant-Id'] = String(resolveTenantIdFromHostname())
  }
  return headers
}

function parseSseBlocks(buffer: string): { events: RealtimeEnvelope[]; rest: string } {
  const events: RealtimeEnvelope[] = []
  let rest = buffer
  while (true) {
    const idx = rest.indexOf('\n\n')
    if (idx === -1) break
    const block = rest.slice(0, idx)
    rest = rest.slice(idx + 2)
    const dataLine = block.split('\n').find((line) => line.startsWith('data: '))
    if (!dataLine) continue
    try {
      events.push(JSON.parse(dataLine.slice(6)) as RealtimeEnvelope)
    } catch {
      if (import.meta.env.DEV) {
        console.warn('[SSE] JSON inválido:', dataLine)
      }
    }
  }
  return { events, rest }
}

async function openAuthenticatedStream(
  signal: AbortSignal,
  retried401: boolean,
): Promise<Response> {
  let token = getAuthToken()
  if (!token) {
    throw new Error('Token não informado')
  }
  const res = await fetch(buildEventStreamUrl(), {
    headers: authHeaders(token),
    signal,
  })
  if (res.status === 401 && !retried401) {
    const refreshed = await refreshAccessTokenForStream()
    if (refreshed) {
      return openAuthenticatedStream(signal, true)
    }
    invalidateSessionAndRedirectToLogin()
    throw new Error('Sessão expirada')
  }
  if (res.status === 401) {
    invalidateSessionAndRedirectToLogin()
    throw new Error('Sessão expirada')
  }
  if (!res.ok) {
    throw new Error(`SSE HTTP ${res.status}`)
  }
  if (!res.body) {
    throw new Error('SSE sem body')
  }
  return res
}

export type EventStreamRunOptions = {
  signal: AbortSignal
  onEvent: (event: RealtimeEnvelope) => void
  onConnected?: () => void
  onError?: (err: Error) => void
}

/** Lê o stream até abort ou erro de rede. */
export async function runEventStreamLoop(options: EventStreamRunOptions): Promise<void> {
  const { signal, onEvent, onConnected, onError } = options
  let response: Response
  try {
    response = await openAuthenticatedStream(signal, false)
  } catch (err) {
    onError?.(err instanceof Error ? err : new Error(String(err)))
    throw err
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (!signal.aborted) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parsed = parseSseBlocks(buffer)
      buffer = parsed.rest
      for (const event of parsed.events) {
        if (event.type === 'connected') {
          onConnected?.()
        }
        onEvent(event)
      }
    }
  } catch (err) {
    if (!signal.aborted) {
      onError?.(err instanceof Error ? err : new Error(String(err)))
      throw err
    }
  } finally {
    try {
      await reader.cancel()
    } catch {
      /* ignore */
    }
  }
}

export const EVENT_STREAM_MAX_FAILURES = 3
export const EVENT_STREAM_BASE_RECONNECT_MS = 1000
export const EVENT_STREAM_MAX_RECONNECT_MS = 30000

export function nextReconnectDelayMs(failureCount: number): number {
  const exp = EVENT_STREAM_BASE_RECONNECT_MS * 2 ** Math.max(0, failureCount - 1)
  return Math.min(exp, EVENT_STREAM_MAX_RECONNECT_MS)
}

export function sleepMs(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const timer = window.setTimeout(() => {
      signal.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    const onAbort = () => {
      window.clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }
    signal.addEventListener('abort', onAbort, { once: true })
  })
}
