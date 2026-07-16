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
import { MarketingLayout } from './MarketingLayout'

function SecondaryLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center justify-center rounded-xl border border-white/20 bg-white/5 px-6 py-3.5 text-sm font-semibold text-slate-100 backdrop-blur-sm transition hover:border-white/35 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60"
    >
      {children}
    </Link>
  )
}

function SectionHeading({
  eyebrow,
  title,
  body,
}: {
  eyebrow?: string
  title: string
  body?: string
}) {
  return (
    <div className="max-w-3xl">
      {eyebrow ? (
        <p className="mb-3 text-xs font-semibold tracking-[0.2em] text-sky-400 uppercase">{eyebrow}</p>
      ) : null}
      <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">{title}</h2>
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
  // Evita hash na URL “prender” o foco sem scroll no container do app
  if (window.history.replaceState) {
    window.history.replaceState(null, '', `#${id}`)
  }
}

type LightboxState = { src: string; alt: string } | null

export function LandingPage() {
  const [lightbox, setLightbox] = useState<LightboxState>(null)
  const closeLightbox = useCallback(() => setLightbox(null), [])

  return (
    <MarketingLayout>
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#071826]/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
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
              className="rounded-lg px-3 py-2 text-sm font-semibold text-sky-300 transition hover:text-sky-200"
            >
              {landingHero.ctaSecondary}
            </Link>
            <LandingContactSlot
              variant="hero"
              label="Ver demonstração"
              className="!px-4 !py-2 text-xs sm:text-sm"
            />
          </nav>
        </div>
      </header>

      <main>
        <section className="relative mx-auto flex min-h-[calc(100dvh-5.5rem)] w-full max-w-6xl flex-col justify-center px-5 pb-14 pt-8 sm:px-8 sm:pb-16">
          <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-12 xl:gap-16">
            <div className="landing-fade-up min-w-0">
              <p className="mb-5 text-sm font-medium tracking-[0.18em] text-sky-300/90 uppercase">
                {landingHero.brand}
                <span className="mx-2 text-slate-500">·</span>
                <span className="normal-case tracking-normal text-slate-400">{landingHero.tagline}</span>
              </p>
              <h1 className="text-[2.15rem] font-bold leading-[1.12] tracking-tight text-white sm:text-5xl lg:text-[3.15rem] lg:leading-[1.1]">
                {landingHero.titleLines.map((line) => (
                  <span key={line} className="block">
                    {line}
                  </span>
                ))}
              </h1>
              <p className="mt-6 max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">
                {landingHero.subtitle}
              </p>
              <div className="mt-9 flex flex-wrap items-center gap-3">
                <LandingContactSlot variant="hero" label={landingHero.ctaPrimary} />
                <SecondaryLink to={landingHero.ctaSecondaryTo}>{landingHero.ctaSecondary}</SecondaryLink>
              </div>
              <p className="mt-6 max-w-lg text-sm leading-relaxed text-slate-500">{landingHero.trustLine}</p>
            </div>

            <div className="landing-shot min-w-0 lg:justify-self-stretch">
              <LandingShotButton
                label="Painel DeskRudder"
                onOpen={() =>
                  setLightbox({
                    src: landingShots.dashboard,
                    alt: 'Painel DeskRudder com métricas de chamados e WhatsApp',
                  })
                }
              >
                <figure className="overflow-hidden rounded-2xl border border-white/12 shadow-2xl shadow-black/50 ring-1 ring-sky-400/15">
                  <img
                    src={landingShots.dashboard}
                    alt="Painel DeskRudder com métricas de chamados e WhatsApp"
                    className="aspect-[16/10] w-full object-cover object-top"
                    loading="eager"
                    fetchPriority="high"
                  />
                </figure>
              </LandingShotButton>
              <p className="mt-3 text-center text-xs text-slate-500 lg:text-left">
                Clique na imagem para ampliar
              </p>
            </div>
          </div>
        </section>

        <section className="border-t border-white/10 bg-[#071826]/70 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-5 sm:px-8">
            <SectionHeading title={landingPain.title} />
            <ul className="mt-10 grid gap-6 md:grid-cols-3">
              {landingPain.items.map((item) => (
                <li key={item.title} className="border-l-2 border-rose-400/50 pl-4">
                  <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.body}</p>
                </li>
              ))}
            </ul>
            <div className="mt-12 rounded-2xl border border-sky-500/25 bg-sky-500/5 px-6 py-8 sm:px-8">
              <h3 className="text-2xl font-bold text-sky-300">{landingPain.pivotTitle}</h3>
              <p className="mt-3 max-w-3xl text-base leading-relaxed text-slate-300">
                {landingPain.pivotBody}
              </p>
            </div>
          </div>
        </section>

        <section className="py-14 sm:py-16">
          <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 sm:px-8 lg:grid-cols-2">
            <div>
              <SectionHeading
                eyebrow="Na prática"
                title="Veja o painel que sua equipe vai usar"
                body="Prints reais do sistema (com dados de demonstração): fila, chamados, chat e conhecimento. Clique na imagem para ampliar."
              />
              <div className="mt-6">
                <LandingContactSlot variant="section" label="Quero ver na prática" />
              </div>
            </div>
            <LandingShotButton
              label="Dashboard DeskRudder"
              onOpen={() =>
                setLightbox({
                  src: landingShots.dashboard,
                  alt: 'Painel DeskRudder com métricas de chamados e WhatsApp',
                })
              }
            >
              <figure className="overflow-hidden rounded-2xl border border-white/12 shadow-2xl shadow-black/40">
                <img
                  src={landingShots.dashboard}
                  alt="Painel DeskRudder com métricas de chamados e WhatsApp"
                  className="w-full object-cover object-top"
                  loading="lazy"
                />
              </figure>
            </LandingShotButton>
          </div>
        </section>

        <section id="produto" className="scroll-mt-24 border-t border-white/10 py-6 sm:py-10">
          <div className="mx-auto max-w-6xl px-5 sm:px-8">
            <SectionHeading
              eyebrow="O que você encontra"
              title="Tudo para gerir o suporte num só lugar"
              body="Sem promessa de roadmap. Abaixo está o que o DeskRudder já entrega hoje para centralizar o atendimento da sua empresa."
            />
          </div>
          <div className="mx-auto mt-12 flex max-w-6xl flex-col gap-20 px-5 sm:px-8 sm:gap-28">
            {landingShowcases.map((block, i) => {
              const reverse = i % 2 === 1
              const alt = `Painel DeskRudder — ${block.eyebrow}`
              return (
                <article
                  key={block.id}
                  id={block.id}
                  className="grid items-center gap-10 lg:grid-cols-2 lg:gap-14"
                >
                  <div className={reverse ? 'lg:order-2' : ''}>
                    <p className="text-xs font-semibold tracking-[0.18em] text-sky-400 uppercase">
                      {block.eyebrow}
                    </p>
                    <h3 className="mt-3 text-2xl font-bold tracking-tight text-white sm:text-3xl">
                      {block.title}
                    </h3>
                    <p className="mt-4 text-base leading-relaxed text-slate-300">{block.body}</p>
                    <ul className="mt-6 space-y-3">
                      {block.bullets.map((b) => (
                        <li key={b} className="flex gap-3 text-sm text-slate-300">
                          <span
                            className="mt-1.5 size-1.5 shrink-0 rounded-full bg-sky-400"
                            aria-hidden
                          />
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

        <section className="mt-16 border-y border-sky-500/20 bg-gradient-to-r from-sky-700/25 via-[#0B2D4A]/80 to-sky-500/20 py-14 sm:py-16">
          <div className="mx-auto max-w-3xl px-5 text-center sm:px-8">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">{landingMidCta.title}</h2>
            <p className="mt-3 text-slate-200">{landingMidCta.body}</p>
            <div className="mt-8 flex justify-center">
              <LandingContactSlot variant="section" label={landingMidCta.ctaPrimary} />
            </div>
          </div>
        </section>

        <section id="resultados" className="scroll-mt-24 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-5 sm:px-8">
            <SectionHeading title={landingOutcomes.title} />
            <ul className="mt-10 grid gap-6 sm:grid-cols-2">
              {landingOutcomes.items.map((item) => (
                <li
                  key={item.label}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition hover:border-sky-500/35"
                >
                  <h3 className="text-xl font-semibold text-sky-300">{item.label}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="border-t border-white/10 bg-[#0A1628]/70 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-5 sm:px-8">
            <SectionHeading title={landingHowItWorks.title} />
            <ol className="mt-12 grid gap-10 md:grid-cols-3">
              {landingHowItWorks.steps.map((s) => (
                <li key={s.n}>
                  <span className="text-3xl font-bold text-sky-500/45">{s.n}</span>
                  <h3 className="mt-3 text-lg font-semibold text-white">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-5 sm:px-8">
            <SectionHeading title={landingAudience.title} body={landingAudience.body} />
            <ul className="mt-10 grid gap-6 md:grid-cols-3">
              {landingAudience.segments.map((seg) => (
                <li key={seg.title} className="border-t border-sky-500/40 pt-5">
                  <h3 className="text-lg font-semibold text-white">{seg.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{seg.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="contato" className="scroll-mt-24 border-t border-white/10 py-16 sm:py-24">
          <div className="mx-auto max-w-3xl px-5 text-center sm:px-8">
            <p className="text-sm font-medium tracking-[0.2em] text-sky-400 uppercase">{APP_NAME}</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              {landingFinalCta.title}
            </h2>
            <p className="mt-4 text-lg text-slate-300">{landingFinalCta.body}</p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <LandingContactSlot variant="section" label={landingFinalCta.ctaPrimary} />
              <SecondaryLink to={landingHero.ctaSecondaryTo}>{landingFinalCta.ctaSecondary}</SecondaryLink>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 bg-[#050810]/80 py-10">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 sm:flex-row sm:items-end sm:justify-between sm:px-8">
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
            <p className="text-xs text-slate-600">
              © {new Date().getFullYear()} {APP_NAME}
            </p>
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
        @media (prefers-reduced-motion: reduce) {
          .landing-fade-up, .landing-shot { animation: none; }
        }
      `}</style>
    </MarketingLayout>
  )
}
