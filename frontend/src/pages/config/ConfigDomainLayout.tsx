import { Navigate, Outlet, useLocation, useParams } from 'react-router-dom'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { ConfigSectionTabs } from '../../components/config/ConfigSectionTabs'
import { ConfigLegacyRedirect } from './ConfigLegacyRedirect'
import { configItemPath, findConfigGroupByPrefix } from './configNav'

/** Index do domínio → primeira aba. */
export function ConfigDomainIndexRedirect() {
  const { domain } = useParams<{ domain: string }>()
  const group = findConfigGroupByPrefix(domain || '')
  const first = group?.items[0]
  if (!group || !first) return <ConfigLegacyRedirect />
  return <Navigate to={configItemPath(group, first)} replace />
}

/** Layout de domínio de Configurações (abas + hint) — #833. */
export function ConfigDomainLayout() {
  const { pathname } = useLocation()
  const { domain } = useParams<{ domain: string }>()
  const group = findConfigGroupByPrefix(domain || '')

  if (!group) {
    return <ConfigLegacyRedirect />
  }

  const tabs = group.items.map((item) => ({
    to: configItemPath(group, item),
    label: item.label,
  }))

  const escaped = group.pathPrefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const slug =
    pathname.match(new RegExp(`/configuracoes/${escaped}/([^/]+)`))?.[1] ?? group.items[0]?.slug
  const hint = group.items.find((i) => i.slug === slug)?.hint ?? ''

  return (
    <PageContainer>
      <PageHeader title={group.label} subtitle={group.description} />
      <ConfigSectionTabs tabs={tabs} ariaLabel={`Seções: ${group.label}`} />
      {hint ? <p className="text-sm text-slate-600 dark:text-slate-400">{hint}</p> : null}
      <Outlet />
    </PageContainer>
  )
}
