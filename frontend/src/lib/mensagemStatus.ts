export type StatusEntregaMensagem = 'pendente' | 'enviada' | 'entregue' | 'lida' | 'erro'

export function mostrarStatusEntrega(
  direcao: string | undefined,
  status: StatusEntregaMensagem | null | undefined,
  opts?: { eventoSistema?: string | null },
): boolean {
  if (opts?.eventoSistema) return false
  if (direcao !== 'outbound') return false
  return Boolean(status)
}

export function formatarHoraMensagemCurta(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export function labelStatusEntrega(status: StatusEntregaMensagem): string {
  switch (status) {
    case 'pendente':
      return 'Enviando'
    case 'enviada':
      return 'Enviada'
    case 'entregue':
      return 'Entregue'
    case 'lida':
      return 'Lida'
    case 'erro':
      return 'Falha no envio'
    default:
      return ''
  }
}
