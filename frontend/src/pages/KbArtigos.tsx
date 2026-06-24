import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, kb, type Kb } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { Select } from '../components/ui/Select'
import { Input } from '../components/ui/Input'
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
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [showCats, setShowCats] = useState(false)
  const [novaCat, setNovaCat] = useState('')

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
      incluir_arquivados: statusFiltro === 'arquivado',
      offset: (page - 1) * PAGE_SIZE_PADRAO,
      limit: PAGE_SIZE_PADRAO,
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
  }, [debouncedBusca, page, statusFiltro, toast])

  useEffect(() => {
    loadCats()
  }, [loadCats])

  useEffect(() => {
    load()
  }, [load])

  async function criarCategoria() {
    if (!novaCat.trim()) return
    try {
      await kb.createCategory({ nome: novaCat.trim(), ordem: categorias.length })
      setNovaCat('')
      loadCats()
      toast.showSuccess('Categoria criada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível criar a categoria.'))
    }
  }

  async function excluirCategoria(id: number) {
    if (!window.confirm('Excluir categoria? Artigos ficarão sem categoria.')) return
    try {
      await kb.deleteCategory(id)
      loadCats()
      load()
      toast.showSuccess('Categoria excluída.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir.'))
    }
  }

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para gerenciar a base de conhecimento."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      }
      title="Base de conhecimento"
      subtitle="Manuais e artigos para consulta interna — rascunho, publicação e arquivamento."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" type="button" onClick={() => setShowCats((v) => !v)}>
            Categorias
          </Button>
          <Button type="button" onClick={() => navigate('/base-conhecimento/novo')}>
            Novo artigo
          </Button>
        </div>
      }
    >
      {showCats ? (
        <Card className="mb-4 space-y-3 p-4">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Categorias</h2>
          <div className="flex flex-wrap gap-2">
            <Input
              label="Nova categoria"
              value={novaCat}
              onChange={(e) => setNovaCat(e.target.value)}
              className="min-w-[200px] flex-1"
            />
            <div className="flex items-end">
              <Button type="button" onClick={criarCategoria}>
                Adicionar
              </Button>
            </div>
          </div>
          {categorias.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhuma categoria.</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
              {categorias.map((c) => (
                <li key={c.id} className="flex items-center justify-between gap-2 py-2">
                  <span>
                    {c.nome}{' '}
                    <span className="text-slate-500">({c.artigos_count} artigo{c.artigos_count === 1 ? '' : 's'})</span>
                  </span>
                  <Button type="button" variant="secondary" onClick={() => excluirCategoria(c.id)}>
                    Excluir
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      ) : null}

      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={(v) => {
            setBusca(v)
            setPage(1)
          }}
          placeholder="Buscar por título ou conteúdo"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <div className="w-full min-w-0 sm:w-auto sm:min-w-[180px]">
              <Select
                label="Status"
                value={statusFiltro}
                onChange={(v) => {
                  setStatusFiltro(typeof v === 'string' ? v : String(v))
                  setPage(1)
                }}
                options={Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))}
                includeEmpty
                emptyLabel="Ativos (sem arquivados)"
                placeholder="Ativos"
              />
            </div>
          }
        />
        {loading ? (
          <p className="text-slate-500">Carregando…</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500">Nenhum artigo cadastrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Título</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Categoria</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Status</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Atualizado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((item) => (
                  <tr
                    key={item.id}
                    className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50"
                    onClick={() => navigate(`/base-conhecimento/${item.id}/editar`)}
                  >
                    <td className="px-4 py-3 font-medium">{item.titulo}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{item.category_nome ?? '—'}</td>
                    <td className="px-4 py-3">{STATUS_LABEL[item.status] ?? item.status}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                      {item.updated_at ? new Date(item.updated_at).toLocaleString('pt-BR') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </ConfigListPageShell>
  )
}
