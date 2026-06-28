import { useEffect, useState } from 'react'
import { tickets, type Tickets } from '../../api/client'
import { Card } from '../ui/Card'
import { SlaBadge } from './SlaBadge'
import { formatMinutosSla, textoCountdownSla, tooltipSlaMeta } from '../../lib/slaTicket'

export function TicketSlaCard({ ticketId, fechado }: { ticketId: number; fechado: boolean }) {
  const [sla, setSla] = useState<Tickets.TicketSla | null>(null)
  const [erro, setErro] = useState(false)

  useEffect(() => {
    let cancelled = false
    tickets
      .getSla(ticketId)
      .then((d) => {
        if (!cancelled) setSla(d)
      })
      .catch(() => {
        if (!cancelled) setErro(true)
      })
    return () => {
      cancelled = true
    }
  }, [ticketId])

  if (erro || !sla?.sla_policy_id) return null

  const comercial = sla.usa_horario_comercial
  const pior =
    sla.primeira_resposta.estado === 'violado' || sla.resolucao.estado === 'violado'
      ? 'violado'
      : sla.primeira_resposta.estado === 'em_risco' || sla.resolucao.estado === 'em_risco'
        ? 'em_risco'
        : sla.primeira_resposta.estado === 'cumprido' && sla.resolucao.estado === 'cumprido'
          ? 'cumprido'
          : 'dentro'

  return (
    <Card className="mb-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">SLA</h3>
        <SlaBadge estado={fechado && pior === 'dentro' ? 'cumprido' : pior} />
      </div>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {comercial ? 'Contagem em horário comercial' : 'Contagem contínua (24×7)'}
        {sla.pausado_agora ? ' · SLA pausado neste status' : ''}
        {sla.minutos_pausados > 0 && !sla.pausado_agora
          ? ` · ${sla.minutos_pausados} min já pausados`
          : ''}
      </p>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
        {(['primeira_resposta', 'resolucao'] as const).map((chave) => {
          const meta = sla[chave]
          const nome = chave === 'primeira_resposta' ? 'Primeira resposta' : 'Resolução'
          return (
            <div
              key={chave}
              className="rounded-lg border border-slate-200/80 bg-slate-50/80 px-3 py-2 dark:border-slate-800/70 dark:bg-slate-900/40"
              title={tooltipSlaMeta(nome, meta, comercial)}
            >
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {nome}
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100">
                {sla.pausado_agora && meta.estado !== 'cumprido' && meta.estado !== 'violado'
                  ? 'Pausado'
                  : textoCountdownSla(meta, comercial)}
              </dd>
              <dd className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Meta: {formatMinutosSla(meta.meta_minutos, comercial)}
              </dd>
            </div>
          )
        })}
      </dl>
    </Card>
  )
}
