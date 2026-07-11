export function formatarHoraRelativa(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const diffMin = Math.floor((Date.now() - d.getTime()) / 60000)
  if (diffMin < 1) return 'Agora'
  if (diffMin < 60) return `${diffMin} min`
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)} h`
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

export function previewTexto(texto: string | null | undefined, max = 80): string {
  const t = (texto ?? '').trim()
  if (!t) return 'Sem mensagens'
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

export type FiltroInboxChatInterno = 'todas' | 'direta' | 'setor' | 'grupo'
