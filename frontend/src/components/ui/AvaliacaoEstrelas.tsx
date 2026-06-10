import { resolveAvaliacaoChat } from '../../lib/whatsappChatMeta'

type AvaliacaoChat = Parameters<typeof resolveAvaliacaoChat>[0]

type AvaliacaoEstrelasProps = {
  chat: AvaliacaoChat
  size?: 'sm' | 'md'
  className?: string
}

const STAR_PATH =
  'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z'

function Estrela({ preenchida, size }: { preenchida: boolean; size: 'sm' | 'md' }) {
  const dim = size === 'sm' ? 14 : 18
  return (
    <svg
      width={dim}
      height={dim}
      viewBox="0 0 24 24"
      aria-hidden
      className={preenchida ? 'text-amber-400' : 'text-slate-300 dark:text-slate-600'}
    >
      {preenchida ? (
        <path fill="currentColor" d={STAR_PATH} />
      ) : (
        <path
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          strokeLinejoin="round"
          d={STAR_PATH}
        />
      )}
    </svg>
  )
}

export function AvaliacaoEstrelas({ chat, size = 'sm', className = '' }: AvaliacaoEstrelasProps) {
  const resolvida = resolveAvaliacaoChat(chat)

  if (resolvida.kind === 'sem_avaliacao') {
    return (
      <span className={`text-xs font-medium text-slate-500 dark:text-slate-400 ${className}`}>
        Sem avaliação
      </span>
    )
  }

  if (resolvida.kind === 'nao_solicitada') {
    return (
      <span className={`text-xs font-medium text-slate-400 dark:text-slate-500 ${className}`}>—</span>
    )
  }

  const { nota } = resolvida

  return (
    <span
      className={`inline-flex items-center gap-0.5 ${className}`}
      title={`${nota} de 5 estrelas`}
      aria-label={`Avaliação: ${nota} de 5 estrelas`}
    >
      {Array.from({ length: 5 }, (_, i) => (
        <Estrela key={i} preenchida={i < nota} size={size} />
      ))}
    </span>
  )
}
