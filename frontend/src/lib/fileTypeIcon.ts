/** Ícone e rótulo por extensão ou MIME (#453). */

export type FileTypeVisual = {
  emoji: string
  label: string
}

const EXT_MAP: Record<string, FileTypeVisual> = {
  pdf: { emoji: '📕', label: 'PDF' },
  doc: { emoji: '📝', label: 'Word' },
  docx: { emoji: '📝', label: 'Word' },
  xls: { emoji: '📊', label: 'Excel' },
  xlsx: { emoji: '📊', label: 'Excel' },
  ppt: { emoji: '📽️', label: 'PowerPoint' },
  pptx: { emoji: '📽️', label: 'PowerPoint' },
  txt: { emoji: '📃', label: 'Texto' },
  csv: { emoji: '📃', label: 'CSV' },
  zip: { emoji: '🗜️', label: 'Compactado' },
  rar: { emoji: '🗜️', label: 'Compactado' },
  '7z': { emoji: '🗜️', label: 'Compactado' },
  jpg: { emoji: '🖼️', label: 'Imagem' },
  jpeg: { emoji: '🖼️', label: 'Imagem' },
  png: { emoji: '🖼️', label: 'Imagem' },
  gif: { emoji: '🖼️', label: 'Imagem' },
  webp: { emoji: '🖼️', label: 'Imagem' },
  mp3: { emoji: '🎵', label: 'Áudio' },
  wav: { emoji: '🎵', label: 'Áudio' },
  ogg: { emoji: '🎵', label: 'Áudio' },
  mp4: { emoji: '🎬', label: 'Vídeo' },
  avi: { emoji: '🎬', label: 'Vídeo' },
  mov: { emoji: '🎬', label: 'Vídeo' },
  webm: { emoji: '🎬', label: 'Vídeo' },
}

const MIME_PREFIX: [string, FileTypeVisual][] = [
  ['application/pdf', EXT_MAP.pdf],
  ['application/msword', EXT_MAP.doc],
  ['application/vnd.openxmlformats-officedocument.wordprocessingml', EXT_MAP.docx],
  ['application/vnd.ms-excel', EXT_MAP.xls],
  ['application/vnd.openxmlformats-officedocument.spreadsheetml', EXT_MAP.xlsx],
  ['application/vnd.ms-powerpoint', EXT_MAP.ppt],
  ['application/vnd.openxmlformats-officedocument.presentationml', EXT_MAP.pptx],
  ['text/plain', EXT_MAP.txt],
  ['text/csv', EXT_MAP.csv],
  ['application/zip', EXT_MAP.zip],
  ['application/x-rar', EXT_MAP.rar],
  ['image/', EXT_MAP.jpg],
  ['audio/', EXT_MAP.mp3],
  ['video/', EXT_MAP.mp4],
]

function extensaoDeNome(nome?: string | null): string | null {
  if (!nome) return null
  const base = nome.split(/[/\\]/).pop() ?? nome
  const idx = base.lastIndexOf('.')
  if (idx <= 0) return null
  return base.slice(idx + 1).toLowerCase()
}

export function visualTipoArquivo(
  nome?: string | null,
  mime?: string | null,
): FileTypeVisual {
  const ext = extensaoDeNome(nome)
  if (ext && EXT_MAP[ext]) return EXT_MAP[ext]
  const m = (mime ?? '').toLowerCase()
  for (const [prefix, visual] of MIME_PREFIX) {
    if (m.startsWith(prefix)) return visual
  }
  return { emoji: '📄', label: 'Ficheiro' }
}

export function rotuloDownloadArquivo(
  nome?: string | null,
  mime?: string | null,
  tipoMidia?: string | null,
): string {
  const tipo = (tipoMidia ?? '').toLowerCase()
  const nomeLimpo = (nome ?? '').trim()
  if (nomeLimpo) {
    const v = visualTipoArquivo(nomeLimpo, mime)
    return `${v.emoji} ${nomeLimpo}`
  }
  if (tipo === 'audio') return '🔊 Baixar áudio'
  if (tipo === 'video') return '🎬 Baixar vídeo'
  if (tipo === 'imagem' || tipo === 'figurinha') return '📷 Baixar imagem'
  const v = visualTipoArquivo(nome, mime)
  return `${v.emoji} Baixar ${v.label}`
}
