import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Button } from './ui/Button'
import { PONTO_AJUDA_SECOES, PONTO_AJUDA_TITULO } from '../lib/pontoAjuda'

type Props = {
  open: boolean
  onClose: () => void
}

export function PontoAjudaModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div
      className="fixed inset-0 z-[700] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ponto-ajuda-modal-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-[1px]"
        onClick={onClose}
        aria-label="Fechar ajuda"
      />
      <div className="relative max-h-[min(85vh,720px)] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-600 dark:bg-slate-900 md:max-w-2xl">
        <h2 id="ponto-ajuda-modal-title" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          {PONTO_AJUDA_TITULO}
        </h2>
        <div className="mt-4 space-y-5">
          {PONTO_AJUDA_SECOES.map((sec) => (
            <section key={sec.titulo}>
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{sec.titulo}</h3>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                {sec.paragrafos.map((p) => (
                  <li key={p.slice(0, 40)}>{p}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        <div className="mt-6 flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
