import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, kb, type Kb } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { KbListaFiltros, KB_PAGE_SIZE } from '../components/kb/KbListaFiltros'
import { KbArtigoPreviewModal } from '../components/kb/KbArtigoPreviewModal'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

const STATUS_LABEL: Record<string, string> = {
  rascunho: 'Rascunho',
  publicado: 'Publicado',
  arquivado: 'Arquivado',
}

export function KbArtigosPage({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<Kb.ArticleBrief[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [categoryFiltro, setCategoryFiltro] = useState('')
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewArtigo, setPreviewArtigo] = useState<Kb.Article | null>(null)
  const [publicandoId, setPublicandoId] = useState<number | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  const loadCats = useCallback(() => {
    kb.listCategories()
      .then(setCategorias)
      .catch(() => setCategorias([]))
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    kb.listArticles({
      busca: debouncedBusca || undefined,
      status: statusFiltro || undefined,
      category_id: categoryFiltro ? Number(categoryFiltro) : undefined,
      incluir_arquivados: statusFiltro === 'arquivado',
      offset: (page - 1) * KB_PAGE_SIZE,
      limit: KB_PAGE_SIZE,
      ordenar_por: 'updated_at',
      ordem: 'desc',
    })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .catch((err) => {
        setList([])
        setTotal(0)
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os artigos.'))
      })
      .finally(() => setLoading(false))
  }, [categoryFiltro, debouncedBusca, page, statusFiltro, toast])

  useEffect(() => {
    loadCats()
  }, [loadCats])

  useEffect(() => {
    load()
  }, [load])

  async function abrirPreview(item: Kb.ArticleBrief) {
    setPreviewOpen(true)
    setPreviewLoading(true)
    setPreviewArtigo(null)
    try {
      const full = await kb.getArticle(item.id)
      setPreviewArtigo(full)
    } catch (err) {
      setPreviewOpen(false)
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o artigo.'))
    } finally {
      setPreviewLoading(false)
    }
  }

  async function publicarDaLista(item: Kb.ArticleBrief) {
    if (item.status === 'publicado') return
    if (!window.confirm(`Publicar «${item.titulo}»? O manual ficará disponível para a equipe em Ajuda → Consultar.`)) return
    setPublicandoId(item.id)
    try {
      await kb.publishArticle(item.id)
      toast.showSuccess('Artigo publicado.')
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível publicar.'))
    } finally {
      setPublicandoId(null)
    }
  }

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para gerenciar os manuais."
          voltarPara="/ajuda/consultar"
          voltarLabel="Voltar para Ajuda"
        />
      }
      title="Artigos"
      subtitle="Rascunho, publicação e arquivamento de manuais."
      actions={
        <Button type="button" onClick={() => navigate('/ajuda/artigos/novo')}>
          Novo artigo
        </Button>
      }
    >
      <Card className="p-4 sm:p-5">
        <KbListaFiltros
          busca={busca}
          onBuscaChange={(v) => {
            setBusca(v)
            setPage(1)
          }}
          buscaPlaceholder="Buscar por título ou conteúdo…"
          categoryId={categoryFiltro}
          onCategoryChange={(v) => {
            setCategoryFiltro(v)
            setPage(1)
          }}
          categorias={categorias}
          disabled={loading}
          statusId={statusFiltro}
          onStatusChange={(v) => {
            setStatusFiltro(v)
            setPage(1)
          }}
          statusOptions={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
          paginacao={{ page, total, onPageChange: setPage, disabled: loading }}
        />

        {loading ? (
          <p className="text-slate-500">Carregando…</p>
        ) : list.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">Nenhum artigo encontrado.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200/90 dark:border-slate-700/80">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Título</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Categoria</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Status</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Atualizado</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-medium">
                      {item.titulo}
                      {item.interno_only ? (
                        <span className="ml-2 rounded bg-slate-200/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                          Só equipe
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{item.category_nome ?? '—'}</td>
                    <td className="px-4 py-3">{STATUS_LABEL[item.status] ?? item.status}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                      {item.updated_at ? new Date(item.updated_at).toLocaleString('pt-BR') : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap justify-end gap-2">
                        <Button type="button" variant="secondary" onClick={() => abrirPreview(item)}>
                          Visualizar
                        </Button>
                        {item.status === 'rascunho' ? (
                          <Button
                            type="button"
                            loading={publicandoId === item.id}
                            onClick={() => publicarDaLista(item)}
                          >
                            Publicar
                          </Button>
                        ) : null}
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => navigate(`/ajuda/artigos/${item.id}/editar`)}
                        >
                          Editar
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <KbArtigoPreviewModal
        open={previewOpen}
        onClose={() => {
          setPreviewOpen(false)
          setPreviewArtigo(null)
        }}
        titulo={previewArtigo?.titulo ?? ''}
        categoryNome={previewArtigo?.category_nome}
        statusLabel={
          previewArtigo ? (STATUS_LABEL[previewArtigo.status] ?? previewArtigo.status) : undefined
        }
        conteudoMarkdown={previewArtigo?.conteudo_markdown ?? ''}
        loading={previewLoading}
        footer={
          previewArtigo ? (
            <>
              {previewArtigo.status === 'rascunho' ? (
                <Button
                  type="button"
                  loading={publicandoId === previewArtigo.id}
                  onClick={async () => {
                    await publicarDaLista(previewArtigo)
                    setPreviewOpen(false)
                    setPreviewArtigo(null)
                  }}
                >
                  Publicar
                </Button>
              ) : null}
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setPreviewOpen(false)
                  navigate(`/ajuda/artigos/${previewArtigo.id}/editar`)
                }}
              >
                Editar
              </Button>
            </>
          ) : null
        }
      />
    </ConfigListPageShell>
  )
}
