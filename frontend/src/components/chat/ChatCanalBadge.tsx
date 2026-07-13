import type { ChatHubCanal } from '../../lib/chatHubLista'

type Props = {
  canal: ChatHubCanal
  className?: string
}

export function ChatCanalBadge({ canal, className = '' }: Props) {
  const isPortal = canal === 'portal'
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
        isPortal
          ? 'bg-violet-100 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300'
          : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300'
      } ${className}`}
    >
      {isPortal ? 'Portal' : 'WhatsApp'}
    </span>
  )
}
