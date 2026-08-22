/**
 * Texto de protocolo para UI: formato novo (#T… / #C… / #S…), legado numérico ou WCH-… (#139).
 */
export function exibirProtocolo(raw: string | null | undefined): string {
  const s = (raw || '').trim()
  if (!s) return '—'
  if (s.startsWith('#')) return s
  if (/^\d+$/.test(s)) return `#${s}`
  return s
}
