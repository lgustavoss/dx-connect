import type { WhatsappChats } from '../api/client'

/** Remove duplicatas ao recarregar a conversa (id / wa_message_id). */
export function whatsappMensagensUnicas(msgs: WhatsappChats.Mensagem[]): WhatsappChats.Mensagem[] {
  const seenId = new Set<number>()
  const seenWa = new Set<string>()
  const out: WhatsappChats.Mensagem[] = []
  for (const m of msgs) {
    if (seenId.has(m.id)) continue
    if (m.wa_message_id) {
      if (seenWa.has(m.wa_message_id)) continue
      seenWa.add(m.wa_message_id)
    }
    seenId.add(m.id)
    out.push(m)
  }
  return out
}
