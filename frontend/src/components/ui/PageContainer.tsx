import type { ReactNode } from 'react'

const MAX_WIDTH_CLASS = {
  '3xl': 'max-w-3xl',
  '5xl': 'max-w-5xl',
  '6xl': 'max-w-6xl',
  '7xl': 'max-w-7xl',
} as const

const SPACING_CLASS = {
  none: '',
  normal: 'space-y-6',
  relaxed: 'space-y-8',
} as const

export type PageContainerMaxWidth = keyof typeof MAX_WIDTH_CLASS
export type PageContainerSpacing = keyof typeof SPACING_CLASS

export const PAGE_CONTAINER_CLASS = `mx-auto w-full ${MAX_WIDTH_CLASS['6xl']} ${SPACING_CLASS.normal} pb-10`

type PageContainerProps = {
  children: ReactNode
  className?: string
  maxWidth?: PageContainerMaxWidth
  spacing?: PageContainerSpacing
}

/** Container padrão das telas do app (listagens, configurações, detalhes). */
export function PageContainer({
  children,
  className = '',
  maxWidth = '6xl',
  spacing = 'normal',
}: PageContainerProps) {
  return (
    <div
      className={`mx-auto w-full ${MAX_WIDTH_CLASS[maxWidth]} ${SPACING_CLASS[spacing]} ${spacing === 'none' ? '' : 'pb-10'} ${className}`.trim()}
    >
      {children}
    </div>
  )
}

type PageHeaderProps = {
  title: string
  subtitle?: string
  actions?: ReactNode
}

/** Cabeçalho padrão: título, subtítulo opcional e ações à direita. */
export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p> : null}
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </div>
  )
}
