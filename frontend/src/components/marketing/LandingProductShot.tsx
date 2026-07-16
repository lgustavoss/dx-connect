import type { LandingShowcaseId } from '../../content/landing'
import { landingShots } from '../../content/landing'

type Props = {
  visual: LandingShowcaseId
  alt: string
}

const shotByVisual: Record<LandingShowcaseId, string> = {
  chat: landingShots.chat,
  tickets: landingShots.tickets,
  sla: landingShots.sla,
  kb: landingShots.kb,
}

export function landingShotSrc(visual: LandingShowcaseId): string {
  return shotByVisual[visual]
}

/** Moldura de produto com print real (seed local) ou fallback visual. */
export function LandingProductShot({ visual, alt }: Props) {
  const src = shotByVisual[visual]
  return (
    <figure className="landing-shot group relative overflow-hidden rounded-2xl border border-white/12 bg-[#0A1628] shadow-2xl shadow-black/50">
      <div className="flex items-center gap-1.5 border-b border-white/10 bg-black/25 px-3 py-2">
        <span className="size-2 rounded-full bg-rose-400/80" aria-hidden />
        <span className="size-2 rounded-full bg-amber-400/80" aria-hidden />
        <span className="size-2 rounded-full bg-emerald-400/80" aria-hidden />
        <span className="ml-2 truncate text-[11px] text-slate-500">app.deskrudder · {visual}</span>
        <span className="ml-auto hidden text-[10px] text-slate-500 sm:inline">Clique para ampliar</span>
      </div>
      <div className="relative aspect-[16/10] overflow-hidden bg-[#071826]">
        <img
          src={src}
          alt={alt}
          className="size-full object-cover object-top transition duration-700 group-hover:scale-[1.02]"
          loading="lazy"
          decoding="async"
          onError={(e) => {
            const el = e.currentTarget
            el.style.display = 'none'
            const fallback = el.nextElementSibling
            if (fallback instanceof HTMLElement) fallback.hidden = false
          }}
        />
        <div
          hidden
          className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[#0B2D4A] to-[#071826] p-6 text-center text-sm text-slate-400"
        >
          Prévia do painel DeskRudder
        </div>
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#071826]/50 via-transparent to-transparent"
        />
      </div>
      <figcaption className="sr-only">{alt}</figcaption>
    </figure>
  )
}
