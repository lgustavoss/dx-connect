import { classeBadgeSla, rotuloSlaEstado } from '../../lib/slaTicket'

export function SlaBadge({
  estado,
  className = '',
}: {
  estado: string | null | undefined
  className?: string
}) {
  const rotulo = rotuloSlaEstado(estado)
  if (!rotulo) return null
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${classeBadgeSla(estado)} ${className}`}
      title={rotulo}
    >
      {rotulo}
    </span>
  )
}
