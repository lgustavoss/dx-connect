import { useState } from 'react'

type Props = {
  nome?: string | null
  fotoUrl?: string | null
  className?: string
  /** Classes do círculo quando só há inicial */
  fallbackClassName?: string
  /** Clique na foto (só quando há URL válida) — ex. lightbox (#681). */
  onFotoClick?: () => void
}

/** Avatar do contato WhatsApp com fallback para inicial (#630). */
export function WhatsappAvatar({
  nome,
  fotoUrl,
  className = 'h-10 w-10',
  fallbackClassName = 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200',
  onFotoClick,
}: Props) {
  const [broke, setBroke] = useState(false)
  const inicial = (nome || '?').trim().charAt(0).toUpperCase() || '?'
  if (fotoUrl && !broke) {
    const img = (
      <img
        src={fotoUrl}
        alt=""
        className={`${className} shrink-0 rounded-full object-cover ${onFotoClick ? 'cursor-zoom-in' : ''}`}
        referrerPolicy="no-referrer"
        onError={() => setBroke(true)}
      />
    )
    if (onFotoClick) {
      return (
        <button
          type="button"
          onClick={onFotoClick}
          className="shrink-0 rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          aria-label="Ver foto do contato"
        >
          {img}
        </button>
      )
    }
    return img
  }
  return (
    <div
      className={`${className} flex shrink-0 items-center justify-center rounded-full text-sm font-bold ${fallbackClassName}`}
      aria-hidden
    >
      {inicial}
    </div>
  )
}
