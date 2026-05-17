/** Remove metadados técnicos e citação da mensagem anterior (espelha o backend). */
export function corpoMensagemEmailVisivel(corpo: string): string {
  let raw = (corpo || '').trim()
  if (!raw) return ''

  if (raw.toLowerCase().startsWith('(mensagem recebida por e-mail') && raw.toLowerCase().includes('corpo não obtido')) {
    return ''
  }

  const lines = raw.split('\n')
  while (lines.length > 0) {
    const t = lines[0].trim()
    if (!t) {
      lines.shift()
      continue
    }
    if (isMetaLine(t)) {
      lines.shift()
      continue
    }
    break
  }
  while (lines.length > 0 && !lines[0].trim()) {
    lines.shift()
  }

  raw = lines.join('\n').trim()
  raw = stripQuotedReply(raw)
  return raw.trim()
}

function isMetaLine(t: string): boolean {
  const tl = t.toLowerCase()
  if (tl.startsWith('mensagem recebida por e-mail')) return true
  if (tl.startsWith('(mensagem recebida por e-mail')) return true
  if (tl.startsWith('remetente:')) return true
  if (/^message[\s-]?id\s*:/i.test(t)) return true
  return false
}

function stripQuotedReply(text: string): string {
  const patterns = [
    /\n-{2,}\s*Original Message\s*-{2,}\s*/i,
    /^\s*Em\s+.+?\bescreveu:\s*$/im,
    /^\s*On\s+.+?\bwrote:\s*$/im,
  ]
  let s = text
  for (const pat of patterns) {
    const m = pat.exec(s)
    if (m && m.index != null) {
      s = s.slice(0, m.index).trimEnd()
      break
    }
  }

  const lines = s.split('\n')
  let cut = lines.length
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].trim().startsWith('>')) {
      cut = i
    } else if (cut < lines.length) {
      break
    }
  }
  if (cut < lines.length) {
    s = lines.slice(0, cut).join('\n').trimEnd()
  }
  return s
}

/** Extrai remetente de mensagens antigas que embutiam metadados no corpo. */
export function remetenteLegadoDoCorpo(corpo: string): string | null {
  const m = corpo.match(/^Remetente:\s*(.+)$/im)
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
