import { useEffect, useId, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

type Props = {
  src: string
  alt: string
  open: boolean
  onClose: () => void
}

/** Lightbox de print da landing — Escape / clique fora / botão fechar. */
export function LandingLightbox({ src, alt, open, onClose }: Props) {
  const titleId = useId()

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const root = document.querySelector('[data-landing-scroll-root]')
    const prevOverflow = root instanceof HTMLElement ? root.style.overflowY : ''
    if (root instanceof HTMLElement) root.style.overflowY = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      if (root instanceof HTMLElement) root.style.overflowY = prevOverflow
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm sm:p-8"
      onClick={onClose}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 rounded-lg bg-white/10 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/20"
      >
        Fechar
      </button>
      <figure
        className="max-h-[min(92dvh,920px)] w-full max-w-6xl overflow-auto rounded-xl border border-white/15 bg-[#0A1628] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <figcaption id={titleId} className="border-b border-white/10 px-4 py-3 text-sm text-slate-300">
          {alt}
        </figcaption>
        <img src={src} alt={alt} className="mx-auto block h-auto max-w-full" />
      </figure>
    </div>,
    document.body,
  )
}

export function LandingShotButton({
  children,
  onOpen,
  label,
}: {
  children: ReactNode
  onOpen: () => void
  label: string
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="block w-full cursor-zoom-in rounded-2xl text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#071826]"
      aria-label={`Ampliar: ${label}`}
    >
      {children}
    </button>
  )
}
