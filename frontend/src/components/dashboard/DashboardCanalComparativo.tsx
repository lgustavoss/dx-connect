import { Link } from 'react-router-dom'
import { Card } from '../ui/Card'
import type { Dashboard } from '../../api/client'

type Props = {
  snapshot: Dashboard.SnapshotCanais
}

function ComparativoItem({
  label,
  value,
  href,
  hrefLabel,
}: {
  label: string
  value: number
  href: string
  hrefLabel: string
}) {
  return (
    <div className="flex min-w-[9rem] flex-1 flex-col gap-1 rounded-lg border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900/40">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
      <Link to={href} className="text-xs font-medium text-cyan-700 hover:text-cyan-800 dark:text-cyan-400">
        {hrefLabel} →
      </Link>
    </div>
  )
}

/** Comparativo rápido entre filas de tickets e WhatsApp (situação atual). */
export function DashboardCanalComparativo({ snapshot }: Props) {
  return (
    <Card
      title="Comparativo entre canais"
      description="Situação atual — use para equilibrar atendimento entre tickets e WhatsApp"
      className="mb-6"
    >
      <div className="flex flex-wrap gap-3">
        <ComparativoItem
          label="Tickets abertos"
          value={snapshot.tickets_abertos}
          href="/tickets?situacao=abertos"
          hrefLabel="Ver tickets"
        />
        <ComparativoItem
          label="Tickets na fila"
          value={snapshot.tickets_sem_responsavel}
          href="/tickets?sem_responsavel=1"
          hrefLabel="Ver fila"
        />
        <ComparativoItem
          label="WhatsApp aguardando"
          value={snapshot.chats_aguardando}
          href="/whatsapp/atendendo"
          hrefLabel="Ir para fila"
        />
        <ComparativoItem
          label="WhatsApp em atendimento"
          value={snapshot.chats_em_atendimento}
          href="/whatsapp/atendendo"
          hrefLabel="Ver central"
        />
      </div>
    </Card>
  )
}

export function snapshotFromGeral(geral: Dashboard.GeralResponse): Dashboard.SnapshotCanais {
  return {
    tickets_abertos: geral.tickets_abertos,
    tickets_sem_responsavel: geral.tickets_sem_responsavel,
    chats_aguardando: geral.chats_aguardando_atendente,
    chats_em_atendimento: geral.chats_em_atendimento,
  }
}
