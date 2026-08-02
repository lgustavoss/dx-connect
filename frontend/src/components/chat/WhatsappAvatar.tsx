import { useState } from 'react'

type Props = {
  nome?: string | null
  fotoUrl?: string | null
  className?: string
  /** Classes do círculo quando só há inicial */
  fallbackClassName?: string
}

/** Avatar do contacto WhatsApp com fallback para inicial (#630). */
export function WhatsappAvatar({
  nome,
  fotoUrl,
  className = 'h-10 w-10',
  fallbackClassName = 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-200',
}: Props) {
  const [broke, setBroke] = useState(false)
  const inicial = (nome || '?').trim().charAt(0).toUpperCase() || '?'
  if (fotoUrl && !broke) {
    return (
      <img
        src={fotoUrl}
        alt=""
        className={`${className} shrink-0 rounded-full object-cover`}
        referrerPolicy="no-referrer"
        onError={() => setBroke(true)}
      />
    )
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
