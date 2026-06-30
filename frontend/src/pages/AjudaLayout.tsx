import { useMemo, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { ConfigSectionTabs } from '../components/config/ConfigSectionTabs'
import { Button } from '../components/ui/Button'

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
  const [copiado, setCopiado] = useState(false)
  const hint = TAB_HINTS[abaAtiva(pathname)] ?? ''
  const publicKbUrl = useMemo(
    () => (typeof window !== 'undefined' ? `${window.location.origin}/kb` : '/kb'),
    [],
  )

  async function copiarLinkPublico() {
    try {
      await navigator.clipboard.writeText(publicKbUrl)
      setCopiado(true)
      window.setTimeout(() => setCopiado(false), 2000)
    } catch {
      setCopiado(false)
    }
  }

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
        actions={
          <div className="w-fit max-w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-800/60">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
              Consulta pública para clientes
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <a
                href="/kb"
                target="_blank"
                rel="noreferrer"
                className="text-sm font-medium whitespace-nowrap text-teal-700 hover:underline dark:text-teal-400"
              >
                {publicKbUrl}
              </a>
              <Button type="button" variant="secondary" className="shrink-0 px-2.5 py-1 text-xs" onClick={() => void copiarLinkPublico()}>
                {copiado ? 'Copiado!' : 'Copiar'}
              </Button>
            </div>
          </div>
        }
      />
      <ConfigSectionTabs tabs={tabs} ariaLabel="Seções de ajuda" />
      {hint ? <p className="text-sm text-slate-600 dark:text-slate-400">{hint}</p> : null}
      <Outlet />
    </PageContainer>
  )
}
