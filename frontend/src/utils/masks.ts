export { maskCnpjCpf, digitsOnly, isCpf, isCnpj } from './maskCnpjCpf'

/** CEP 00000-000 */
export function maskCep(value: string): string {
  const d = value.replace(/\D/g, '').slice(0, 8)
  if (d.length <= 5) return d
  return `${d.slice(0, 5)}-${d.slice(5)}`
}

/**
 * Telefone BR: fixo (10) ou celular (11 dígitos com DDD).
 * (00) 0000-0000 | (00) 00000-0000
 */
export function maskTelefoneBr(value: string): string {
  const d = value.replace(/\D/g, '').slice(0, 11)
  if (d.length === 0) return ''
  if (d.length <= 2) return `(${d}`
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
}

/** Exibe telefone já salvo (só dígitos ou já mascarado). */
export function formatTelefoneBrExibicao(value: string | null | undefined): string {
  if (!value?.trim()) return ''
  return maskTelefoneBr(value)
}

/**
 * Formata `wa_id` WhatsApp para exibição na mesa (#684).
 * Ex.: `5511987654321` → `+55 (11) 98765-4321`
 */
export function formatWaIdExibicao(waId: string | null | undefined): string {
  if (!waId?.trim()) return ''
  const raw = waId.trim().split('@')[0] || waId.trim()
  const digits = raw.replace(/\D/g, '')
  if (digits.startsWith('55') && (digits.length === 12 || digits.length === 13)) {
    const local = formatTelefoneBrExibicao(digits.slice(2))
    return local ? `+55 ${local}` : `+${digits}`
  }
  if (digits.length >= 10 && digits.length <= 11) {
    return formatTelefoneBrExibicao(digits)
  }
  if (raw.startsWith('+')) return raw
  return digits ? `+${digits}` : raw
}

/** IE alfanumérica comum (apenas letras e números, máx. 20). */
export function maskInscricaoEstadual(value: string): string {
  return value.replace(/[^a-zA-Z0-9]/g, '').slice(0, 20).toUpperCase()
}
