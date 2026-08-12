import { Outlet, useLocation } from 'react-router-dom'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { ConfigSectionTabs } from '../../components/config/ConfigSectionTabs'

const TABS = [
  { to: '/configuracoes/cadastros/tipos-negocio', label: 'Tipos de negócio' },
  { to: '/configuracoes/cadastros/pdv', label: 'Catálogos PDV' },
  { to: '/configuracoes/cadastros/custos', label: 'Catálogo de custos' },
] as const

const TAB_HINTS: Record<string, string> = {
  'tipos-negocio': 'Classificação das empresas (posto, conveniência, restaurante…).',
  pdv: 'Rótulos de dispositivo e tipos de acesso remoto usados no cadastro de PDVs por empresa.',
  custos: 'Salário mínimo com vigência, perfis/módulos de custo e simulador estimado para negociação.',
}

function abaAtiva(pathname: string): string {
  const match = pathname.match(/\/configuracoes\/cadastros\/([^/]+)/)
  return match?.[1] ?? 'tipos-negocio'
}

export function ConfigCadastrosLayout() {
  const { pathname } = useLocation()
  const hint = TAB_HINTS[abaAtiva(pathname)] ?? ''

  return (
    <PageContainer>
      <PageHeader title="Cadastros" subtitle="Tipos de negócio, catálogos de PDV e custos comerciais." />
      <ConfigSectionTabs tabs={[...TABS]} ariaLabel="Seções de cadastros" />
      {hint ? <p className="text-sm text-slate-600 dark:text-slate-400">{hint}</p> : null}
      <Outlet />
    </PageContainer>
  )
}
