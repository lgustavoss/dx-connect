import type { WhatsappChats } from '../../api/client'
import { rotuloDemanda, formatarHoraDemanda } from '../../lib/whatsappDemandaUtils'

const DESFECHO: Record<string, string> = {
  resolvido_sessao: 'Resolvido na sessão',
  escalado_ticket: 'Escalado para ticket',
}

type Props = {
  demanda: WhatsappChats.Demanda
}

export function WhatsappDemandaTimelineMarco({ demanda }: Props) {
  return (
    <div className="flex w-full justify-center py-2">
      <div
        className="max-w-md rounded-xl border border-violet-200 bg-violet-50/95 px-4 py-2 text-center text-xs shadow-sm dark:border-violet-900/50 dark:bg-violet-950/40"
        title={demanda.descricao_curta ?? undefined}
      >
        <p className="font-bold uppercase tracking-wide text-violet-800 dark:text-violet-200">
          Demanda registada
        </p>
        <p className="mt-0.5 font-medium text-violet-950 dark:text-violet-100">{rotuloDemanda(demanda)}</p>
        <p className="mt-0.5 text-[10px] text-violet-700/80 dark:text-violet-300/80">
          {DESFECHO[demanda.desfecho] ?? demanda.desfecho}
          {demanda.atendente_nome ? ` · ${demanda.atendente_nome}` : ''}
          {' · '}
          {formatarHoraDemanda(demanda.created_at)}
        </p>
        {demanda.descricao_curta && (
          <p className="mt-1 text-[11px] text-violet-800/90 dark:text-violet-200/90">{demanda.descricao_curta}</p>
        )}
      </div>
    </div>
  )
}
