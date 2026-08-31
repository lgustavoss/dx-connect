import { Link } from 'react-router-dom'
import type { Tickets } from '../api/client'
import { exibirProtocolo } from '../lib/exibirProtocolo'
import { marcarTicketAtivo, TICKETS_PATH } from '../lib/ticketAtivo'
import { Button } from './ui/Button'
import { IconEye } from './ui/IconEye'

export type TicketsTabelaContextoProps = {
  items: Tickets.Ticket[]
  loading: boolean
  /** Ex.: tickets da rede (uma linha por empresa). */
  showEmpresaColumn?: boolean
  emptyMessage?: string
}

export function TicketsTabelaContexto({
  items,
  loading,
  showEmpresaColumn = false,
  emptyMessage = 'Nenhum ticket encontrado.',
}: TicketsTabelaContextoProps) {
  if (loading && items.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Carregando tickets...</p>
  }
  if (items.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">{emptyMessage}</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
            <th className="px-4 py-3 sm:px-6">Protocolo</th>
            {showEmpresaColumn ? <th className="px-4 py-3 sm:px-6">Empresa</th> : null}
            <th className="px-4 py-3 sm:px-6">Assunto</th>
            <th className="px-4 py-3 sm:px-6">Status</th>
            <th className="px-4 py-3 sm:px-6">Responsável</th>
            <th className="w-px px-4 py-3 text-right sm:px-6">
              <span className="sr-only">Abrir</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {items.map((t) => (
            <tr
              key={t.id}
              className="transition-colors hover:bg-slate-50/80 focus-within:bg-slate-50/80 dark:hover:bg-white/5 dark:focus-within:bg-slate-800/50"
            >
              <td
                className="max-w-[11rem] truncate px-4 py-3 font-mono text-xs text-slate-800 dark:text-slate-100 sm:px-6"
                title={exibirProtocolo(t.protocolo)}
              >
                {exibirProtocolo(t.protocolo)}
              </td>
              {showEmpresaColumn ? (
                <td
                  className="max-w-[11rem] truncate px-4 py-3 text-slate-700 dark:text-slate-200 sm:px-6"
                  title={t.empresa_nome ?? undefined}
                >
                  {t.empresa_nome ??
                    (t.empresa_nome ?? (t.empresa_id != null ? `#${t.empresa_id}` : '—'))}
                </td>
              ) : null}
              <td
                className="max-w-[14rem] truncate px-4 py-3 text-slate-700 dark:text-slate-200 sm:px-6"
                title={t.assunto}
              >
                {t.assunto}
              </td>
              <td className="px-4 py-3 sm:px-6">
                <span className="inline-flex flex-col gap-0.5">
                  <span className="text-slate-700 dark:text-slate-200">{t.status_nome ?? '—'}</span>
                  {t.fechado_em ? (
                    <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Fechado</span>
                  ) : (
                    <span className="text-xs font-medium text-amber-600 dark:text-amber-400">Em aberto</span>
                  )}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-300 sm:px-6">
                {t.atendente_nome ?? '—'}
              </td>
              <td className="px-4 py-3 text-right sm:px-6">
                <Link
                  to={TICKETS_PATH}
                  onClick={() => marcarTicketAtivo(t.id)}
                  aria-label={`Ver ticket ${exibirProtocolo(t.protocolo)}`}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    className="inline-flex size-9 items-center justify-center p-0"
                  >
                    <IconEye className="size-5 shrink-0" ariaHidden={false} />
                  </Button>
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
