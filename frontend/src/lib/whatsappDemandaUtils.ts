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

/** Aviso ou encerramento automático por inatividade do cliente — demanda no modal é opcional. */
export function chatEncerramentoPorInatividade(msgs: WhatsappChats.Mensagem[]): boolean {
  return msgs.some(
    (m) =>
      m.evento_sistema === 'auto_encerrado_inatividade' || m.evento_sistema === 'auto_inativ_aviso',
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

export function demandasComMarcoMensagem(
  demandas: WhatsappChats.Demanda[],
  msgs: WhatsappChats.Mensagem[],
): WhatsappChats.Demanda[] {
  const idsComMarco = new Set<number>()
  for (const m of msgs) {
    if (m.evento_sistema === 'demanda_registrada' || m.evento_sistema === 'demanda_escalada') {
      const match = m.corpo?.match(/^\[demanda_id=(\d+)\]/)
      if (match) idsComMarco.add(Number(match[1]))
    }
  }
  return demandas.filter((d) => !idsComMarco.has(d.id))
}

export function textoMarcoDemanda(corpo: string | null | undefined): string {
  if (!corpo) return 'Demanda registada'
  return corpo.replace(/^\[demanda_id=\d+\]\s*/, '')
}

export function mergeTimelineChat(
  msgs: WhatsappChats.Mensagem[],
  demandas: WhatsappChats.Demanda[],
): TimelineItem[] {
  const items: TimelineItem[] = []
  const demandasMerge = demandasComMarcoMensagem(demandas, msgs)
  for (const m of mensagensVisiveisConversa(msgs)) {
    items.push({
      kind: 'mensagem',
      ts: m.created_at ? new Date(m.created_at).getTime() : 0,
      mensagem: m,
    })
  }
  for (const d of demandasMerge) {
    items.push({
      kind: 'demanda',
      ts: d.created_at ? new Date(d.created_at).getTime() : 0,
      demanda: d,
    })
  }
  return items.sort((a, b) => a.ts - b.ts || (a.kind === 'demanda' ? 1 : 0) - (b.kind === 'demanda' ? 1 : 0))
}
