import type { SolicitacoesMelhoria } from '../../api/client'
import { classesBadgeStatusSolicitacao } from '../../lib/saasSolicitacoes'

function fmt(dt: string): string {
  try {
    return new Date(dt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return dt
  }
}

type TimelineEntry =
  | { kind: 'historico'; id: number; created_at: string; data: SolicitacoesMelhoria.Historico }
  | { kind: 'comentario'; id: number; created_at: string; data: SolicitacoesMelhoria.Comentario }

function montarTimeline(
  historico: SolicitacoesMelhoria.Historico[],
  comentarios: SolicitacoesMelhoria.Comentario[],
): TimelineEntry[] {
  const items: TimelineEntry[] = [
    ...historico.map((h) => ({ kind: 'historico' as const, id: h.id, created_at: h.created_at, data: h })),
    ...comentarios.map((c) => ({ kind: 'comentario' as const, id: c.id, created_at: c.created_at, data: c })),
  ]
  return items.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
}

type Props = {
  historico: SolicitacoesMelhoria.Historico[]
  comentarios: SolicitacoesMelhoria.Comentario[]
}

/** Linha do tempo vertical — status + comentários em ordem cronológica. */
export function SolicitacoesMelhoriaTimeline({ historico, comentarios }: Props) {
  const items = montarTimeline(historico, comentarios)

  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Ainda não há atualizações neste pedido.</p>
  }

  return (
    <ol className="relative border-l-2 border-slate-200 pl-6 dark:border-slate-700">
      {items.map((item) => {
        const isComentario = item.kind === 'comentario'
        const dotClass = isComentario
          ? 'bg-cyan-500 ring-cyan-100 dark:ring-cyan-950/60'
          : 'bg-slate-400 ring-slate-100 dark:bg-slate-500 dark:ring-slate-900/80'

        return (
          <li key={`${item.kind}-${item.id}`} className="relative pb-6 last:pb-0">
            <span
              className={`absolute -left-[calc(0.75rem+1px)] top-1.5 size-3 rounded-full ring-4 ${dotClass}`}
              aria-hidden
            />
            {item.kind === 'historico' ? (
              <div className="rounded-lg border border-slate-100 bg-slate-50/80 p-3 text-sm dark:border-slate-800 dark:bg-slate-800/40">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeStatusSolicitacao(item.data.status_novo)}`}
                  >
                    {item.data.status_novo_rotulo}
                  </span>
                  <span className="text-xs text-slate-400">{fmt(item.created_at)}</span>
                </div>
                {item.data.mensagem_publica ? (
                  <p className="mt-2 whitespace-pre-wrap text-slate-600 dark:text-slate-300">
                    {item.data.mensagem_publica}
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="rounded-lg border border-cyan-100 bg-white p-3 text-sm shadow-sm dark:border-cyan-900/40 dark:bg-slate-900/60">
                <p className="text-xs font-medium text-slate-500">
                  {item.data.autor_nome || 'Equipe'} · {fmt(item.created_at)}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-slate-700 dark:text-slate-200">{item.data.corpo}</p>
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
