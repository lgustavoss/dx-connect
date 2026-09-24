export type ContatoCartao = {
  nome: string
  telefone: string | null
}

const LINHA_CONTATO = /^\[(?:Contacto|Contato)\]\s+(.+?)(?:\s+[—–-]\s+(\d{8,}))?\s*$/
const LINHA_ASSINATURA = /^\[[^\]]+\]:?$/

/** Cartões `[Contato] Nome — número` (e o rótulo antigo `[Contacto]`). Null se a mensagem tiver outro texto. */
export function contatosNaMensagem(corpo: string | null | undefined): ContatoCartao[] | null {
  const texto = (corpo || '').trim()
  if (!texto) return null
  const parsed: ContatoCartao[] = []
  for (const raw of texto.split('\n')) {
    const linha = raw.trim()
    if (!linha || LINHA_ASSINATURA.test(linha)) continue
    const match = linha.match(LINHA_CONTATO)
    if (!match) return null
    parsed.push({ nome: match[1].trim(), telefone: match[2] || null })
  }
  return parsed.length > 0 ? parsed : null
}
