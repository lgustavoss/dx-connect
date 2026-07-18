/**
 * Copy comercial da landing (#515) — só o que já opera no produto.
 * Tom orientado a conversão; sem «em breve» / roadmap.
 */

import { APP_DESCRIPTION, APP_NAME, APP_TAGLINE, brandAssets } from '../brand/tokens'

export const landingContactEmail =
  (import.meta.env.VITE_LANDING_CONTACT_EMAIL as string | undefined)?.trim() ||
  'contato@deskrudder.com.br'

export const landingSeo = {
  title: `${APP_NAME} — suporte centralizado para sua empresa`,
  description:
    'Centralize chamados, WhatsApp e prazos num só painel. Organize a fila, acompanhe o time e atenda melhor — sem planilha e sem conversa perdida.',
  ogImage: brandAssets.lockup,
  ogImageAlt: `${APP_NAME} — ${APP_TAGLINE}`,
} as const

export const landingHero = {
  brand: APP_NAME,
  tagline: APP_TAGLINE,
  title: 'Suporte centralizado. Operação sob controle. Cliente bem atendido.',
  titleLines: [
    'Centralize o atendimento.',
    'Organize a fila.',
    'Eleve a experiência do cliente.',
  ] as const,
  subtitle:
    'O DeskRudder reúne chamados, WhatsApp, e-mail e conhecimento num único painel — para sua empresa operar com mais clareza, velocidade e excelência.',
  ctaPrimary: 'Quero ver uma demonstração',
  ctaSecondary: 'Já sou cliente',
  ctaSecondaryTo: '/login',
  trustLine: 'Visibilidade da operação · Priorização simples · Ambiente exclusivo da sua empresa',
} as const

export const landingPain = {
  title: 'Quando cada canal vira um problema, a operação perde controle',
  items: [
    {
      title: 'WhatsApp espalhado por celulares',
      body: 'As conversas se perdem, ninguém assume e a fila vira um caos de mensagens repetidas.',
    },
    {
      title: 'Planilha e e-mail no lugar de processo',
      body: 'A prioridade fica no improviso, e a gestão perde a visão do que está em risco.',
    },
    {
      title: 'Troca de plantão sem contexto',
      body: 'Cada atendente recomeça do zero, e o cliente sente que ninguém está coordenando a resposta.',
    },
  ],
  pivotTitle: 'Com o DeskRudder, o suporte passa a ter direção e consistência',
  pivotBody:
    'Uma fila. Um histórico. Responsabilidades claras. A gestão vê o risco antes de virar reclamação; o time entende o próximo passo; o cliente sente organização desde o primeiro contato.',
} as const

export type LandingShowcaseId = 'chat' | 'tickets' | 'sla' | 'kb'

export const landingShowcases: Array<{
  id: LandingShowcaseId
  eyebrow: string
  title: string
  body: string
  bullets: string[]
  visual: LandingShowcaseId
}> = [
  {
    id: 'chat',
    eyebrow: 'WhatsApp e chat',
    title: 'Toda conversa na mesma fila',
    body: 'WhatsApp, portal e chat interno juntos. Assuma, transfira e registre a demanda sem pular de aplicativo.',
    bullets: [
      'Caixa única para o time de atendimento',
      'Assuma, transfira e acompanhe a conversa',
      'Avisos na hora, para não perder mensagem',
      'Contato ligado ao cadastro do seu cliente',
    ],
    visual: 'chat',
  },
  {
    id: 'tickets',
    eyebrow: 'Chamados',
    title: 'Cada solicitação com dono e histórico',
    body: 'Protocolo, prioridade, setor e responsável. Você sabe quem tocou, o que mudou e quando fechou.',
    bullets: [
      'Abertura por e-mail ou formulário interno',
      'Distribuição automática entre a equipe',
      'Encaminhamento por setor, natureza e prioridade',
      'Transferência entre setores com registro',
    ],
    visual: 'tickets',
  },
  {
    id: 'sla',
    eyebrow: 'Prazos e gestão',
    title: 'Prazos visíveis antes do atraso virar reclamação',
    body: 'Defina metas por setor e prioridade, respeite o horário comercial e receba alerta quando o atendimento entrar em risco.',
    bullets: [
      'Metas de primeira resposta e de resolução',
      'Pausa automática conforme o status do chamado',
      'Alertas por e-mail e no painel',
      'Painéis e exportação em planilha para a gestão',
    ],
    visual: 'sla',
  },
  {
    id: 'kb',
    eyebrow: 'Base de conhecimento',
    title: 'Respostas prontas para o time — e para o cliente',
    body: 'Manuais internos para a equipe e portal de ajuda para o seu cliente, com a sua marca.',
    bullets: [
      'Editor e categorias organizadas',
      'Portal de ajuda personalizável',
      'Sugestão de artigos ao classificar o chamado',
      'Chat ao vivo no portal, na mesma caixa do time',
    ],
    visual: 'kb',
  },
]

