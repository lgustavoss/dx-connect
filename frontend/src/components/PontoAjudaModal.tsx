import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Button } from './ui/Button'
import {
  PONTO_AJUDA_TITULO,
  secoesAjudaPonto,
  type PontoAjudaAudiencia,
} from '../lib/pontoAjuda'

type Props = {
  open: boolean
  onClose: () => void
  audiencia?: PontoAjudaAudiencia
}

export function PontoAjudaModal({ open, onClose, audiencia = 'colaborador' }: Props) {
  const secoes = secoesAjudaPonto(audiencia)

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
      <div className="relative max-h-[min(85vh,720px)] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-600 dark:bg-slate-900 md:max-w-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2
              id="ponto-ajuda-modal-title"
              className="text-lg font-semibold text-slate-900 dark:text-slate-100"
            >
              {PONTO_AJUDA_TITULO}
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {audiencia === 'admin'
                ? 'Resumo para quem gerencia a equipe'
                : 'Resumo rápido para o dia a dia'}
            </p>
          </div>
          <Button type="button" variant="ghost" onClick={onClose} aria-label="Fechar">
            Fechar
          </Button>
        </div>
        <div className="mt-5 space-y-5">
          {secoes.map((sec) => (
            <section key={sec.titulo}>
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{sec.titulo}</h3>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                {sec.paragrafos.map((p) => (
                  <li key={p.slice(0, 48)}>{p}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  )
}
