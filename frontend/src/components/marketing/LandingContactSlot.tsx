import { landingMailtoHref } from '../../content/landing'

type Variant = 'hero' | 'section'

type Props = {
  variant?: Variant
  label: string
  className?: string
}

/**
 * Slot de contato comercial (#516).
 * v1 (#515): mailto institucional — o canal B2B dedicado substitui este conteúdo depois.
 */
export function LandingContactSlot({ variant = 'hero', label, className = '' }: Props) {
  const base =
    variant === 'hero'
      ? 'group inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sky-500 via-sky-400 to-cyan-400 px-6 py-3.5 text-sm font-semibold text-white shadow-[0_16px_40px_rgba(14,165,233,0.25)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_20px_50px_rgba(14,165,233,0.32)] focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 focus-visible:ring-offset-2 focus-visible:ring-offset-[#071826]'
      : 'group inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sky-500 via-sky-400 to-cyan-400 px-6 py-3 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(14,165,233,0.2)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_35px_rgba(14,165,233,0.28)] focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300'

  return (
    <a
      id={variant === 'section' ? 'contato-cta' : undefined}
      href={landingMailtoHref()}
      className={`${base} ${className}`.trim()}
      data-landing-contact-slot={variant}
    >
      <span>{label}</span>
      <svg viewBox="0 0 20 20" fill="none" className="size-4 transition duration-200 group-hover:translate-x-0.5" aria-hidden>
        <path d="M4 10h12M12 5l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </a>
  )
}
