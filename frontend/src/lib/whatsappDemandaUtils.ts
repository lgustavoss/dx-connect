import type { WhatsappChats } from '../api/client'

export type DemandaPosEncerramento = {
  ultimaDemanda: WhatsappChats.Demanda
  mensagensApos: number
  ultimaMensagemAt: string | null
}

export function formatarHoraDemanda(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function rotuloDemanda(d: WhatsappChats.Demanda): string {
  return d.motivo_nome ? `${d.natureza_nome} · ${d.motivo_nome}` : d.natureza_nome ?? 'Demanda'
}

/** Mensagens visíveis na conversa (exclui eventos ocultos de avaliação). */
export function mensagensVisiveisConversa(msgs: WhatsappChats.Mensagem[]): WhatsappChats.Mensagem[] {
  return msgs.filter(
    (m) =>
      m.evento_sistema !== 'auto_avaliacao_solicitacao' &&
      m.evento_sistema !== 'avaliacao_cliente_nota',
  )
}

export function analisarDemandaPosRegistro(
  demandas: WhatsappChats.Demanda[],
  msgs: WhatsappChats.Mensagem[],
): DemandaPosEncerramento | null {
  const editaveis = demandas.filter((d) => d.desfecho === 'resolvido_sessao')
  if (editaveis.length === 0) return null
  const ultimaDemanda = editaveis.reduce((a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0
    return tb >= ta ? b : a
  })
  const tDemanda = ultimaDemanda.created_at ? new Date(ultimaDemanda.created_at).getTime() : 0
  const visiveis = mensagensVisiveisConversa(msgs)
  const apos = visiveis.filter((m) => {
    const t = m.created_at ? new Date(m.created_at).getTime() : 0
    return t > tDemanda
  })
  if (apos.length === 0) return null
  const ultima = apos.reduce((a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0
    return tb >= ta ? b : a
  })
  return {
    ultimaDemanda,
    mensagensApos: apos.length,
    ultimaMensagemAt: ultima.created_at ?? null,
  }
}

export type TimelineItem =
  | { kind: 'mensagem'; ts: number; mensagem: WhatsappChats.Mensagem }
  | { kind: 'demanda'; ts: number; demanda: WhatsappChats.Demanda }

export function mergeTimelineChat(
  msgs: WhatsappChats.Mensagem[],
  demandas: WhatsappChats.Demanda[],
): TimelineItem[] {
  const items: TimelineItem[] = []
  for (const m of mensagensVisiveisConversa(msgs)) {
    items.push({
      kind: 'mensagem',
      ts: m.created_at ? new Date(m.created_at).getTime() : 0,
      mensagem: m,
    })
  }
  for (const d of demandas) {
    items.push({
      kind: 'demanda',
      ts: d.created_at ? new Date(d.created_at).getTime() : 0,
      demanda: d,
    })
  }
  return items.sort((a, b) => a.ts - b.ts || (a.kind === 'demanda' ? 1 : 0) - (b.kind === 'demanda' ? 1 : 0))
}
