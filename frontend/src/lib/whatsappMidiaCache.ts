/** Cache de blobs/object URLs por mensagem — evita refetch e ERR_INSUFFICIENT_RESOURCES (#471). */

const objectUrls = new Map<string, string>()
const inflight = new Map<string, Promise<string>>()

function cacheKey(chatId: number, mensagemId: number) {
  return `${chatId}:${mensagemId}`
}

export function getWhatsappMidiaObjectUrl(chatId: number, mensagemId: number): string | null {
  return objectUrls.get(cacheKey(chatId, mensagemId)) ?? null
}

export async function resolveWhatsappMidiaObjectUrl(
  chatId: number,
  mensagemId: number,
  fetchBlob: () => Promise<Blob>,
): Promise<string> {
  const key = cacheKey(chatId, mensagemId)
  const cached = objectUrls.get(key)
  if (cached) return cached

  const pending = inflight.get(key)
  if (pending) return pending

  const promise = fetchBlob().then((blob) => {
    const existing = objectUrls.get(key)
    if (existing) return existing
    const url = URL.createObjectURL(blob)
    objectUrls.set(key, url)
    return url
  }).finally(() => {
    inflight.delete(key)
  })

  inflight.set(key, promise)
  return promise
}

export function revokeWhatsappMidiaForChat(chatId: number) {
  const prefix = `${chatId}:`
  for (const [key, url] of objectUrls.entries()) {
    if (key.startsWith(prefix)) {
      URL.revokeObjectURL(url)
      objectUrls.delete(key)
    }
  }
}
