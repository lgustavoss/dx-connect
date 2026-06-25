import { Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { ConfigSectionTabs } from '../components/config/ConfigSectionTabs'

const TAB_HINTS: Record<string, string> = {
  consultar: 'Busque e leia manuais publicados pela equipe.',
  categorias: 'Organize os manuais em pastas e subpastas.',
  artigos: 'Crie, edite e publique manuais para a equipe consultar.',
}

function abaAtiva(pathname: string): string {
  if (pathname.startsWith('/ajuda/artigos')) return 'artigos'
  if (pathname.startsWith('/ajuda/categorias')) return 'categorias'
  return 'consultar'
}

export function AjudaLayout() {
  const { isAdmin } = useAuth()
  const { pathname } = useLocation()
  const hint = TAB_HINTS[abaAtiva(pathname)] ?? ''

  const tabs = [
    { to: '/ajuda/consultar', label: 'Consultar', end: true },
    ...(isAdmin
      ? [
          { to: '/ajuda/categorias', label: 'Categorias', end: true },
          { to: '/ajuda/artigos', label: 'Artigos', end: true },
        ]
      : []),
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Ajuda"
        subtitle="Manuais e procedimentos para consulta da equipe."
      />
      <ConfigSectionTabs tabs={tabs} ariaLabel="Seções de ajuda" />
      {hint ? <p className="text-sm text-slate-600 dark:text-slate-400">{hint}</p> : null}
      <Outlet />
    </PageContainer>
  )
}
