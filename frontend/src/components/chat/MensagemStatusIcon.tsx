import type { StatusEntregaMensagem } from '../../lib/mensagemStatus'
import { labelStatusEntrega } from '../../lib/mensagemStatus'

type Props = {
  status: StatusEntregaMensagem
  /** Bolha clara (cyan) ou escura */
  variant?: 'claro' | 'escuro'
  className?: string
}

function corIcone(status: StatusEntregaMensagem, variant: 'claro' | 'escuro'): string {
  if (status === 'lida') {
    return variant === 'claro' ? 'text-cyan-100' : 'text-cyan-500 dark:text-cyan-400'
  }
  if (status === 'erro') {
    return variant === 'claro' ? 'text-rose-200' : 'text-rose-500'
  }
  return variant === 'claro' ? 'text-cyan-100/90' : 'text-slate-400'
}

function IconePendente({ className }: { className: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className} aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  )
}

function IconeUmTick({ className }: { className: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function IconeDoisTicks({ className }: { className: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>
      <path d="M18 6 7 17l-2-2" />
      <path d="m22 6-9 9-2-2" />
    </svg>
  )
}

function IconeErro({ className }: { className: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className} aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </svg>
  )
}

export function MensagemStatusIcon({ status, variant = 'escuro', className = '' }: Props) {
  const cor = corIcone(status, variant)
  const titulo = labelStatusEntrega(status)

  let icon
  if (status === 'pendente') icon = <IconePendente className={cor} />
  else if (status === 'enviada') icon = <IconeUmTick className={cor} />
  else if (status === 'entregue' || status === 'lida') icon = <IconeDoisTicks className={cor} />
  else if (status === 'erro') icon = <IconeErro className={cor} />
  else icon = null

  if (!icon) return null

  return (
    <span className={`inline-flex shrink-0 items-center ${className}`} title={titulo} aria-label={titulo}>
      {icon}
    </span>
  )
}
