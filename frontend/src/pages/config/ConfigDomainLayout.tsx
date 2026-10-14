import { Navigate, Outlet, useLocation, useParams } from 'react-router-dom'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { ConfigSectionTabs } from '../../components/config/ConfigSectionTabs'
import { useAuth } from '../../contexts/AuthContext'
import { temPermissao } from '../../lib/permissoes'
import { ConfigLegacyRedirect } from './ConfigLegacyRedirect'
import { PERMISSAO_CONFIG, configItemPath, findConfigGroupByPrefix } from './configNav'

function itensVisiveis(group: NonNullable<ReturnType<typeof findConfigGroupByPrefix>>, role: string | undefined, permissoes: string[] | undefined) {
  const usuario = { role, permissoes }
  return group.items.filter((item) => {
    const codigo = PERMISSAO_CONFIG[item.slug]
    return !codigo || temPermissao(usuario, codigo)
  })
}

/** Index do domínio → primeira aba que a pessoa pode abrir. */
export function ConfigDomainIndexRedirect() {
  const { user } = useAuth()
  const { domain } = useParams<{ domain: string }>()
  const group = findConfigGroupByPrefix(domain || '')
  const first = group ? itensVisiveis(group, user?.role, user?.permissoes)[0] : undefined
  if (!group || !first) return <ConfigLegacyRedirect />
  return <Navigate to={configItemPath(group, first)} replace />
}

/** Layout de domínio de Configurações (abas + hint) — #833. */
export function ConfigDomainLayout() {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const { domain } = useParams<{ domain: string }>()
  const group = findConfigGroupByPrefix(domain || '')

  if (!group) {
    return <ConfigLegacyRedirect />
  }

  const visiveis = itensVisiveis(group, user?.role, user?.permissoes)
  const tabs = visiveis.map((item) => ({
    to: configItemPath(group, item),
    label: item.label,
  }))

  const escaped = group.pathPrefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const slug =
    pathname.match(new RegExp(`/configuracoes/${escaped}/([^/]+)`))?.[1] ?? visiveis[0]?.slug
  const hint = visiveis.find((i) => i.slug === slug)?.hint ?? ''

  return (
    <PageContainer>
      <PageHeader title={group.label} subtitle={group.description} />
      <ConfigSectionTabs tabs={tabs} ariaLabel={`Seções: ${group.label}`} />
      {hint ? <p className="text-sm text-slate-600 dark:text-slate-400">{hint}</p> : null}
      <Outlet />
    </PageContainer>
  )
}
