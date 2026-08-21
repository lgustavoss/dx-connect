/** Navegação de Configurações — hub + sidebar + abas (#833). */

export type ConfigNavItem = {
  /** Segmento de URL (último path). */
  slug: string
  label: string
  hint: string
  keywords: string[]
}

export type ConfigNavGroup = {
  id: string
  /** Prefixo de rota: /configuracoes/{pathPrefix}/… */
  pathPrefix: string
  label: string
  description: string
  /** Ícone do Sidebar (chave em ICONS). */
  icon: string
  items: ConfigNavItem[]
}

export const CONFIG_GROUPS: ConfigNavGroup[] = [
  {
    id: 'equipa',
    pathPrefix: 'equipa',
    label: 'Equipa e tickets',
    description: 'Setores, atendentes, fluxo de tickets, roteamento e SLA.',
    icon: 'setores',
    items: [
      {
        slug: 'setores',
        label: 'Setores',
        hint: 'Áreas de atuação dos atendentes (suporte, financeiro, comercial…).',
        keywords: ['setor', 'área', 'equipe'],
      },
      {
        slug: 'atendentes',
        label: 'Atendentes',
        hint: 'Usuários internos que operam tickets e o chat.',
        keywords: ['utilizador', 'usuário', 'login', 'perfil'],
      },
      {
        slug: 'status-ticket',
        label: 'Status de ticket',
        hint: 'Etapas do fluxo de chamados (aberto, em atendimento, encerrado…).',
        keywords: ['estado', 'pipeline', 'status'],
      },
      {
        slug: 'natureza-motivo',
        label: 'Natureza e motivo',
        hint: 'Categorias (natureza) e itens específicos (motivo) usados ao encerrar tickets.',
        keywords: ['classificação', 'categoria', 'encerrar'],
      },
      {
        slug: 'respostas-prontas',
        label: 'Respostas prontas',
        hint: 'Macros reutilizáveis ao responder tickets — globais ou por setor.',
        keywords: ['macro', 'template', 'resposta'],
      },
      {
        slug: 'roteamento',
        label: 'Roteamento',
        hint: 'Regras automáticas de setor e prioridade na criação de tickets (e-mail e manual).',
        keywords: ['regra', 'automação', 'distribuição'],
      },
      {
        slug: 'sla',
        label: 'SLA',
        hint: 'Metas de SLA por setor/prioridade e calendários comerciais (horário útil).',
        keywords: ['prazo', 'meta', 'calendário'],
      },
    ],
  },
  {
    id: 'canais',
    pathPrefix: 'canais',
    label: 'Canais',
    description: 'WhatsApp, e-mail e portal da base de conhecimento.',
    icon: 'chat',
    items: [
      {
        slug: 'whatsapp',
        label: 'WhatsApp',
        hint: 'Conexão, mensagens automáticas, inatividade, avaliação e horários de atendimento.',
        keywords: ['wpp', 'evolution', 'fila', 'inatividade'],
      },
      {
        slug: 'email',
        label: 'E-mail',
        hint: 'Encaminhamento por setor e envio de respostas aos clientes.',
        keywords: ['smtp', 'mail', 'inbox'],
      },
      {
        slug: 'base-conhecimento',
        label: 'Base de conhecimento',
        hint: 'Personalização do portal público /kb — cores, textos e aparência.',
        keywords: ['kb', 'portal', 'ajuda', 'artigos'],
      },
    ],
  },
  {
    id: 'comercial',
    pathPrefix: 'comercial',
    label: 'Comercial / CRM',
    description: 'Funil, propostas, contratos, custos e checklist de implantação.',
    icon: 'tiposNegocio',
    items: [
      {
        slug: 'funil-crm',
        label: 'Funil CRM',
        hint: 'Estágios do funil comercial (Lead, Em negociação…). Usados na lista e no Kanban do CRM.',
        keywords: ['crm', 'lead', 'kanban', 'estágio'],
      },
      {
        slug: 'propostas',
        label: 'Modelos de proposta',
        hint: 'HTML dos modelos da proposta comercial. Placeholders são preenchidos na negociação.',
        keywords: ['proposta', 'comercial', 'html'],
      },
      {
        slug: 'contratos',
        label: 'Modelos de contrato',
        hint: 'HTML dos modelos do contrato comercial. Placeholders (fidelidade, setup, cláusulas) são preenchidos na negociação.',
        keywords: ['contrato', 'assinatura', 'fidelidade'],
      },
      {
        slug: 'custos',
        label: 'Catálogo de custos',
        hint: 'Salário mínimo com vigência, perfis/módulos de custo e simulador estimado para negociação.',
        keywords: ['custo', 'preço', 'simulador'],
      },
      {
        slug: 'implantacao',
        label: 'Checklist de implantação',
        hint: 'Itens copiados para o ticket automático quando o contrato é marcado como assinado.',
        keywords: ['implantação', 'checklist', 'onboarding'],
      },
    ],
  },
  {
    id: 'empresa',
    pathPrefix: 'empresa-catalogos',
    label: 'Empresa e catálogos',
    description: 'Dados da instalação, tipos de negócio e catálogos de PDV.',
    icon: 'empresas',
    items: [
      {
        slug: 'empresa',
        label: 'Empresa',
        hint: 'Dados institucionais da instalação — CNPJ, logo e endereço.',
        keywords: ['cnpj', 'logo', 'institucional'],
      },
      {
        slug: 'tipos-negocio',
        label: 'Tipos de negócio',
        hint: 'Classificação das empresas (posto, conveniência, restaurante…).',
        keywords: ['posto', 'classificação', 'tipo'],
      },
      {
        slug: 'pdv',
        label: 'Catálogos PDV',
        hint: 'Rótulos de dispositivo e tipos de acesso remoto usados no cadastro de PDVs por empresa.',
        keywords: ['pdv', 'remoto', 'dispositivo'],
      },
    ],
  },
  {
    id: 'admin',
    pathPrefix: 'administracao',
    label: 'Administração',
    description: 'Auditoria e ferramentas administrativas.',
    icon: 'configuracoes',
    items: [
      {
        slug: 'auditoria',
        label: 'Auditoria',
        hint: 'Histórico de alterações em cadastros e configurações.',
        keywords: ['log', 'histórico', 'alterações'],
      },
      {
        slug: 'sugestoes',
        label: 'Sugestões de clientes',
        hint: 'Triagem de pedidos enviados a partir das notas de versão.',
        keywords: ['sugestão', 'feedback', 'release', 'github'],
      },
    ],
  },
]

