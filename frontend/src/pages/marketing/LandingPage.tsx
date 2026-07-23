import { Link } from 'react-router-dom'
import { useCallback, useState, type MouseEvent, type ReactNode } from 'react'
import { BrandLogo } from '../../brand'
import { APP_NAME } from '../../brand/tokens'
import { LandingContactSlot } from '../../components/marketing/LandingContactSlot'
import { LandingLightbox, LandingShotButton } from '../../components/marketing/LandingLightbox'
import { LandingProductShot, landingShotSrc } from '../../components/marketing/LandingProductShot'
import {
  landingAudience,
  landingContactEmail,
  landingFinalCta,
  landingFooter,
  landingHero,
  landingHowItWorks,
  landingMidCta,
  landingOutcomes,
  landingPain,
  landingShowcases,
  landingShots,
} from '../../content/landing'
import { isSaasControlPlaneFrontend, SAAS_LICENCAS_PATH } from '../../lib/saasControlPlane'
import { MarketingLayout } from './MarketingLayout'

function SecondaryLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center justify-center rounded-2xl border border-sky-400/30 bg-white/5 px-5 py-3 text-sm font-semibold text-sky-100 shadow-[0_0_0_1px_rgba(255,255,255,0.03)] backdrop-blur-sm transition duration-200 hover:-translate-y-0.5 hover:border-sky-300/50 hover:bg-sky-400/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60"
    >
      {children}
    </Link>
  )
}

function SectionHeading({
  eyebrow,
  title,
  body,
  align = 'left',
}: {
  eyebrow?: string
  title: string
  body?: string
  align?: 'left' | 'center'
}) {
  return (
    <div className={align === 'center' ? 'mx-auto max-w-3xl text-center' : 'max-w-3xl'}>
      {eyebrow ? (
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.25em] text-sky-400">{eyebrow}</p>
      ) : null}
      <div className={align === 'center' ? 'mx-auto h-px w-20 bg-gradient-to-r from-sky-500/0 via-sky-400/80 to-sky-500/0' : 'h-px w-20 bg-gradient-to-r from-sky-500/0 via-sky-400/80 to-sky-500/0'} />
      <h2 className="mt-5 text-3xl font-bold tracking-tight text-white sm:text-4xl">{title}</h2>
      {body ? <p className="mt-4 text-lg leading-relaxed text-slate-300">{body}</p> : null}
    </div>
  )
}

