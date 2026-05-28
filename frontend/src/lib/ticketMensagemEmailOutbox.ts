/** Estados da fila de e-mail em mensagens públicas (#140 / #141). */

export type EmailOutboxStatus =
  | 'pendente_envio'
  | 'em_edicao'
  | 'enviando'
  | 'enviada'
  | 'cancelada'

export function rotuloStatusEmail(status: string | null | undefined): string | null {
  switch (status) {
    case 'pendente_envio':
      return 'E-mail agendado'
    case 'em_edicao':
      return 'Em edição'
    case 'enviando':
      return 'A enviar e-mail…'
    case 'enviada':
      return 'E-mail enviado ao cliente'
    case 'cancelada':
      return 'Envio por e-mail cancelado'
    default:
      return null
  }
}

export function mensagemEmFilaEmail(status: string | null | undefined): boolean {
  return status === 'pendente_envio' || status === 'em_edicao' || status === 'enviando'
}

export function segundosAteEnvio(scheduledAt: string | null | undefined, nowMs = Date.now()): number | null {
  if (!scheduledAt) return null
  const t = new Date(scheduledAt).getTime()
  if (Number.isNaN(t)) return null
  return Math.max(0, Math.ceil((t - nowMs) / 1000))
}

export function textoContagemEnvio(segundos: number | null): string {
  if (segundos == null) return ''
  if (segundos <= 0) return 'envio imediato'
  if (segundos < 60) return `envia em ${segundos}s`
  const m = Math.ceil(segundos / 60)
  return `envia em ~${m} min`
}
