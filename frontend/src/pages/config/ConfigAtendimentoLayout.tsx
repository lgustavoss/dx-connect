import { Outlet, useLocation } from 'react-router-dom'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { ConfigSectionTabs } from '../../components/config/ConfigSectionTabs'

const TABS = [
  { to: '/configuracoes/atendimento/setores', label: 'Setores' },
  { to: '/configuracoes/atendimento/atendentes', label: 'Atendentes' },
  { to: '/configuracoes/atendimento/status-ticket', label: 'Status de ticket' },
  { to: '/configuracoes/atendimento/natureza-motivo', label: 'Natureza e motivo' },
  { to: '/configuracoes/atendimento/respostas-prontas', label: 'Respostas prontas' },
  { to: '/configuracoes/atendimento/roteamento', label: 'Roteamento' },
  { to: '/configuracoes/atendimento/sla', label: 'SLA' },
] as const

const TAB_HINTS: Record<string, string> = {
  setores: 'Áreas de atuação dos atendentes (suporte, financeiro, comercial…).',
  atendentes: 'Usuários internos que operam tickets e o chat.',
  'status-ticket': 'Etapas do fluxo de chamados (aberto, em atendimento, encerrado…).',
  'natureza-motivo': 'Categorias (natureza) e itens específicos (motivo) usados ao encerrar tickets.',
  'respostas-prontas': 'Macros reutilizáveis ao responder tickets — globais ou por setor.',
  roteamento: 'Regras automáticas de setor e prioridade na criação de tickets (e-mail e manual).',
  sla: 'Metas de SLA por setor/prioridade e calendários comerciais (horário útil).',
}

function abaAtiva(pathname: string): string {
  const match = pathname.match(/\/configuracoes\/atendimento\/([^/]+)/)
  return match?.[1] ?? 'setores'
}

export function ConfigAtendimentoLayout() {
  const { pathname } = useLocation()
  const hint = TAB_HINTS[abaAtiva(pathname)] ?? ''

  return (
    <PageContainer>
      <PageHeader
        title="Atendimento"
        subtitle="Setores, equipe, status, classificação e respostas prontas."
      />
      <ConfigSectionTabs tabs={[...TABS]} ariaLabel="Seções de atendimento" />
      {hint ? <p className="text-sm text-slate-600 dark:text-slate-400">{hint}</p> : null}
      <Outlet />
    </PageContainer>
  )
}
