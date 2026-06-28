import { RudderMark } from '../../brand'

type Props = {
  label?: string
  /** Ocupa a tela inteira (ex.: sessão / auth). */
  fullscreen?: boolean
  className?: string
}

export function PageLoading({
  label = 'Carregando…',
  fullscreen = false,
  className = '',
}: Props) {
  const shell = fullscreen
    ? 'h-dvh max-h-dvh bg-gradient-to-b from-slate-50 to-slate-100/90 dark:from-slate-950 dark:to-slate-900/95'
    : 'min-h-[40vh]'

  return (
    <div
      className={`flex flex-col items-center justify-center px-6 ${shell} ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={label}
    >
      <div className="relative flex size-11 items-center justify-center">
        <span
          className="absolute inset-0 rounded-full border border-cyan-200/80 dark:border-cyan-900/60"
          aria-hidden
        />
        <span
          className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-cyan-600 dark:border-t-cyan-400"
          aria-hidden
        />
        <RudderMark className="relative size-[22px]" title="" />
      </div>
      <p className="mt-4 text-sm font-medium tracking-tight text-slate-700 dark:text-slate-200">{label}</p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Só um instante</p>
    </div>
  )
}
