const STAR_PATH =
  'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z'

type Size = 'sm' | 'md' | 'lg'

const DIM: Record<Size, number> = { sm: 14, md: 18, lg: 22 }

function EstrelaVazia({ size }: { size: Size }) {
  const dim = DIM[size]
  return (
    <svg width={dim} height={dim} viewBox="0 0 24 24" aria-hidden className="text-slate-300 dark:text-slate-600">
      <path fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" d={STAR_PATH} />
    </svg>
  )
}

function EstrelaParcial({ fill, size }: { fill: number; size: Size }) {
  const dim = DIM[size]
  const pct = `${Math.max(0, Math.min(1, fill)) * 100}%`
  return (
    <span className="relative inline-block" style={{ width: dim, height: dim }}>
      <EstrelaVazia size={size} />
      <span className="absolute inset-0 overflow-hidden" style={{ width: pct }}>
        <svg width={dim} height={dim} viewBox="0 0 24 24" aria-hidden className="text-amber-400">
          <path fill="currentColor" d={STAR_PATH} />
        </svg>
      </span>
    </span>
  )
}

type NotaEstrelasMediaProps = {
  media: number | null
  size?: Size
  className?: string
  mostrarNumero?: boolean
}

/** Exibe 5 estrelas com preenchimento parcial conforme a média (ex.: 4,3 → 4 cheias + 1 parcial). */
export function NotaEstrelasMedia({
  media,
  size = 'md',
  className = '',
  mostrarNumero = true,
}: NotaEstrelasMediaProps) {
  if (media == null) {
    return <span className={`text-2xl font-bold text-slate-400 ${className}`}>—</span>
  }

  const clamped = Math.max(0, Math.min(5, media))
  const estrelas = Array.from({ length: 5 }, (_, i) => {
    const fill = Math.max(0, Math.min(1, clamped - i))
    return fill >= 1 ? 1 : fill
  })

  const label = `${media.toFixed(1).replace('.', ',')} de 5 estrelas`

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <span className="inline-flex items-center gap-0.5" title={label} aria-label={label}>
        {estrelas.map((fill, i) =>
          fill >= 1 ? (
            <svg
              key={i}
              width={DIM[size]}
              height={DIM[size]}
              viewBox="0 0 24 24"
              aria-hidden
              className="text-amber-400"
            >
              <path fill="currentColor" d={STAR_PATH} />
            </svg>
          ) : fill > 0 ? (
            <EstrelaParcial key={i} fill={fill} size={size} />
          ) : (
            <EstrelaVazia key={i} size={size} />
          ),
        )}
      </span>
      {mostrarNumero ? (
        <span className="text-lg font-semibold text-slate-700 dark:text-slate-200">
          {media.toFixed(1).replace('.', ',')}
        </span>
      ) : null}
    </div>
  )
}
