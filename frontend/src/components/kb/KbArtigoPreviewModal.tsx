import { useEffect, type ReactNode } from 'react'
import { Button } from '../ui/Button'
import { MODAL_OVERLAY, MODAL_PANEL_WIDE_SHELL } from '../../lib/modalPanel'
import { KbMarkdownPreview } from './KbMarkdownPreview'

type Props = {
  open: boolean
  onClose: () => void
  titulo: string
  categoryNome?: string | null
  statusLabel?: string
  conteudoMarkdown: string
  loading?: boolean
  footer?: ReactNode
}

export function KbArtigoPreviewModal({
  open,
  onClose,
  titulo,
  categoryNome,
  statusLabel,
  conteudoMarkdown,
  loading,
  footer,
}: Props) {
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className={MODAL_OVERLAY}
      role="dialog"
      aria-modal="true"
      aria-labelledby="kb-artigo-preview-title"
      onClick={onClose}
    >
      <div className={MODAL_PANEL_WIDE_SHELL} onClick={(e) => e.stopPropagation()}>
        <div className="shrink-0 border-b border-slate-200 px-5 py-4 dark:border-slate-700">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Pré-visualização
              </p>
              <h2 id="kb-artigo-preview-title" className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-50">
                {titulo || 'Sem título'}
              </h2>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
                {categoryNome ? <span>{categoryNome}</span> : null}
                {statusLabel ? <span>{statusLabel}</span> : null}
              </div>
            </div>
            <Button type="button" variant="secondary" onClick={onClose}>
              Fechar
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <p className="text-sm text-slate-500">Carregando…</p>
          ) : (
            <KbMarkdownPreview markdown={conteudoMarkdown} />
          )}
        </div>

        {footer ? (
          <div className="flex shrink-0 flex-wrap justify-end gap-2 border-t border-slate-200 px-5 py-4 dark:border-slate-700">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}