function scrollToSection(e: MouseEvent<HTMLAnchorElement>, id: string) {
  e.preventDefault()
  const root = document.querySelector('[data-landing-scroll-root]')
  const el = document.getElementById(id)
  if (!el) return
  if (root instanceof HTMLElement) {
    const top = el.getBoundingClientRect().top - root.getBoundingClientRect().top + root.scrollTop - 12
    root.scrollTo({ top, behavior: 'smooth' })
  } else {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  if (window.history.replaceState) {
    window.history.replaceState(null, '', `#${id}`)
  }
}

type LightboxState = { src: string; alt: string } | null

export function LandingPage() {
  const [lightbox, setLightbox] = useState<LightboxState>(null)
  const closeLightbox = useCallback(() => setLightbox(null), [])

  const heroProofPoints = ['Fila única', 'SLA visível', 'Base de conhecimento', 'Painel executivo']
  const heroStats = [
    { value: '+40%', label: 'visibilidade da fila em tempo real' },
    { value: '0', label: 'perda de contexto entre setores' },
    { value: '24/7', label: 'controle do fluxo sem improviso' },
  ]
  const experienceHighlights = [
    {
      title: 'Resposta com contexto',
      body: 'Cada demanda chega completa, com histórico, prioridade e próximos passos já definidos.',
    },
    {
      title: 'Visibilidade executiva',
      body: 'SLA, fila e risco ocupam um só painel, para a gestão decidir sem ruído.',
    },
    {
      title: 'Fluxo único',
      body: 'Chamados, WhatsApp e e-mail seguem o mesmo processo, com menos retrabalho e mais consistência.',
    },
  ]
  const credibilityMetrics = [
    { value: '3x', label: 'mais velocidade na coordenação' },
    { value: '100%', label: 'visibilidade da operação em um só painel' },
    { value: '≤ 1 min', label: 'para entender o próximo passo' },
  ]
  const valuePillars = [
    {
      title: 'Centralize a operação',
      body: 'Junte tickets, WhatsApp, e-mail e conhecimento num único contexto, sem perder o histórico.',
    },
    {
      title: 'Acelere a resposta',
      body: 'Defina prioridades, encaminhe rápido e mantenha o time alinhado com visão real do fluxo.',
    },
    {
      title: 'Mostre resultado',
      body: 'Tenha métricas claras de SLA, produtividade e atendimento para tomar decisão com confiança.',
    },
  ]

  return (
    <MarketingLayout>
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#071826]/85 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <BrandLogo variant="full" size="md" markVariant="onDark" />
          <nav className="flex flex-wrap items-center justify-end gap-2 sm:gap-4">
            <a
              href="#produto"
              onClick={(e) => scrollToSection(e, 'produto')}
              className="hidden text-sm font-medium text-slate-300 transition hover:text-white md:inline"
            >
              Produto
            </a>
            <a
              href="#resultados"
              onClick={(e) => scrollToSection(e, 'resultados')}
              className="hidden text-sm font-medium text-slate-300 transition hover:text-white md:inline"
            >
              Resultados
            </a>
            <Link
              to={landingHero.ctaSecondaryTo}
              className="rounded-full px-3 py-2 text-sm font-semibold text-sky-300 transition hover:bg-white/5 hover:text-sky-200"
            >
              {landingHero.ctaSecondary}
            </Link>
            {isSaasControlPlaneFrontend() ? (
              <Link
                to={`/login?next=${encodeURIComponent(SAAS_LICENCAS_PATH)}`}
                className="rounded-full border border-sky-400/35 bg-sky-400/10 px-3 py-2 text-sm font-semibold text-sky-100 transition hover:border-sky-300/50 hover:bg-sky-400/20"
              >
                Painel de licenças
              </Link>
            ) : null}
            <LandingContactSlot
              variant="hero"
              label="Ver demonstração"
              className="!px-4 !py-2 text-xs sm:text-sm"
            />
          </nav>
        </div>
      </header>

      <main>
        <section className="relative isolate overflow-hidden py-8 sm:py-10 lg:py-12">
          <div className="absolute inset-x-0 top-0 -z-10 h-[32rem] bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.22),_transparent_46%),radial-gradient(circle_at_85%_12%,_rgba(14,165,233,0.16),_transparent_38%)]" />
          <div className="pointer-events-none absolute left-8 top-20 hidden h-40 w-40 rounded-full border border-sky-400/20 bg-sky-400/10 blur-3xl lg:block" />
          <div className="pointer-events-none absolute right-10 top-24 hidden h-56 w-56 rounded-full border border-white/10 bg-white/5 blur-3xl lg:block" />
          <div className="mx-auto flex min-h-[calc(100dvh-5.5rem)] w-full max-w-7xl flex-col justify-center px-5 pb-16 pt-8 sm:px-8 sm:pb-20 lg:px-10">
            <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12 xl:gap-16">
              <div className="landing-fade-up min-w-0">
                <div className="inline-flex items-center gap-2 rounded-full border border-sky-400/30 bg-sky-400/10 px-3.5 py-2 text-sm font-medium text-sky-200 shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
                  <span className="size-2 rounded-full bg-sky-400" />
                  {landingHero.brand} · {landingHero.tagline}
                </div>
                <h1 className="mt-6 bg-gradient-to-r from-white via-sky-100 to-slate-400 bg-clip-text text-[2.15rem] font-bold leading-[1.08] tracking-tight text-transparent sm:text-5xl lg:text-[3.2rem] lg:leading-[1.05]">
                  {landingHero.titleLines.map((line) => (
                    <span key={line} className="block">
                      {line}
                    </span>
                  ))}
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
                  {landingHero.subtitle}
                </p>
                <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300">
                  <span className="size-2 rounded-full bg-emerald-400" />
                  Plataforma premium para operações de suporte que querem excelência
                </div>
                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <LandingContactSlot variant="hero" label={landingHero.ctaPrimary} />
                  <SecondaryLink to={landingHero.ctaSecondaryTo}>{landingHero.ctaSecondary}</SecondaryLink>
                </div>
                <div className="mt-7 flex flex-wrap gap-2">
                  {heroProofPoints.map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300"
                    >
                      {item}
                    </span>
                  ))}
                </div>
                <div className="mt-8 grid gap-3 sm:grid-cols-3">
                  {heroStats.map((stat) => (
                    <div key={stat.label} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-sm">
                      <p className="text-xl font-semibold text-white">{stat.value}</p>
                      <p className="mt-1 text-sm text-slate-400">{stat.label}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="landing-shot min-w-0 lg:justify-self-stretch">
                <div className="relative overflow-hidden rounded-[1.9rem] border border-white/10 bg-gradient-to-br from-white/[0.08] via-slate-950/80 to-slate-900/90 p-3 shadow-[0_30px_80px_rgba(2,8,23,0.45)] backdrop-blur-xl sm:p-4 before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-sky-400/70 before:to-transparent">
                  <div className="mb-4 flex items-center justify-between rounded-full border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-slate-300">
                    <span className="font-medium text-white">Operação premium</span>
                    <span className="rounded-full border border-sky-400/25 bg-sky-400/10 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">
                      em tempo real
                    </span>
                  </div>
                  <LandingShotButton
                    label="Painel DeskRudder"
                    onOpen={() =>
                      setLightbox({
                        src: landingShots.dashboard,
                        alt: 'Painel DeskRudder com métricas de chamados e WhatsApp',
                      })
                    }
                  >
                    <figure className="overflow-hidden rounded-[1.2rem] border border-white/10">
                      <img
                        src={landingShots.dashboard}
                        alt="Painel DeskRudder com métricas de chamados e WhatsApp"
                        className="aspect-[16/10] w-full object-cover object-top"
                        loading="eager"
                        fetchPriority="high"
                      />
                    </figure>
                  </LandingShotButton>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-sky-400/20 bg-sky-400/10 p-4">
                      <p className="text-2xl font-semibold text-white">+40%</p>
                      <p className="mt-1 text-sm text-slate-300">visibilidade da fila em tempo real</p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-[#0A1628]/70 p-4">
                      <p className="text-2xl font-semibold text-white">0</p>
                      <p className="mt-1 text-sm text-slate-300">perda de conversa entre setores</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 pb-8 sm:px-8 lg:px-10">
          <div className="rounded-[1.5rem] border border-white/10 bg-gradient-to-r from-white/[0.06] via-white/[0.03] to-white/[0.05] px-6 py-5 shadow-[0_20px_60px_rgba(2,8,23,0.18)] backdrop-blur-sm sm:px-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Por que empresas escolhem o DeskRudder</p>
              <div className="flex flex-wrap gap-3 text-sm text-slate-300">
                <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1">Atendimento centralizado</span>
                <span className="rounded-full border border-white/10 bg-[#0A1628]/70 px-3 py-1">SLA e prioridade em um só painel</span>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 pb-8 sm:px-8 lg:px-10">
          <div className="rounded-[1.75rem] border border-sky-400/20 bg-gradient-to-br from-sky-500/10 via-white/[0.03] to-slate-950/80 p-6 shadow-[0_25px_70px_rgba(2,8,23,0.22)] backdrop-blur-md sm:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-2xl">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-400">Confiança operacional</p>
                <h2 className="mt-3 text-2xl font-semibold text-white sm:text-3xl">Mais controle, menos ruído e menos retrabalho para o time.</h2>
                <p className="mt-3 text-base leading-relaxed text-slate-300">
                  O DeskRudder transforma a operação em um ambiente previsível, com contexto claro, prioridades visíveis e decisões mais rápidas.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[32rem]">
                {credibilityMetrics.map((metric) => (
                  <div key={metric.label} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                    <p className="text-xl font-semibold text-white">{metric.value}</p>
                    <p className="mt-1 text-sm text-slate-400">{metric.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="valor" className="py-14 sm:py-16">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <SectionHeading
              eyebrow="O que muda na operação"
              title="Uma operação mais limpa, mais rápida e mais previsível"
              body="A solução foi pensada para dar clareza ao time, reduzir ruído e fazer o atendimento parecer um sistema profissional — e não um improviso."
            />
            <div className="mt-10 grid gap-6 lg:grid-cols-3">
              {valuePillars.map((pillar, index) => (
                <article key={pillar.title} className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-6 shadow-lg shadow-black/10 transition duration-300 hover:-translate-y-1 hover:border-sky-400/25 hover:bg-white/[0.05] before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-sky-400/70 before:to-transparent">
                  <div className="inline-flex size-11 items-center justify-center rounded-2xl border border-sky-400/20 bg-sky-500/10 text-sm font-semibold text-sky-200">
                    0{index + 1}
                  </div>
                  <h3 className="mt-4 text-xl font-semibold text-white">{pillar.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-400">{pillar.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="pb-8 sm:pb-10">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <div className="grid gap-6 lg:grid-cols-3">
              {experienceHighlights.map((item) => (
                <div key={item.title} className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-gradient-to-br from-white/[0.04] to-white/[0.02] p-6 shadow-[0_15px_45px_rgba(2,8,23,0.12)] before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-sky-400/60 before:to-transparent">
                  <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-400">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-t border-white/10 bg-[#071826]/70 py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <SectionHeading title={landingPain.title} />
            <ul className="mt-10 grid gap-6 md:grid-cols-3">
              {landingPain.items.map((item, index) => (
                <li key={item.title} className="relative overflow-hidden rounded-[1.35rem] border border-rose-400/20 bg-rose-400/10 p-6 transition duration-300 hover:-translate-y-1 hover:border-rose-400/35 before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-rose-400/60 before:to-transparent">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-300">0{index + 1}</p>
                  <h3 className="mt-3 text-lg font-semibold text-white">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.body}</p>
                </li>
              ))}
            </ul>
            <div className="mt-10 rounded-[1.5rem] border border-sky-500/25 bg-sky-500/10 px-6 py-8 sm:px-8">
              <h3 className="text-2xl font-bold text-sky-300">{landingPain.pivotTitle}</h3>
              <p className="mt-3 max-w-3xl text-base leading-relaxed text-slate-300">{landingPain.pivotBody}</p>
            </div>
          </div>
        </section>

        <section className="py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-[1.75rem] border border-rose-400/20 bg-rose-500/10 p-8 shadow-[0_20px_60px_rgba(2,8,23,0.16)]">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-300">Antes</p>
                <h3 className="mt-3 text-2xl font-semibold text-white">Operação fragmentada e reativa</h3>
                <ul className="mt-5 space-y-3 text-sm leading-relaxed text-slate-300">
                  <li>• Mensagens espalhadas por celulares e e-mails</li>
                  <li>• Falta de contexto ao transferir entre setores</li>
                  <li>• SLA e prioridades invisíveis para a gestão</li>
                </ul>
              </div>
              <div className="rounded-[1.75rem] border border-sky-400/20 bg-gradient-to-br from-sky-500/10 via-white/[0.03] to-slate-950/80 p-8 shadow-[0_20px_60px_rgba(2,8,23,0.16)]">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-300">Depois</p>
                <h3 className="mt-3 text-2xl font-semibold text-white">Fluxo único, visão clara e resposta mais certeira</h3>
                <ul className="mt-5 space-y-3 text-sm leading-relaxed text-slate-300">
                  <li>• Um painel para todos os canais e fornecedores de atendimento</li>
                  <li>• Histórico completo e responsabilidade bem definida</li>
                  <li>• Alertas e métricas para gerenciar com excelência</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section id="produto" className="scroll-mt-24 py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <SectionHeading
              eyebrow="O que você encontra"
              title="Tudo o que sua equipe precisa para atender melhor"
              body="Do canal ao prazo, o DeskRudder reúne cada etapa do atendimento para reduzir ruído, dar contexto e manter o fluxo sob controle."
            />
          </div>
          <div className="mx-auto mt-12 flex max-w-7xl flex-col gap-8 px-5 sm:px-8 lg:px-10">
            {landingShowcases.map((block, i) => {
              const reverse = i % 2 === 1
              const alt = `Painel DeskRudder — ${block.eyebrow}`
              return (
                <article
                  key={block.id}
                  id={block.id}
                  className="relative overflow-hidden grid items-center gap-8 rounded-[1.75rem] border border-white/10 bg-white/[0.035] p-6 shadow-xl shadow-black/15 transition duration-300 hover:-translate-y-1 hover:border-sky-400/25 hover:bg-white/[0.045] lg:grid-cols-2 lg:gap-12 lg:p-8 before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-sky-400/70 before:to-transparent"
                >
                  <div className={reverse ? 'lg:order-2' : ''}>
                    <p className="text-xs font-semibold uppercase tracking-[0.25em] text-sky-400">{block.eyebrow}</p>
                    <h3 className="mt-3 text-2xl font-bold tracking-tight text-white sm:text-3xl">{block.title}</h3>
                    <p className="mt-4 text-base leading-relaxed text-slate-300">{block.body}</p>
                    <ul className="mt-6 space-y-3">
                      {block.bullets.map((b) => (
                        <li key={b} className="flex gap-3 text-sm text-slate-300">
                          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-sky-400" aria-hidden />
                          <span className="leading-relaxed">{b}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className={reverse ? 'lg:order-1' : ''}>
                    <LandingShotButton
                      label={alt}
                      onOpen={() => setLightbox({ src: landingShotSrc(block.visual), alt })}
                    >
                      <LandingProductShot visual={block.visual} alt={alt} />
                    </LandingShotButton>
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <section className="border-y border-sky-500/20 bg-gradient-to-r from-sky-700/20 via-[#0B2D4A]/85 to-sky-500/20 py-14 sm:py-16">
          <div className="mx-auto max-w-3xl px-5 text-center sm:px-8">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">{landingMidCta.title}</h2>
            <p className="mt-3 text-slate-200">{landingMidCta.body}</p>
            <div className="mt-8 flex justify-center">
              <LandingContactSlot variant="section" label={landingMidCta.ctaPrimary} />
            </div>
          </div>
        </section>

        <section id="resultados" className="scroll-mt-24 py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <SectionHeading title={landingOutcomes.title} />
            <ul className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {landingOutcomes.items.map((item) => (
                <li key={item.label} className="relative overflow-hidden rounded-[1.35rem] border border-white/10 bg-white/[0.03] p-6 transition duration-300 hover:-translate-y-1 hover:border-sky-500/35 hover:bg-white/[0.05] before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-sky-400/60 before:to-transparent">
                  <h3 className="text-lg font-semibold text-sky-300">{item.label}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="border-t border-white/10 bg-[#0A1628]/70 py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <SectionHeading title={landingHowItWorks.title} />
            <ol className="mt-12 grid gap-10 md:grid-cols-3">
              {landingHowItWorks.steps.map((s) => (
                <li key={s.n} className="relative overflow-hidden rounded-[1.35rem] border border-white/10 bg-white/[0.03] p-6 transition duration-300 hover:-translate-y-1 hover:border-sky-400/25 hover:bg-white/[0.05] before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-sky-400/60 before:to-transparent">
                  <span className="text-3xl font-bold text-sky-500/45">{s.n}</span>
                  <h3 className="mt-3 text-lg font-semibold text-white">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
            <SectionHeading title={landingAudience.title} body={landingAudience.body} />
            <ul className="mt-10 grid gap-6 md:grid-cols-3">
              {landingAudience.segments.map((seg) => (
                <li key={seg.title} className="relative overflow-hidden rounded-[1.35rem] border border-sky-500/20 bg-sky-500/5 p-6 transition duration-300 hover:-translate-y-1 hover:border-sky-400/35 hover:bg-sky-500/10 before:absolute before:left-0 before:top-0 before:h-px before:w-full before:bg-gradient-to-r before:from-transparent before:via-sky-400/60 before:to-transparent">
                  <h3 className="text-lg font-semibold text-white">{seg.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{seg.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="contato" className="scroll-mt-24 border-t border-white/10 py-16 sm:py-24">
          <div className="mx-auto max-w-3xl px-5 text-center sm:px-8">
            <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-sky-400/25 bg-sky-400/10 px-3.5 py-2 text-sm text-sky-200">
              <span className="size-2 rounded-full bg-sky-400" />
              {APP_NAME}
            </div>
            <h2 className="mt-5 text-3xl font-bold tracking-tight text-white sm:text-4xl">{landingFinalCta.title}</h2>
            <p className="mt-4 text-lg text-slate-300">{landingFinalCta.body}</p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <LandingContactSlot variant="section" label={landingFinalCta.ctaPrimary} />
              <SecondaryLink to={landingHero.ctaSecondaryTo}>{landingFinalCta.ctaSecondary}</SecondaryLink>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 bg-[#050810]/80 py-10">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 sm:flex-row sm:items-end sm:justify-between sm:px-8 lg:px-10">
          <div>
            <BrandLogo variant="wordmark" size="sm" markVariant="onDark" />
            <p className="mt-2 max-w-md text-sm text-slate-500">{landingFooter.productLine}</p>
          </div>
          <div className="flex flex-col gap-2 text-sm sm:items-end">
            <Link to="/login" className="font-medium text-sky-300 hover:text-sky-200">
              {landingFooter.loginLabel}
            </Link>
            <a href={`mailto:${landingContactEmail}`} className="text-slate-400 hover:text-slate-200">
              {landingFooter.contactLabel}: {landingContactEmail}
            </a>
            <p className="text-xs text-slate-600">© {new Date().getFullYear()} {APP_NAME}</p>
          </div>
        </div>
      </footer>

      <LandingLightbox
        open={lightbox != null}
        src={lightbox?.src ?? ''}
        alt={lightbox?.alt ?? ''}
        onClose={closeLightbox}
      />

      <style>{`
        @keyframes landing-fade-up {
          from { opacity: 0; transform: translateY(18px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .landing-fade-up {
          animation: landing-fade-up 0.75s ease-out both;
        }
        .landing-shot {
          animation: landing-fade-up 0.9s ease-out both;
        }
        body {
          background-color: #071826;
        }
        @media (prefers-reduced-motion: reduce) {
          .landing-fade-up, .landing-shot { animation: none; }
        }
      `}</style>
    </MarketingLayout>
  )
}
