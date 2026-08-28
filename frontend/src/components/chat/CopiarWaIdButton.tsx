import { useState } from 'react'
import { formatWaIdExibicao } from '../../utils/masks'

type Props = {
  waId: string
  className?: string
  /** Se false, mostra o `wa_id` cru (útil em listas densas). Default: formatado (#684). */
  formatado?: boolean
}

/**
 * Número WhatsApp clicável — copia `wa_id` para a área de transferência (#831 / #684).
 * Usar `stopPropagation` para não abrir o card/link pai.
 */
export function CopiarWaIdButton({ waId, className = '', formatado = true }: Props) {
  const [copiado, setCopiado] = useState(false)
  const raw = waId.trim()
  if (!raw) return null

  return (
    <button
      type="button"
      className={`max-w-full truncate font-mono text-xs transition hover:text-cyan-700 dark:hover:text-cyan-300 ${className}`}
      title={copiado ? 'Copiado' : 'Clique para copiar o número'}
      aria-label={copiado ? 'Número copiado' : 'Copiar número do contato'}
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        void navigator.clipboard?.writeText(raw).then(() => {
          setCopiado(true)
          window.setTimeout(() => setCopiado(false), 1500)
        })
      }}
    >
      {copiado ? 'Copiado!' : formatado ? formatWaIdExibicao(raw) : raw}
    </button>
  )
}
