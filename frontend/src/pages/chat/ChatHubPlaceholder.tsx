type Props = {
  titulo?: string
  subtitulo?: string
}

export function ChatHubPlaceholder({
  titulo = 'Selecione uma conversa',
  subtitulo = 'Escolha um chat na lista ao lado para começar.',
}: Props) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-100 text-cyan-600 dark:bg-cyan-950/50 dark:text-cyan-400">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">{titulo}</h2>
      <p className="mt-2 max-w-sm text-sm text-slate-500">{subtitulo}</p>
    </div>
  )
}
