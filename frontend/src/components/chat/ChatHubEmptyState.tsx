import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

type Action =
  | { type: 'link'; to: string; label: string }
  | { type: 'button'; label: string; onClick: () => void }

type Props = {
  title: string
  description?: string
  actions?: Action[]
  icon?: ReactNode
}

/** Estado vazio da lista do hub de chats — #756. */
export function ChatHubEmptyState({ title, description, actions, icon }: Props) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      {icon ? (
        <div className="flex size-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
          {icon}
        </div>
      ) : (
        <div
          className="flex size-12 items-center justify-center rounded-2xl bg-slate-100 text-2xl text-slate-400 dark:bg-slate-800"
          aria-hidden
        >
          💬
        </div>
      )}
      <div className="space-y-1">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</p>
        {description ? (
          <p className="max-w-xs text-xs leading-relaxed text-slate-500 dark:text-slate-400">{description}</p>
        ) : null}
      </div>
      {actions && actions.length > 0 ? (
        <div className="mt-1 flex flex-wrap items-center justify-center gap-2">
          {actions.map((a) =>
            a.type === 'link' ? (
              <Link
                key={a.label}
                to={a.to}
                className="inline-flex min-h-11 items-center justify-center rounded-lg bg-cyan-600 px-4 text-sm font-semibold text-white hover:bg-cyan-700"
              >
                {a.label}
              </Link>
            ) : (
              <button
                key={a.label}
                type="button"
                onClick={a.onClick}
                className="inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {a.label}
              </button>
            ),
          )}
        </div>
      ) : null}
    </div>
  )
}
