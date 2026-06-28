import { useEffect } from 'react'
import { Button } from '../ui/Button'
import { MODAL_OVERLAY, MODAL_PANEL_WIDE_SHELL } from '../../lib/modalPanel'
import { KbMarkdownPreview } from './KbMarkdownPreview'
import type { Kb } from '../../api/client'

type Props = {
  open: boolean
  onClose: () => void
  articleId: number
  versions: Kb.ArticleVersion[]
  loading: boolean
  onSelectVersion: (versionId: number) => void
  selectedVersion: Kb.ArticleVersionDetail | null
  loadingVersion: boolean
}

export function KbArtigoHistoricoModal({
  open,
  onClose,
  versions,
  loading,
  onSelectVersion,
  selectedVersion,
  loadingVersion,
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
    <div className={MODAL_OVERLAY} role="dialog" aria-modal="true" onClick={onClose}>
      <div className={MODAL_PANEL_WIDE_SHELL} onClick={(e) => e.stopPropagation()}>
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Histórico de versões</h2>
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
        <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[minmax(220px,280px)_1fr]">
          <div className="min-h-0 overflow-y-auto border-b border-slate-200 p-3 dark:border-slate-800 lg:border-b-0 lg:border-r">
            {loading ? (
              <p className="text-sm text-slate-500">Carregando…</p>
            ) : versions.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhuma versão registrada.</p>
            ) : (
              <ul className="space-y-1">
                {versions.map((v) => (
                  <li key={v.id}>
                    <button
                      type="button"
                      onClick={() => onSelectVersion(v.id)}
                      className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        selectedVersion?.id === v.id
                          ? 'bg-cyan-50 text-cyan-950 dark:bg-cyan-950/40 dark:text-cyan-100'
                          : 'hover:bg-slate-100 dark:hover:bg-slate-800/80'
                      }`}
                    >
                      <span className="font-medium">{v.titulo}</span>
                      <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                        {v.status} · {new Date(v.created_at).toLocaleString('pt-BR')}
                        {v.autor_nome ? ` · ${v.autor_nome}` : ''}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="min-h-0 overflow-y-auto p-4">
            {loadingVersion ? (
              <p className="text-sm text-slate-500">Carregando versão…</p>
            ) : selectedVersion ? (
              <KbMarkdownPreview markdown={selectedVersion.conteudo_markdown} />
            ) : (
              <p className="text-sm text-slate-500">Selecione uma versão para visualizar.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
