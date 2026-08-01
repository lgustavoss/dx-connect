import {
  setFilaAguardandoMuted,
  useFilaAguardandoMuted,
} from '../../hooks/useAlertaFilaSemResponsavel'

type Props = {
  className?: string
  /** Compacto para caber no header mobile / tabs */
  size?: 'sm' | 'md'
}

export function ChatFilaSomToggle({ className = '', size = 'sm' }: Props) {
  const muted = useFilaAguardandoMuted()
  const dim = size === 'md' ? 'h-8 w-8' : 'h-7 w-7'
  const icon = size === 'md' ? 18 : 16

  return (
    <button
      type="button"
      aria-pressed={muted}
      aria-label={
        muted
          ? 'Ativar alerta sonoro da fila Aguardando'
          : 'Silenciar alerta sonoro da fila Aguardando'
      }
      title={muted ? 'Alerta da fila silenciado — clique para ativar' : 'Silenciar alerta da fila'}
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        setFilaAguardandoMuted(!muted)
      }}
      className={`inline-flex ${dim} shrink-0 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100 ${
        muted ? 'text-amber-600 dark:text-amber-400' : ''
      } ${className}`}
    >
      {muted ? (
        <svg xmlns="http://www.w3.org/2000/svg" width={icon} height={icon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M11 5 6 9H2v6h4l5 4V5z" />
          <line x1="23" y1="9" x2="17" y2="15" />
          <line x1="17" y1="9" x2="23" y2="15" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" width={icon} height={icon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
        </svg>
      )}
    </button>
  )
}
