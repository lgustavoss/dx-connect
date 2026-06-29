import type { WhatsappChats } from '../api/client'

/** Campos de vínculo com contato/empresa — preservados se payload SSE/poll vier desatualizado. */
const CAMPOS_VINCULO: (keyof WhatsappChats.Chat)[] = [
  'funcionario_rede_id',
  'funcionario_nome',
  'funcionario_email',
  'funcionario_tipo',
  'empresa_id',
  'empresa_nome',
]

function copiarCamposVinculo(origem: WhatsappChats.Chat, destino: WhatsappChats.Chat): WhatsappChats.Chat {
  const merged = { ...destino }
  for (const k of CAMPOS_VINCULO) {
    ;(merged as Record<string, unknown>)[k] = origem[k]
  }
  return merged
}

/**
 * Mescla atualizações de chat sem perder vínculo recém-gravado quando SSE/polling
 * ainda traz snapshot antigo (#472).
 */
export function mergeWhatsappChat(
  prev: WhatsappChats.Chat | null | undefined,
  next: WhatsappChats.Chat,
): WhatsappChats.Chat {
  if (!prev || prev.id !== next.id) return next
  const merged: WhatsappChats.Chat = { ...prev, ...next }
  if (prev.funcionario_rede_id && !next.funcionario_rede_id) {
    return copiarCamposVinculo(prev, merged)
  }
  return merged
}

export function patchWhatsappChatLista(
  lista: WhatsappChats.Chat[],
  atualizado: WhatsappChats.Chat,
): WhatsappChats.Chat[] {
  const idx = lista.findIndex((c) => c.id === atualizado.id)
  if (idx < 0) return lista
  const next = [...lista]
  next[idx] = mergeWhatsappChat(lista[idx], atualizado)
  return next
}

/** Substitui o chat na lista (resposta autoritativa de mutação — vincular/desvincular). */
export function replaceWhatsappChatLista(
  lista: WhatsappChats.Chat[],
  atualizado: WhatsappChats.Chat,
): WhatsappChats.Chat[] {
  const idx = lista.findIndex((c) => c.id === atualizado.id)
  if (idx < 0) return lista
  const next = [...lista]
  next[idx] = atualizado
  return next
}
