import { PAGE_CONTAINER_CLASS } from './PageContainer'
import { VoltarButton } from './VoltarButton'

type Props = {
  titulo: string
  detalhe?: string
  onVoltar: () => void
  voltarLabel?: string
  className?: string
}

export function CarregamentoFalhou({
  titulo,
  detalhe,
  onVoltar,
  voltarLabel = 'Voltar',
  className = PAGE_CONTAINER_CLASS,
}: Props) {
  return (
    <div className={className}>
      <p className="text-slate-800 dark:text-slate-100">{titulo}</p>
      {detalhe ? <p className="text-sm text-slate-600 dark:text-slate-400">{detalhe}</p> : null}
      <div className="mt-3">
        <VoltarButton onClick={onVoltar} label={voltarLabel} />
      </div>
    </div>
  )
}
