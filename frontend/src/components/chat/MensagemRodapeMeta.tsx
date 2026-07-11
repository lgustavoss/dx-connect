import { MensagemStatusIcon } from './MensagemStatusIcon'
import { formatarHoraMensagemCurta, mostrarStatusEntrega, type StatusEntregaMensagem } from '../../lib/mensagemStatus'

type Props = {
  hora: string | null | undefined
  status?: StatusEntregaMensagem | null
  direcao?: string
  eventoSistema?: string | null
  variant?: 'claro' | 'escuro'
  prefixo?: string
  className?: string
}

export function MensagemRodapeMeta({
  hora,
  status,
  direcao,
  eventoSistema,
  variant = 'escuro',
  prefixo,
  className = '',
}: Props) {
  const horaFmt = formatarHoraMensagemCurta(hora)
  const exibirStatus = mostrarStatusEntrega(direcao, status, { eventoSistema })

  if (!horaFmt && !exibirStatus && !prefixo) return null

  return (
    <div className={`mt-1 flex items-center justify-end gap-1 ${className}`}>
      {prefixo ? <span className="truncate text-[10px] opacity-80">{prefixo}</span> : null}
      {horaFmt ? (
        <span className={`text-[10px] tabular-nums ${variant === 'claro' ? 'text-cyan-100/90' : 'text-slate-400'}`}>
          {horaFmt}
        </span>
      ) : null}
      {exibirStatus && status ? <MensagemStatusIcon status={status} variant={variant} /> : null}
    </div>
  )
}
