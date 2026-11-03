/**
 * Timeline 360 e saúde do cliente da carteira (#912 / #914).
 *
 * Módulo novo, isolado de `client.ts`: o Lead integra as rotas depois do merge.
 */

import { api, type Paginated } from './client'

export type CategoriaEvento = 'crm' | 'implantacao' | 'suporte'

export type SaudeStatus = 'saudavel' | 'atencao' | 'risco'

/** `info` = sinal informativo (não altera o status, só dá contexto). */
export type NivelSinal = SaudeStatus | 'info'

export type EventoTimeline = {
  id: string
  em: string
  categoria: CategoriaEvento
  tipo: string
  titulo: string
  detalhe: string | null
  ref_tipo: 'crm_negociacao' | 'comercial_proposta' | 'comercial_contrato' | 'ticket' | null
  ref_id: number | null
}

export type SinalSaude = {
  codigo: string
  rotulo: string
  valor: string
  nivel: NivelSinal
  explicacao: string | null
}

export type SaudeEmpresa = {
  empresa_id: number
  empresa_nome: string
  rede_id: number | null
  rede_nome: string | null
  ativo: boolean
  status: SaudeStatus
  motivos: string[]
  sinais: SinalSaude[]
  ultimo_evento_em: string | null
  dias_sem_movimento: number | null
  atualizado_em: string
}

export const CATEGORIAS_TIMELINE: ReadonlyArray<{ value: CategoriaEvento; label: string }> = [
  { value: 'crm', label: 'CRM' },
  { value: 'implantacao', label: 'Implantação' },
  { value: 'suporte', label: 'Suporte' },
]

export const CATEGORIA_LABEL: Record<CategoriaEvento, string> = {
  crm: 'CRM',
  implantacao: 'Implantação',
  suporte: 'Suporte',
}

export const SAUDE_STATUS_OPCOES: ReadonlyArray<{ value: SaudeStatus; label: string }> = [
  { value: 'saudavel', label: 'Saudável' },
  { value: 'atencao', label: 'Atenção' },
  { value: 'risco', label: 'Risco' },
]

export const SAUDE_LABEL: Record<SaudeStatus, string> = {
  saudavel: 'Saudável',
  atencao: 'Atenção',
  risco: 'Risco',
}

/** Badge do status de saúde — mesmas cores em carteira e timeline. */
export const SAUDE_BADGE_CLASS: Record<SaudeStatus, string> = {
  saudavel:
    'bg-emerald-100 text-emerald-800 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-900/60',
  atencao:
    'bg-amber-100 text-amber-900 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900/60',
  risco:
    'bg-red-100 text-red-800 ring-red-200 dark:bg-red-950/40 dark:text-red-200 dark:ring-red-900/60',
}

export const CATEGORIA_BADGE_CLASS: Record<CategoriaEvento, string> = {
  crm: 'bg-blue-100 text-blue-800 ring-blue-200 dark:bg-blue-950/40 dark:text-blue-200 dark:ring-blue-900/60',
  implantacao:
    'bg-violet-100 text-violet-800 ring-violet-200 dark:bg-violet-950/40 dark:text-violet-200 dark:ring-violet-900/60',
  suporte:
    'bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700',
}

export type TimelineParams = {
  empresaId: number
  categorias?: CategoriaEvento[]
  /** Data (YYYY-MM-DD) inclusiva; enviada como início do dia. */
  de?: string
  /** Data (YYYY-MM-DD) inclusiva; enviada como fim do dia. */
  ate?: string
  ordem?: 'asc' | 'desc'
  offset?: number
  limit?: number
}

export type CarteiraParams = {
  busca?: string
  status?: SaudeStatus
  incluirInativos?: boolean
  offset?: number
  limit?: number
}

function dataInicioIso(data: string | undefined): string | undefined {
  return data ? `${data}T00:00:00` : undefined
}

function dataFimIso(data: string | undefined): string | undefined {
  return data ? `${data}T23:59:59` : undefined
}

function comParams(path: string, params: Record<string, string | number | boolean | undefined>): string {
  const q = new URLSearchParams()
  for (const [chave, valor] of Object.entries(params)) {
    if (valor !== undefined && valor !== '') q.set(chave, String(valor))
  }
  const query = q.toString()
  return query ? `${path}?${query}` : path
}

export const operacaoTimeline = {
  timeline: ({ empresaId, categorias, de, ate, ordem, offset, limit }: TimelineParams) => {
    const q = new URLSearchParams()
    q.set('empresa_id', String(empresaId))
    for (const categoria of categorias ?? []) q.append('categorias', categoria)
    const inicio = dataInicioIso(de)
    const fim = dataFimIso(ate)
    if (inicio) q.set('de', inicio)
    if (fim) q.set('ate', fim)
    if (ordem) q.set('ordem', ordem)
    if (offset !== undefined) q.set('offset', String(offset))
    if (limit !== undefined) q.set('limit', String(limit))
    return api<Paginated<EventoTimeline>>(`/operacao/timeline?${q.toString()}`)
  },

  carteira: ({ busca, status, incluirInativos, offset, limit }: CarteiraParams = {}) =>
    api<Paginated<SaudeEmpresa>>(
      comParams('/operacao/carteira', {
        busca: busca?.trim() || undefined,
        status,
        incluir_inativos: incluirInativos ? 'true' : undefined,
        offset: offset ?? 0,
        limit: limit ?? 20,
      }),
    ),

  saude: (empresaId: number) => api<SaudeEmpresa>(`/operacao/carteira/${empresaId}`),
}
