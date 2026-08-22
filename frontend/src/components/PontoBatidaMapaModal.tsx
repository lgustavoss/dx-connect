import { linkMapaOsm } from '../lib/pontoFormat'

type Props = {
  open: boolean
  onClose: () => void
  latitude: number
  longitude: number
  titulo?: string
  subtitulo?: string
  raioMetros?: number | null
}

function embedUrl(lat: number, lon: number, delta = 0.006): string {
  const bbox = `${lon - delta},${lat - delta},${lon + delta},${lat + delta}`
  return `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(bbox)}&layer=mapnik&marker=${lat}%2C${lon}`
}

export function PontoBatidaMapaModal({
  open,
  onClose,
  latitude,
  longitude,
  titulo = 'Localização da batida',
  subtitulo,
  raioMetros,
}: Props) {
  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={titulo}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-700">
          <div>
            <p className="font-semibold text-slate-900 dark:text-slate-50">{titulo}</p>
            {subtitulo ? (
              <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">{subtitulo}</p>
            ) : null}
            <p className="mt-1 font-mono text-xs text-slate-500">
              {latitude.toFixed(5)}, {longitude.toFixed(5)}
              {raioMetros != null ? ` · raio ref. ${raioMetros} m` : ''}
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg px-2 py-1 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            onClick={onClose}
          >
            Fechar
          </button>
        </div>
        <iframe
          title={titulo}
          className="h-72 w-full border-0"
          loading="lazy"
          src={embedUrl(latitude, longitude)}
        />
        <div className="border-t border-slate-200 px-4 py-2 text-right dark:border-slate-700">
          <a
            className="text-sm text-cyan-700 underline dark:text-cyan-300"
            href={linkMapaOsm(latitude, longitude)}
            target="_blank"
            rel="noreferrer"
          >
            Abrir no OpenStreetMap
          </a>
        </div>
      </div>
    </div>
  )
}
