import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { ePdfDocumento } from '../../lib/fileTypeIcon'

type Props = {
  url: string
  nome?: string | null
  mime?: string | null
  onClose: () => void
}

/** Overlay de documento com Voltar/Fechar — evita blob: na WebView (#1067 / #S202608-0013). */
export function DocumentoPreviewLightbox({ url, nome, mime, onClose }: Props) {
  const pdf = ePdfDocumento(nome, mime)
  const titulo = (nome || '').trim() || (pdf ? 'PDF' : 'Documento')
  const downloadName = (nome || '').trim() || (pdf ? 'documento.pdf' : 'arquivo')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.preventDefault()
      e.stopImmediatePropagation()
      onClose()
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [onClose])

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex flex-col bg-black/90 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-label={titulo}
      onClick={onClose}
    >
      <div
        className="flex shrink-0 items-center gap-2 border-b border-white/10 bg-black/40 px-3 py-3 sm:px-4"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="inline-flex h-12 min-w-[6.5rem] items-center justify-center gap-1 rounded-xl bg-white px-4 text-sm font-semibold text-slate-900 shadow-sm touch-manipulation hover:bg-slate-100"
          onClick={onClose}
        >
          <span aria-hidden>←</span>
          Voltar
        </button>
        <p className="min-w-0 flex-1 truncate text-sm font-medium text-white">{titulo}</p>
        <a
          href={url}
          download={downloadName}
          className="inline-flex h-12 shrink-0 items-center justify-center rounded-xl bg-cyan-600 px-4 text-sm font-bold text-white touch-manipulation hover:bg-cyan-700"
        >
          Baixar
        </a>
      </div>
      <div className="flex min-h-0 flex-1 items-stretch justify-center p-3 sm:p-4">
        {pdf ? (
          <iframe
            title={titulo}
            src={url}
            className="h-full min-h-[70vh] w-full max-w-5xl rounded-lg bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <div
            className="flex h-full min-h-[50vh] max-w-lg flex-col items-center justify-center gap-3 rounded-lg bg-white/5 px-4 text-center text-sm text-white/90"
            onClick={(e) => e.stopPropagation()}
          >
            <p>Pré-visualização disponível só para PDF. Use Baixar para abrir o arquivo.</p>
            <button
              type="button"
              className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-slate-100"
              onClick={onClose}
            >
              Voltar à conversa
            </button>
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
