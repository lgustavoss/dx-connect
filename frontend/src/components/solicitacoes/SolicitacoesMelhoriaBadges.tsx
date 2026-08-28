import {
  classesBadgeStatusSolicitacao,
  classesBadgeTipoSolicitacao,
  rotuloStatusSolicitacao,
  rotuloTipoSolicitacao,
} from '../../lib/saasSolicitacoes'

type Props = {
  tipo: string
  status: string
  statusRotulo?: string
}

export function SolicitacoesMelhoriaBadges({ tipo, status, statusRotulo }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeTipoSolicitacao(tipo)}`}
      >
        {rotuloTipoSolicitacao(tipo)}
      </span>
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeStatusSolicitacao(status)}`}
      >
        {statusRotulo || rotuloStatusSolicitacao(status)}
      </span>
    </div>
  )
}
