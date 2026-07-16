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
      ? 'inline-flex items-center justify-center rounded-xl bg-sky-500 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-sky-900/40 transition hover:bg-sky-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 focus-visible:ring-offset-2 focus-visible:ring-offset-[#071826]'
      : 'inline-flex items-center justify-center rounded-xl bg-sky-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-sky-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300'

  return (
    <a
      id={variant === 'section' ? 'contato-cta' : undefined}
      href={landingMailtoHref()}
      className={`${base} ${className}`.trim()}
      data-landing-contact-slot={variant}
    >
      {label}
    </a>
  )
}