export function configItemPath(group: ConfigNavGroup, item: ConfigNavItem): string {
  return `/configuracoes/${group.pathPrefix}/${item.slug}`
}

export function configGroupIndexPath(group: ConfigNavGroup): string {
  return `/configuracoes/${group.pathPrefix}`
}

export function findConfigGroupByPrefix(pathPrefix: string): ConfigNavGroup | undefined {
  return CONFIG_GROUPS.find((g) => g.pathPrefix === pathPrefix)
}

/** Redirects 1:1 de URLs antigas (#833). */
export const CONFIG_LEGACY_REDIRECTS: Array<{ from: string; to: string }> = [
  { from: '/configuracoes/atendimento', to: '/configuracoes/equipa' },
  { from: '/configuracoes/atendimento/setores', to: '/configuracoes/equipa/setores' },
  { from: '/configuracoes/atendimento/atendentes', to: '/configuracoes/equipa/atendentes' },
  { from: '/configuracoes/atendimento/status-ticket', to: '/configuracoes/equipa/status-ticket' },
  { from: '/configuracoes/atendimento/natureza-motivo', to: '/configuracoes/equipa/natureza-motivo' },
  { from: '/configuracoes/atendimento/respostas-prontas', to: '/configuracoes/equipa/respostas-prontas' },
  { from: '/configuracoes/atendimento/roteamento', to: '/configuracoes/equipa/roteamento' },
  { from: '/configuracoes/atendimento/sla', to: '/configuracoes/equipa/sla' },
  { from: '/configuracoes/atendimento/sla/politicas', to: '/configuracoes/equipa/sla/politicas' },
  { from: '/configuracoes/atendimento/sla/calendarios', to: '/configuracoes/equipa/sla/calendarios' },
  { from: '/configuracoes/atendimento/base-conhecimento', to: '/ajuda/artigos' },
  { from: '/configuracoes/sistema', to: '/configuracoes/empresa-catalogos' },
  { from: '/configuracoes/sistema/empresa', to: '/configuracoes/empresa-catalogos/empresa' },
  { from: '/configuracoes/sistema/email', to: '/configuracoes/canais/email' },
  { from: '/configuracoes/sistema/whatsapp', to: '/configuracoes/canais/whatsapp' },
  { from: '/configuracoes/sistema/base-conhecimento', to: '/configuracoes/canais/base-conhecimento' },
  { from: '/configuracoes/sistema/auditoria', to: '/configuracoes/administracao/auditoria' },
  { from: '/configuracoes/sistema/empresa-email', to: '/configuracoes/empresa-catalogos/empresa' },
  { from: '/configuracoes/cadastros', to: '/configuracoes/empresa-catalogos' },
  { from: '/configuracoes/cadastros/tipos-negocio', to: '/configuracoes/empresa-catalogos/tipos-negocio' },
  { from: '/configuracoes/cadastros/pdv', to: '/configuracoes/empresa-catalogos/pdv' },
  { from: '/configuracoes/cadastros/custos', to: '/configuracoes/comercial/custos' },
  { from: '/configuracoes/cadastros/funil-crm', to: '/configuracoes/comercial/funil-crm' },
  { from: '/configuracoes/cadastros/propostas', to: '/configuracoes/comercial/propostas' },
  { from: '/configuracoes/cadastros/contratos', to: '/configuracoes/comercial/contratos' },
  { from: '/configuracoes/cadastros/implantacao', to: '/configuracoes/comercial/implantacao' },
  { from: '/configuracoes/whatsapp', to: '/configuracoes/canais/whatsapp' },
  { from: '/configuracoes/empresa-email', to: '/configuracoes/empresa-catalogos/empresa' },
  { from: '/configuracoes/pdv-catalogos', to: '/configuracoes/empresa-catalogos/pdv' },
]
