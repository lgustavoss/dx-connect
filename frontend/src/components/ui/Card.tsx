import { type HTMLAttributes, type ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string
  description?: string
  /** Ações à direita do título (ex.: link). */
  titleActions?: ReactNode
  /** Classes do corpo (ex.: `p-0` para tabela edge-to-edge). */
  bodyClassName?: string
}

export function Card({
  title,
  description,
  titleActions,
  bodyClassName = 'p-6',
  className = '',
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/95 dark:shadow-none dark:ring-1 dark:ring-white/5 ${className}`}
      {...props}
    >
      {title ? (
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">{title}</h2>
            {description ? (
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            ) : null}
          </div>
          {titleActions ? <div className="shrink-0">{titleActions}</div> : null}
        </div>
      ) : null}
      <div className={bodyClassName}>{children}</div>
    </div>
  )
}
