import { APP_NAME, APP_TAGLINE } from './tokens'
import { RudderMark } from './RudderMark'

type Props = {
  /** Icone + nome, nome so, lockup vertical (login) ou icone. */
  variant?: 'full' | 'mark' | 'wordmark' | 'lockup'
  /** sm = header mobile; sidebar = menu lateral expandido; md = login; lg = destaque. */
  size?: 'sm' | 'sidebar' | 'md' | 'lg'
  className?: string
  markVariant?: 'default' | 'onDark'
}

const markSizes = {
  sm: 'h-9 w-auto md:h-10',
  sidebar: 'h-11 w-auto shrink-0',
  md: 'h-10 w-auto sm:h-12',
  lg: 'h-28 w-auto max-w-full sm:h-32',
} as const

const wordmarkSizes = {
  sm: 'text-[0.95rem]',
  sidebar: 'text-[1.65rem] leading-none sm:text-[1.75rem]',
  md: 'text-2xl sm:text-3xl',
  lg: 'text-3xl sm:text-4xl',
} as const

const taglineSizes = {
  sm: 'text-[0.625rem] px-2.5 py-0.5',
  md: 'text-xs sm:text-sm px-3.5 py-1',
  lg: 'text-sm sm:text-base px-4 py-1.5',
} as const

export function BrandLogo({
  variant = 'full',
  size = 'sm',
  className = '',
  markVariant = 'default',
}: Props) {
  const onDark = markVariant === 'onDark'

  const wordmarkCompact = size !== 'sidebar'

  const wordmark = (
    <span
      className={`min-w-0 font-semibold tracking-tight ${wordmarkCompact ? 'truncate leading-tight' : 'flex-1 leading-none'} ${wordmarkSizes[size]}`}
    >
      <span className={`font-semibold ${onDark ? 'text-slate-100' : 'text-[#0B2D4A]'}`}>Desk</span>
      <span className={`font-bold ${onDark ? 'text-sky-400' : 'text-[#0284C7]'}`}>Rudder</span>
    </span>
  )

  const tagline = (
    <p
      className={`m-0 inline-flex items-center justify-center rounded-[10px] border font-medium tracking-wide ${taglineSizes[size]} ${
        onDark
          ? 'border-white/10 bg-white/[0.06] text-slate-300 shadow-inner shadow-black/20'
          : 'border-slate-200/90 bg-slate-50 text-slate-600'
      }`}
    >
      {APP_TAGLINE}
    </p>
  )

  if (variant === 'wordmark') {
    return (
      <span className={`inline-flex min-w-0 items-center ${className}`.trim()} aria-label={APP_NAME}>
        {wordmark}
      </span>
    )
  }

  if (variant === 'mark') {
    return (
      <RudderMark
        className={`shrink-0 ${markSizes[size]} ${className}`.trim()}
        variant={markVariant}
        title={APP_NAME}
      />
    )
  }

  if (variant === 'lockup') {
    const gap = size === 'lg' ? 'gap-4' : 'gap-2.5'
    return (
      <div
        className={`flex flex-col items-center ${gap} ${className}`.trim()}
        aria-label={APP_NAME}
      >
        <RudderMark className={markSizes[size]} variant={markVariant} title="" />
        {wordmark}
        {tagline}
      </div>
    )
  }

  const gap =
    size === 'lg' ? 'gap-3 sm:gap-4' : size === 'sidebar' ? 'gap-3' : size === 'md' ? 'gap-2.5' : 'gap-2'

  return (
    <span
      className={`inline-flex min-w-0 items-center ${size === 'sidebar' ? 'w-full' : ''} ${gap} ${className}`.trim()}
      aria-label={APP_NAME}
    >
      <RudderMark className={`shrink-0 ${markSizes[size]}`} variant={markVariant} title="" />
      {wordmark}
    </span>
  )
}
