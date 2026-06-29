import { useEffect, useState } from 'react'
import { kb, type Kb } from '../../api/client'
import { KbArtigoPreviewModal } from './KbArtigoPreviewModal'

type Props = {
  motivoId?: number | ''
  naturezaId?: number | ''
  className?: string
}

export function KbSugestoesMotivo({ motivoId, naturezaId, className = '' }: Props) {
  const [itens, setItens] = useState<Kb.ArticleBrief[]>([])
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<Kb.Article | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)

  useEffect(() => {
    if (motivoId === '' && naturezaId === '') {
      setItens([])
      return
    }
    const params: { motivo_id?: number; natureza_id?: number } = {}
    if (motivoId !== '') params.motivo_id = Number(motivoId)
    else if (naturezaId !== '') params.natureza_id = Number(naturezaId)
    else {
      setItens([])
      return
    }
    let cancelled = false
    setLoading(true)
    kb.suggestions(params)
      .then((rows) => {
        if (!cancelled) setItens(rows)
      })
      .catch(() => {
        if (!cancelled) setItens([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [motivoId, naturezaId])

  async function abrirArtigo(id: number) {
    setLoadingPreview(true)
    try {
      const full = await kb.getPublicado(id)
      setPreview(full)
    } catch {
      setPreview(null)
    } finally {
      setLoadingPreview(false)
    }
  }

  if (motivoId === '' && naturezaId === '') return null
  if (!loading && itens.length === 0) return null

  return (
    <>
      <div
        className={`rounded-xl border border-cyan-200/80 bg-cyan-50/60 px-3 py-2.5 dark:border-cyan-900/50 dark:bg-cyan-950/30 ${className}`.trim()}
      >
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-cyan-800 dark:text-cyan-200">
          Manuais sugeridos
        </p>
        {loading ? (
          <p className="text-sm text-slate-600 dark:text-slate-400">Carregando sugestões…</p>
        ) : (
          <ul className="space-y-1">
            {itens.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => void abrirArtigo(item.id)}
                  className="w-full rounded-lg px-2 py-1.5 text-left text-sm font-medium text-cyan-900 hover:bg-cyan-100/80 dark:text-cyan-100 dark:hover:bg-cyan-900/40"
                >
                  {item.titulo}
                  {item.interno_only ? (
                    <span className="ml-1.5 text-[10px] font-semibold uppercase text-slate-500">equipe</span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <KbArtigoPreviewModal
        open={preview != null}
        onClose={() => setPreview(null)}
        titulo={preview?.titulo ?? ''}
        categoryNome={preview?.category_nome}
        conteudoMarkdown={preview?.conteudo_markdown ?? ''}
        loading={loadingPreview}
      />
    </>
  )
}
