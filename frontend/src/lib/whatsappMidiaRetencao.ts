export const MSG_MIDIA_WHATSAPP_INDISPONIVEL =
  'Esta mídia não está mais disponível. Peça para o cliente enviar novamente.'

export const MSG_MIDIA_WHATSAPP_TEMPORARIA =
  'Não foi possível recuperar a mídia agora. Tente de novo.'

export function midiaWhatsappIndisponivel(m: { midia_estado?: string | null }): boolean {
  return (m.midia_estado || '').toLowerCase() === 'indisponivel'
}

export function midiaWhatsappExpiradaLocal(m: { midia_estado?: string | null }): boolean {
  return (m.midia_estado || '').toLowerCase() === 'expirada_local'
}

function codigoDoErro(err: unknown): string | null {
  if (!err || typeof err !== 'object' || !('body' in err)) return null
  const body = (err as { body?: unknown }).body
  if (body && typeof body === 'object' && body !== null && 'codigo' in body) {
    const c = (body as { codigo?: unknown }).codigo
    return typeof c === 'string' ? c : null
  }
  return null
}

export function erroMidiaWhatsappIndisponivel(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const status = 'status' in err ? Number((err as { status?: number }).status) : 0
  if (status === 410) return true
  return codigoDoErro(err) === 'midia_indisponivel'
}

export function erroMidiaWhatsappTemporaria(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const status = 'status' in err ? Number((err as { status?: number }).status) : 0
  if (status === 503) return true
  return codigoDoErro(err) === 'midia_temporariamente_indisponivel'
}