export const landingOutcomes = {
  title: 'Resultados que aparecem no dia a dia',
  items: [
    {
      label: 'Fila única',
      body: 'WhatsApp, e-mail e portal passam a seguir o mesmo fluxo, sem disputa por responsabilidade.',
    },
    {
      label: 'Time organizado',
      body: 'Cada setor enxerga sua demanda com contexto, e a gestão vê a operação inteira.',
    },
    {
      label: 'Prazos sob controle',
      body: 'O risco de atraso fica visível antes de virar reclamação e prejudicar a confiança.',
    },
    {
      label: 'Ambiente exclusivo',
      body: 'Seu painel, suas regras, seus dados e seus processos — tudo em um espaço seguro para a empresa.',
    },
  ],
} as const

export const landingHowItWorks = {
  title: 'Como começar a usar',
  steps: [
    {
      n: '01',
      title: 'Monte sua operação',
      body: 'Cadastre setores, atendentes, prazos e regras de encaminhamento.',
    },
    {
      n: '02',
      title: 'Atenda em um só lugar',
      body: 'Chamados e WhatsApp na mesma tela, com fila e histórico claros.',
    },
    {
      n: '03',
      title: 'Acompanhe e melhore',
      body: 'Painéis e alertas para gerir o suporte — não só apagar incêndio.',
    },
  ],
} as const

export const landingAudience = {
  title: 'Para empresas que levam o suporte a sério',
  body: 'Se a sua empresa atende clientes todo dia, o DeskRudder ajuda a centralizar a operação e dar resposta com mais controle.',
  segments: [
    {
      title: 'Software houses e revendas',
      body: 'Você vende o sistema e presta suporte. Mantenha fila, WhatsApp e histórico no mesmo painel.',
    },
    {
      title: 'Suporte B2B / SAC',
      body: 'Centralize chamados, prazos e transferência entre especialidades — sem planilha paralela.',
    },
    {
      title: 'Clientes com várias unidades',
      body: 'Quando um cliente tem mais de uma empresa, o cadastro mantém o contexto certo em cada atendimento.',
    },
  ],
} as const

export const landingMidCta = {
  title: 'Veja o DeskRudder na prática',
  body: 'Em uma demonstração rápida, mostramos a fila, os chamados e o painel de gestão no cenário da sua empresa.',
  ctaPrimary: 'Agendar demonstração',
} as const

export const landingFinalCta = {
  title: 'Pronto para organizar o suporte da sua empresa?',
  body: 'Fale com a gente e veja o DeskRudder funcionando — ou entre no painel se você já é cliente.',
  ctaPrimary: 'Quero uma demonstração',
  ctaSecondary: 'Já sou cliente',
} as const

export const landingFooter = {
  productLine: APP_DESCRIPTION,
  loginLabel: 'Acessar o painel',
  contactLabel: 'Contato',
} as const

/** Assets de marketing em public/marketing/ (prints do ambiente seed local). */
export const landingShots = {
  login: '/marketing/shot-login.png',
  dashboard: '/marketing/shot-dashboard.png',
  tickets: '/marketing/shot-tickets.png',
  chat: '/marketing/shot-chat.png',
  kb: '/marketing/shot-kb.png',
  sla: '/marketing/shot-sla.png',
} as const

export function landingMailtoHref(subject = `Demonstração ${APP_NAME}`): string {
  const q = new URLSearchParams({ subject })
  return `mailto:${landingContactEmail}?${q.toString()}`
}
