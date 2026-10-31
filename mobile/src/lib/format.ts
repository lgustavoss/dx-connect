export function nomeDoChat(chat: {
  funcionario_nome?: string | null
  cliente_nome?: string | null
  wa_id?: string
}): string {
  return (chat.funcionario_nome || chat.cliente_nome || chat.wa_id || 'Contato').trim()
}

export function horaCurta(iso?: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const hoje = new Date()
  const mesmaData =
    d.getFullYear() === hoje.getFullYear() && d.getMonth() === hoje.getMonth() && d.getDate() === hoje.getDate()
  return mesmaData
    ? d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function rotuloEstado(estado: string): string {
  if (estado === 'aguardando_atendente') return 'Na fila'
  if (estado === 'em_atendimento') return 'Em atendimento'
  if (estado === 'encerrado') return 'Encerrado'
  return estado
}

export function iniciais(nome: string): string {
  const partes = nome.split(/\s+/).filter(Boolean)
  const a = partes[0]?.[0] || '?'
  const b = partes.length > 1 ? partes[partes.length - 1][0] : ''
  return (a + b).toUpperCase()
}

const ROTULO_SEM_LEGENDA =
  /^(?:\[\s*[^\]]+\s*\]:\s*)?\[(Imagem|Áudio|Audio|Vídeo|Video|Documento|Figurinha|Contacto|Contato|Localização)(\s+enviad[oa])?\]$/i

/** Legenda real sob a mídia; ignora placeholders tipo «[Imagem]». */
export function legendaMidiaVisivel(corpo: string | null | undefined): string | null {
  const t = (corpo || '').trim()
  if (!t || ROTULO_SEM_LEGENDA.test(t)) return null
  return t
}
