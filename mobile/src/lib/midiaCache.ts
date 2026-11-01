const urls = new Map<string, string>()
const inflight = new Map<string, Promise<string>>()

function key(chatId: number, mensagemId: number) {
  return `${chatId}:${mensagemId}`
}

export function getMidiaUrl(chatId: number, mensagemId: number): string | null {
  return urls.get(key(chatId, mensagemId)) ?? null
}

export async function resolveMidiaUrl(
  chatId: number,
  mensagemId: number,
  fetchBlob: () => Promise<Blob>,
): Promise<string> {
  const k = key(chatId, mensagemId)
  const hit = urls.get(k)
  if (hit) return hit
  const pending = inflight.get(k)
  if (pending) return pending
  const promise = fetchBlob()
    .then((blob) => {
      const existing = urls.get(k)
      if (existing) return existing
      const url = URL.createObjectURL(blob)
      urls.set(k, url)
      return url
    })
    .finally(() => inflight.delete(k))
  inflight.set(k, promise)
  return promise
}
