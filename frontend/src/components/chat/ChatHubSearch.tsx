import { useChatHub } from '../../contexts/ChatHubContext'

export function ChatHubSearch({ placeholder = 'Pesquise por conversas' }: { placeholder?: string }) {
  const { busca, setBusca } = useChatHub()

  return (
    <div className="shrink-0 border-b border-slate-200 p-3 dark:border-slate-800">
      <div className="relative">
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
          className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        />
      </div>
    </div>
  )
}
