/** Preferências de MIME para nota de voz (WhatsApp / Evolution PTT). */
const MIME_CANDIDATOS = [
  'audio/ogg;codecs=opus',
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
] as const

/** Blobs só com cabeçalho (sem samples) costumam ficar abaixo disto. */
export const TAMANHO_MIN_AUDIO_BYTES = 512

export function escolherMimeGravacao(): string {
  if (typeof MediaRecorder === 'undefined' || typeof MediaRecorder.isTypeSupported !== 'function') {
    return ''
  }
  for (const mime of MIME_CANDIDATOS) {
    if (MediaRecorder.isTypeSupported(mime)) return mime
  }
  return ''
}

export function extensaoAudioMime(mime: string): string {
  const m = (mime || '').toLowerCase()
  if (m.includes('ogg')) return 'ogg'
  if (m.includes('mp4') || m.includes('mpeg') || m.includes('m4a') || m.includes('aac')) return 'm4a'
  if (m.includes('wav')) return 'wav'
  return 'webm'
}

export function criarMediaRecorder(stream: MediaStream): MediaRecorder {
  const mime = escolherMimeGravacao()
  return mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
}

export function ficheiroDeBlobGravacao(blob: Blob): File {
  const type = blob.type || 'audio/webm'
  const ext = extensaoAudioMime(type)
  return new File([blob], `audio-${Date.now()}.${ext}`, { type })
}
