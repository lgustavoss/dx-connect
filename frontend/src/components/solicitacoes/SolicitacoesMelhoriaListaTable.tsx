import { useNavigate } from 'react-router-dom'
import type { SolicitacoesMelhoria } from '../../api/client'
import {
  classesBadgeStatusSolicitacao,
  classesBadgeTipoSolicitacao,
  rotuloStatusSolicitacao,
  rotuloTipoSolicitacao,
} from '../../lib/saasSolicitacoes'

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

type Props = {
  items: SolicitacoesMelhoria.ListaItem[]
  /** Rota do detalhe, ex.: `/minhas-solicitacoes/${id}` */
  itemPath: (id: number) => string
}

/** Tabela de solicitações do cliente — mesma linguagem visual do painel admin SaaS. */
export function SolicitacoesMelhoriaListaTable({ items, itemPath }: Props) {
  const navigate = useNavigate()

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
            <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Tipo</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Protocolo</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Título</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Status</th>
            <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Quando</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {items.map((item) => (
            <tr
              key={item.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(itemPath(item.id))}
              onKeyDown={(ev) => {
                if (ev.key === 'Enter' || ev.key === ' ') {
                  ev.preventDefault()
                  navigate(itemPath(item.id))
                }
              }}
              className={`cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/5 ${
                item.tipo === 'problema'
                  ? 'border-l-2 border-l-rose-400/80'
                  : 'border-l-2 border-l-sky-400/60'
              }`}
            >
              <td className="px-4 py-3 sm:px-6">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeTipoSolicitacao(item.tipo)}`}
                >
                  {rotuloTipoSolicitacao(item.tipo)}
                </span>
              </td>
              <td className="px-4 py-3 font-mono text-sm text-cyan-800 dark:text-cyan-300 sm:px-6">
                {item.protocolo || '—'}
              </td>
              <td className="px-4 py-3 sm:px-6">
                <p className="font-medium text-slate-800 dark:text-slate-100">{item.titulo}</p>
                {item.versao_alvo_rotulo ? (
                  <p className="mt-0.5 text-xs text-emerald-700 dark:text-emerald-300">{item.versao_alvo_rotulo}</p>
                ) : null}
              </td>
              <td className="px-4 py-3 sm:px-6">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeStatusSolicitacao(item.status)}`}
                >
                  {item.status_rotulo || rotuloStatusSolicitacao(item.status)}
                </span>
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-500 sm:px-6">{formatWhen(item.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
