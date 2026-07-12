import type { ChatInterno } from '../api/client'

export function ordenarMensagensChatInterno(mensagens: ChatInterno.Mensagem[]): ChatInterno.Mensagem[] {
  return [...mensagens].sort((a, b) => a.id - b.id)
}

export function mergeMensagensChatInterno(
  prev: ChatInterno.Mensagem[],
  incoming: ChatInterno.Mensagem[],
): ChatInterno.Mensagem[] {
  const byId = new Map(prev.map((m) => [m.id, m]))
  for (const m of incoming) {
    byId.set(m.id, m)
  }
  return ordenarMensagensChatInterno(Array.from(byId.values()))
}

export function prependMensagensChatInterno(
  prev: ChatInterno.Mensagem[],
  older: ChatInterno.Mensagem[],
): ChatInterno.Mensagem[] {
  return mergeMensagensChatInterno(older, prev)
}
