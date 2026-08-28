/** Primeira inbound não lida para o divisor visual (#951 / #S202608-0010). */
export type ChatUnreadCursor = {
  nao_lidas_count?: number
  last_seen_mensagem_id?: number | null
  last_seen_at?: string | null
  atendimento_inicio_at?: string | null
  created_at?: string | null
}

export type MensagemUnreadCursor = {
  id: number
  direcao: string
  evento_sistema?: string | null
  apagada?: boolean
  created_at?: string | null
}

export function primeiraInboundNaoLidaMsgId(
  msgs: MensagemUnreadCursor[],
  chat: ChatUnreadCursor,
): number | null {
  if ((chat.nao_lidas_count ?? 0) <= 0) return null

  const cursorId = chat.last_seen_mensagem_id
  if (cursorId != null) {
    const primeira = msgs.find(
      (m) =>
        m.direcao === 'inbound' &&
        !m.evento_sistema &&
        !m.apagada &&
        m.id > cursorId,
    )
    return primeira?.id ?? null
  }

  const eff = chat.last_seen_at || chat.atendimento_inicio_at || chat.created_at || null
  const effMs = eff ? new Date(eff).getTime() : 0
  const primeira = msgs.find(
    (m) =>
      m.direcao === 'inbound' &&
      !m.evento_sistema &&
      !m.apagada &&
      m.created_at &&
      new Date(m.created_at).getTime() > effMs,
  )
  return primeira?.id ?? null
}
