import { BRAND_ASSET_VERSION } from './tokens'

type Props = {
  className?: string
  /** Fundo escuro: usa PNG com alpha quando disponível. */
  variant?: 'default' | 'onDark'
  title?: string
}

/** Monograma oficial (PNG v2 — agente 3D no D). */
export function RudderMark({ className = '', variant = 'default', title = 'DeskRudder' }: Props) {
  const v = BRAND_ASSET_VERSION
  const src =
    variant === 'onDark' ? `/deskrudder-mark-alpha.png?v=${v}` : `/deskrudder-mark.png?v=${v}`

  return (
    <img
      src={src}
      alt={title}
      className={`object-contain ${variant === 'onDark' ? 'drop-shadow-[0_2px_16px_rgba(56,189,248,0.2)]' : ''} ${className}`.trim()}
      decoding="async"
      draggable={false}
    />
  )
}
