import { useCallback, useEffect, useState } from 'react'
import { ApiError, kb, type Kb } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { MODAL_PANEL_COMPACT } from '../lib/modalPanel'
import {
  kbCategoriasEmArvore,
  kbCategoriasPaiOpcoes,
  kbCategoriasRaiz,
} from '../lib/kbCategorias'

type FormState = {
  nome: string
  ordem: string
  parent_id: string
}

const emptyForm = (): FormState => ({ nome: '', ordem: '0', parent_id: '' })

export function KbCategoriasPage({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [categorias, setCategorias] = useState<Kb.Category[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [saving, setSaving] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm())
  const [dragId, setDragId] = useState<number | null>(null)
  const [reordering, setReordering] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    kb.listCategories()
      .then(setCategorias)
      .catch((err) => {
        setCategorias([])
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar as categorias.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  function abrirNovo(parentId?: number) {
    setEditId(null)
    setForm({
      nome: '',
      ordem: String(categorias.length),
      parent_id: parentId != null ? String(parentId) : '',
    })
    setModalOpen(true)
  }

  function abrirEditar(cat: Kb.Category) {
    setEditId(cat.id)
    setForm({
      nome: cat.nome,
      ordem: String(cat.ordem),
      parent_id: cat.parent_id != null ? String(cat.parent_id) : '',
    })
    setModalOpen(true)
  }

  function fecharModal() {
    setModalOpen(false)
    setEditId(null)
    setForm(emptyForm())
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    if (!form.nome.trim()) return
    setSaving(true)
    const payload = {
      nome: form.nome.trim(),
      ordem: Number(form.ordem) || 0,
      parent_id: form.parent_id ? Number(form.parent_id) : null,
    }
    try {
      if (editId != null) {
        await kb.updateCategory(editId, payload)
        toast.showSuccess('Categoria atualizada.')
      } else {
        await kb.createCategory(payload)
        toast.showSuccess('Categoria criada.')
      }
      fecharModal()
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a categoria.'))
    } finally {
      setSaving(false)
    }
  }

  function irmaos(categoria: Kb.Category) {
    return categorias
      .filter((c) => c.parent_id === categoria.parent_id)
      .sort((a, b) => a.ordem - b.ordem || a.id - b.id)
  }

  async function soltarEm(targetId: number) {
    if (dragId == null || dragId === targetId || reordering) return
    const dragged = categorias.find((c) => c.id === dragId)
    const target = categorias.find((c) => c.id === targetId)
    if (!dragged || !target || dragged.parent_id !== target.parent_id) return
    const siblings = irmaos(dragged)
    const without = siblings.filter((s) => s.id !== dragId)
    const targetIdx = without.findIndex((s) => s.id === targetId)
    if (targetIdx < 0) return
    without.splice(targetIdx, 0, dragged)
    const items = without.map((s, i) => ({ id: s.id, ordem: i }))
    setReordering(true)
    try {
      await kb.reorderCategories(items)
      toast.showSuccess('Ordem atualizada.')
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível reordenar.'))
    } finally {
      setReordering(false)
      setDragId(null)
    }
  }

  async function excluir(cat: Kb.Category) {
    const temFilhos = categorias.some((c) => c.parent_id === cat.id)
    const msg = temFilhos
      ? 'Esta categoria possui subcategorias. Exclua-as primeiro.'
      : `Excluir «${cat.nome}»? Artigos vinculados ficarão sem categoria.`
    if (!window.confirm(msg)) return
    if (temFilhos) return
    try {
      await kb.deleteCategory(cat.id)
      toast.showSuccess('Categoria excluída.')
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir.'))
    }
  }

  const paisDisponiveis = kbCategoriasRaiz(categorias).filter((c) => c.id !== editId)
  const arvore = kbCategoriasEmArvore(categorias)

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para gerenciar categorias."
          voltarPara="/ajuda/consultar"
          voltarLabel="Voltar para Ajuda"
        />
      }
      title="Categorias"
      subtitle="Organize os manuais em categorias. Arraste pelo ícone ≡ para mudar a ordem."
      actions={
        <Button type="button" onClick={() => abrirNovo()}>
          Nova categoria
        </Button>
      }
    >
      <Card>
        {loading ? (
          <p className="text-slate-500">Carregando…</p>
        ) : arvore.length === 0 ? (
          <p className="text-slate-500">Nenhuma categoria cadastrada.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="w-10 px-2 py-3" aria-label="Ordenar" />
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Nome</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Artigos</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500">Ordem</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {arvore.map(({ categoria, depth }) => (
                  <tr
                    key={categoria.id}
                    className={`hover:bg-slate-50/80 dark:hover:bg-white/40 ${dragId === categoria.id ? 'opacity-60' : ''}`}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => void soltarEm(categoria.id)}
                  >
                    <td className="px-2 py-3 text-center">
                      <button
                        type="button"
                        draggable={!reordering}
                        onDragStart={() => setDragId(categoria.id)}
                        onDragEnd={() => setDragId(null)}
                        className="cursor-grab rounded px-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 active:cursor-grabbing dark:hover:bg-slate-800"
                        aria-label={`Reordenar ${categoria.nome}`}
                        title="Arrastar para reordenar"
                      >
                        ≡
                      </button>
                    </td>
                    <td className="px-4 py-3 font-medium">
                      <span style={{ paddingLeft: depth * 20 }} className="inline-block">
                        {depth === 1 ? <span className="text-slate-400">↳ </span> : null}
                        {categoria.nome}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{categoria.artigos_count}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{categoria.ordem}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap justify-end gap-2">
                        {depth === 0 ? (
                          <Button type="button" variant="secondary" onClick={() => abrirNovo(categoria.id)}>
                            Subcategoria
                          </Button>
                        ) : null}
                        <Button type="button" variant="secondary" onClick={() => abrirEditar(categoria)}>
                          Editar
                        </Button>
                        <Button type="button" variant="secondary" onClick={() => excluir(categoria)}>
                          Excluir
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

      {modalOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          onClick={fecharModal}
        >
          <form
            className={MODAL_PANEL_COMPACT}
            onClick={(e) => e.stopPropagation()}
            onSubmit={salvar}
          >
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              {editId != null ? 'Editar categoria' : 'Nova categoria'}
            </h2>
            <div className="mt-4 space-y-4">
              <Input
                label="Nome"
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                required
                autoFocus
              />
              <Select
                label="Categoria pai"
                value={form.parent_id}
                onChange={(v) => setForm((f) => ({ ...f, parent_id: typeof v === 'string' ? v : String(v) }))}
                options={kbCategoriasPaiOpcoes(paisDisponiveis)}
                includeEmpty
                emptyLabel="Nenhuma (categoria raiz)"
                placeholder="Categoria raiz"
                disabled={editId != null && categorias.some((c) => c.parent_id === editId)}
              />
              {editId != null && categorias.some((c) => c.parent_id === editId) ? (
                <p className="text-xs text-slate-500">
                  Categorias com subcategorias não podem virar subcategoria.
                </p>
              ) : null}
              <Input
                label="Ordem"
                type="number"
                min={0}
                value={form.ordem}
                onChange={(e) => setForm((f) => ({ ...f, ordem: e.target.value }))}
              />
            </div>
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <Button type="button" variant="secondary" onClick={fecharModal} disabled={saving}>
                Cancelar
              </Button>
              <Button type="submit" loading={saving}>
                Salvar
              </Button>
            </div>
          </form>
        </div>
      ) : null}
    </ConfigListPageShell>
  )
}
