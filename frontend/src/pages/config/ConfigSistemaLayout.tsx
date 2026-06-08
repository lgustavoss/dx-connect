import { Outlet, useLocation } from 'react-router-dom'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { ConfigSectionTabs } from '../../components/config/ConfigSectionTabs'

const TABS = [
  { to: '/configuracoes/sistema/empresa', label: 'Empresa' },
  { to: '/configuracoes/sistema/email', label: 'E-mail' },
  { to: '/configuracoes/sistema/whatsapp', label: 'WhatsApp' },
  { to: '/configuracoes/sistema/auditoria', label: 'Auditoria' },
] as const

const TAB_HINTS: Record<string, string> = {
  empresa: 'Dados institucionais da instalação — CNPJ, logo e endereço.',
  email: 'Encaminhamento por setor e envio de respostas aos clientes.',
  whatsapp: 'Conexão Evolution API, mensagens automáticas e horários de atendimento.',
  auditoria: 'Histórico de alterações em cadastros e configurações.',
}

function abaAtiva(pathname: string): string {
  const match = pathname.match(/\/configuracoes\/sistema\/([^/]+)/)
  return match?.[1] ?? 'empresa'
}

export function ConfigSistemaLayout() {
  const { pathname } = useLocation()
  const hint = TAB_HINTS[abaAtiva(pathname)] ?? ''

  return (
    <PageContainer>
      <PageHeader title="Sistema" subtitle="Empresa, integrações e auditoria." />
      <ConfigSectionTabs tabs={[...TABS]} ariaLabel="Seções do sistema" />
      {hint ? <p className="text-sm text-slate-600 dark:text-slate-400">{hint}</p> : null}
      <Outlet />
    </PageContainer>
  )
}
