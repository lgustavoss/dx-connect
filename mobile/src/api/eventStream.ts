import { API_VERSION_PREFIX, apiOrigin, getAccessToken, getStoredSlug } from './client'
import { instanceHeaders } from '../lib/instance'

export type RealtimeEnvelope = {
  type: string
  payload: Record<string, unknown>
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
      /* ignore malformed */
    }
  }
  return { events, rest }
}

/** Uma conexão SSE. Falha silenciosa → a tela continua com polling. */
export async function consumeEventStream(
  onEvent: (envelope: RealtimeEnvelope) => void,
  signal: AbortSignal,
): Promise<void> {
  const origin = await apiOrigin()
  const token = await getAccessToken()
  const slug = (await getStoredSlug()) || ''
  if (!token) return
  const res = await fetch(`${origin}${API_VERSION_PREFIX}/events/stream`, {
    method: 'GET',
    headers: {
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`,
      ...instanceHeaders(slug),
    },
    signal,
  })
  if (!res.ok || !res.body) {
    throw new Error(`SSE HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (!signal.aborted) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parsed = parseSseBlocks(buffer.replace(/\r\n/g, '\n'))
    buffer = parsed.rest
    for (const ev of parsed.events) {
      if (ev.type && ev.type !== 'ping' && ev.type !== 'connected') onEvent(ev)
    }
  }
}
