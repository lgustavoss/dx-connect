import type { ReactNode } from 'react'
import { PageContainer, PageHeader } from '../ui/PageContainer'

type Props = {
  embedded?: boolean
  forbidden?: boolean
  denied: ReactNode
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}

/** Envolve listagens de configuração no modo página inteira ou embutido em abas do hub. */
export function ConfigListPageShell({
  embedded = false,
  forbidden = false,
  denied,
  title,
  subtitle,
  actions,
  children,
}: Props) {
  if (forbidden) {
    return embedded ? denied : <PageContainer>{denied}</PageContainer>
  }

  const content = (
    <>
      {embedded ? (
        actions ? <div className="flex justify-end">{actions}</div> : null
      ) : (
        <PageHeader title={title} subtitle={subtitle} actions={actions} />
      )}
      {children}
    </>
  )

  return embedded ? content : <PageContainer>{content}</PageContainer>
}
