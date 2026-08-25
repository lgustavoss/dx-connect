/** Status da fila de sugestões / problemas no painel ops (#923). */

export const SAAS_SOLICITACAO_STATUS = [
  { value: 'aberta', label: 'Recebida' },
  { value: 'em_analise', label: 'Em análise' },
  { value: 'planejada', label: 'Planejada' },
  { value: 'em_desenvolvimento', label: 'Em desenvolvimento' },
  { value: 'concluida', label: 'Concluída' },
  { value: 'nao_sera_desenvolvida', label: 'Não será desenvolvida' },
] as const

export type SaasSolicitacaoStatus = (typeof SAAS_SOLICITACAO_STATUS)[number]['value']

/** Fases para filtro rápido (agrupa vários status). */
export const SAAS_SOLICITACAO_FASES = [
  {
    value: 'aguardando',
    label: 'Aguardando',
    hint: 'Recebida, em análise ou planejada',
  },
  {
    value: 'desenvolvimento',
    label: 'Em desenvolvimento',
    hint: 'Já em andamento',
  },
  {
    value: 'finalizadas',
    label: 'Finalizadas',
    hint: 'Concluída ou não será desenvolvida',
  },
] as const

export type SaasSolicitacaoFase = (typeof SAAS_SOLICITACAO_FASES)[number]['value']

const BADGE: Record<string, string> = {
  aberta:
    'bg-slate-100 text-slate-800 ring-slate-200/80 dark:bg-slate-800/70 dark:text-slate-100 dark:ring-slate-600/70',
  em_analise:
    'bg-sky-50 text-sky-900 ring-sky-200/80 dark:bg-sky-950/50 dark:text-sky-100 dark:ring-sky-800/50',
  planejada:
    'bg-violet-50 text-violet-900 ring-violet-200/80 dark:bg-violet-950/40 dark:text-violet-100 dark:ring-violet-800/50',
  em_desenvolvimento:
    'bg-cyan-50 text-cyan-900 ring-cyan-200/80 dark:bg-cyan-950/40 dark:text-cyan-100 dark:ring-cyan-800/50',
  concluida:
    'bg-emerald-50 text-emerald-900 ring-emerald-200/80 dark:bg-emerald-950/40 dark:text-emerald-100 dark:ring-emerald-800/50',
  nao_sera_desenvolvida:
    'bg-rose-50 text-rose-900 ring-rose-200/80 dark:bg-rose-950/40 dark:text-rose-100 dark:ring-rose-800/50',
}

export function rotuloStatusSolicitacao(value: string): string {
  return SAAS_SOLICITACAO_STATUS.find((s) => s.value === value)?.label ?? value
}

export function classesBadgeStatusSolicitacao(value: string): string {
  return (
    BADGE[value] ??
    'bg-slate-100 text-slate-800 ring-slate-200/80 dark:bg-slate-800/70 dark:text-slate-100 dark:ring-slate-600/70'
  )
}

/** Painel ops: “problema” do cliente = erro reportado. */
export function rotuloTipoSolicitacao(tipo: string): string {
  return tipo === 'problema' ? 'Erro' : 'Sugestão'
}

export function classesBadgeTipoSolicitacao(tipo: string): string {
  if (tipo === 'problema') {
    return 'bg-rose-50 text-rose-900 ring-rose-200/90 dark:bg-rose-950/45 dark:text-rose-100 dark:ring-rose-800/60'
  }
  return 'bg-sky-50 text-sky-900 ring-sky-200/90 dark:bg-sky-950/45 dark:text-sky-100 dark:ring-sky-800/60'
}

/** GitHub / issue #N não deve ir na mensagem visível ao cliente. */
export function mencionaTrabalhoInterno(texto: string): boolean {
  const t = texto.trim()
  if (!t) return false
  return /github\.com|\bgithub\b|\bissues?\s*#\s*\d+|\/issues\/\d+/i.test(t)
}
