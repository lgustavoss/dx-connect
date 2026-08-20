import { useChatHub } from '../../contexts/ChatHubContext'
import { ChatFilaSomToggle } from './ChatFilaSomToggle'

export function ChatHubSearch({ placeholder = 'Pesquise por conversas' }: { placeholder?: string }) {
  const { busca, setBusca } = useChatHub()
  const temBusca = Boolean(busca.trim())

  return (
    <div className="sticky top-0 z-10 shrink-0 border-b border-slate-200 bg-white/95 p-3 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/95">
      <div className="flex items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder={placeholder}
            enterKeyHint="search"
            className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-base leading-normal text-slate-900 placeholder:text-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          />
        </div>
        {temBusca ? (
          <button
            type="button"
            className="inline-flex min-h-11 shrink-0 items-center rounded-lg px-2 text-sm font-medium text-cyan-700 dark:text-cyan-400"
            onClick={() => {
              setBusca('')
              ;(document.activeElement as HTMLElement | null)?.blur?.()
            }}
          >
            Limpar
          </button>
        ) : null}
        <ChatFilaSomToggle size="lg" />
      </div>
    </div>
  )
}
