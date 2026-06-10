import type { WhatsappChats } from '../api/client'

type ChatResumo = Pick<
  WhatsappChats.Chat,
  'estado' | 'atendente_id' | 'atendente_nome' | 'setor_nome'
>

export function rotuloEstadoChat(estado: string): string {
  if (estado === 'em_atendimento') return 'Em atendimento'
  if (estado === 'aguardando_atendente') return 'Aguardando atendimento'
  if (estado === 'aguardando_avaliacao') return 'Aguardando avaliação'
  if (estado === 'encerrado') return 'Encerrado'
  return estado.replace(/_/g, ' ')
}

export function rotuloResponsavelChat(chat: ChatResumo, usuarioId?: number | null): string {
  if (chat.estado === 'aguardando_atendente') {
    return chat.setor_nome ? `Fila • ${chat.setor_nome}` : 'Na fila'
  }
  if (chat.estado === 'encerrado') {
    return chat.atendente_nome ? `Encerrado por ${chat.atendente_nome}` : 'Encerrado'
  }
  if (chat.estado === 'aguardando_avaliacao') {
    return chat.atendente_nome ? `Aguardando avaliação • ${chat.atendente_nome}` : 'Aguardando avaliação'
  }
  if (!chat.atendente_id) {
    return chat.setor_nome ? `Sem responsável • ${chat.setor_nome}` : 'Sem responsável'
  }
  if (usuarioId != null && chat.atendente_id === usuarioId) return 'Você'
  return chat.atendente_nome || `Atendente #${chat.atendente_id}`
}

export type AvaliacaoChatResolvida =
  | { kind: 'nota'; nota: number }
  | { kind: 'sem_avaliacao' }
  | { kind: 'nao_solicitada' }

export function resolveAvaliacaoChat(chat: {
  avaliacao_nota?: number | null
  avaliacao_solicitada?: boolean
  sem_avaliacao?: boolean
  nota?: number | null
}): AvaliacaoChatResolvida {
  const nota = chat.avaliacao_nota ?? chat.nota
  if (nota != null) return { kind: 'nota', nota }
  if (chat.sem_avaliacao || (chat.avaliacao_solicitada && nota == null)) return { kind: 'sem_avaliacao' }
  return { kind: 'nao_solicitada' }
}

export function rotuloAvaliacaoChat(chat: {
  avaliacao_nota?: number | null
  avaliacao_solicitada?: boolean
  sem_avaliacao?: boolean
  nota?: number | null
}): string {
  const resolvida = resolveAvaliacaoChat(chat)
  if (resolvida.kind === 'nota') return `${resolvida.nota}/5`
  if (resolvida.kind === 'sem_avaliacao') return 'Sem avaliação'
  return '—'
}

export function mensagemTransferenciaSucesso(chat: ChatResumo): string {
  if (chat.estado === 'aguardando_atendente') {
    return chat.setor_nome
      ? `Chat enviado para a fila do setor ${chat.setor_nome}.`
      : 'Chat enviado para a fila.'
  }
  if (chat.atendente_nome) {
    const setor = chat.setor_nome ? ` (${chat.setor_nome})` : ''
    return `Chat transferido para ${chat.atendente_nome}${setor}.`
  }
  return 'Chat transferido.'
}
