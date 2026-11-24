import { Platform } from 'react-native'
import { File as ExpoFile, Paths } from 'expo-file-system'

const urls = new Map<string, string>()
const inflight = new Map<string, Promise<string>>()

function key(chatId: number, mensagemId: number) {
  return `${chatId}:${mensagemId}`
}

function extensaoDoTipo(contentType?: string | null): string {
  const t = (contentType || '').toLowerCase()
  if (t.includes('ogg') || t.includes('opus')) return 'ogg'
  if (t.includes('mpeg') || t.includes('mp3')) return 'mp3'
  if (t.includes('m4a') || t === 'audio/mp4') return 'm4a'
  if (t.includes('mp4') || t.includes('m4v')) return 'mp4'
  if (t.includes('webm')) return 'webm'
  if (t.includes('jpeg') || t.includes('jpg')) return 'jpg'
  if (t.includes('png')) return 'png'
  if (t.includes('webp')) return 'webp'
  if (t.includes('gif')) return 'gif'
  if (t.includes('pdf')) return 'pdf'
  return 'bin'
}

async function bytesParaUrlLocal(
  bytes: ArrayBuffer,
  contentType: string | null,
  chatId: number,
  mensagemId: number,
): Promise<string> {
  // Nunca use URL.createObjectURL no nativo: o BlobManager do RN costuma
  // estar sem BLOB_URL_PREFIX e estoura "Cannot create URL for blob!".
  const arquivo = new ExpoFile(
    Paths.cache,
    'wa-midia',
    `${chatId}-${mensagemId}.${extensaoDoTipo(contentType)}`,
  )
  arquivo.create({ intermediates: true, overwrite: true })
  await arquivo.write(bytes)
  return arquivo.uri
}

export function getMidiaUrl(chatId: number, mensagemId: number): string | null {
  return urls.get(key(chatId, mensagemId)) ?? null
}

export type MidiaBaixada = {
  bytes: ArrayBuffer
  contentType?: string | null
}

/**
 * Resolve URI reproduzível: no web usa blob:; no device grava no cache em disco.
 * O downloader deve devolver bytes brutos — não passe por `response.blob()` no nativo.
 */
export async function resolveMidiaUrl(
  chatId: number,
  mensagemId: number,
  baixar: () => Promise<MidiaBaixada>,
): Promise<string> {
  const k = key(chatId, mensagemId)
  const hit = urls.get(k)
  if (hit) return hit
  const pending = inflight.get(k)
  if (pending) return pending
  const promise = baixar()
    .then(async ({ bytes, contentType }) => {
      const existing = urls.get(k)
      if (existing) return existing
      let url: string
      if (Platform.OS === 'web') {
        url = URL.createObjectURL(new Blob([bytes], { type: contentType || undefined }))
      } else {
        url = await bytesParaUrlLocal(bytes, contentType ?? null, chatId, mensagemId)
      }
      urls.set(k, url)
      return url
    })
    .finally(() => inflight.delete(k))
  inflight.set(k, promise)
  return promise
}
