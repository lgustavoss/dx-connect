/** Remove metadados técnicos de e-mails legados exibidos no corpo da mensagem. */
export function corpoMensagemEmailVisivel(corpo: string): string {
  const lines = corpo.split('\n')
  const out: string[] = []
  let pastMeta = false
  for (const line of lines) {
    const t = line.trim()
    if (!pastMeta && (t.startsWith('Remetente:') || t.startsWith('Message-ID:'))) {
      continue
    }
    if (!pastMeta && t === '' && out.length === 0) {
      continue
    }
    pastMeta = true
    out.push(line)
  }
  const joined = out.join('\n').trim()
  return joined || corpo.trim()
}

/** Extrai remetente de mensagens antigas que embutiam metadados no corpo. */
export function remetenteLegadoDoCorpo(corpo: string): string | null {
  const m = corpo.match(/^Remetente:\s*(.+)$/m)
  return m?.[1]?.trim() || null
}

export function autorRodapeMensagem(msg: {
  tipo: string
  atendente_nome?: string | null
  autor_externo?: string | null
  corpo: string
}): string {
  if (msg.tipo === 'abertura' || msg.tipo === 'email_cliente') {
    return (
      msg.autor_externo?.trim() ||
      remetenteLegadoDoCorpo(msg.corpo) ||
      (msg.tipo === 'email_cliente' ? 'Cliente (e-mail)' : '—')
    )
  }
  return msg.atendente_nome?.trim() || '—'
}
