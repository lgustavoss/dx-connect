import { useState, useEffect } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { setores, type Setores } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { IconPencil } from '../components/ui/IconPencil'
import { IconTrash } from '../components/ui/IconTrash'
import { useToast } from '../components/ui/Toast'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { Switch } from '../components/ui/Switch'
import { useNavigate } from 'react-router-dom'
import { FormSection } from '../components/ui/FormSection'

type ColunaSetor = 'nome' | 'slug' | 'ativo'

export function Setores() {
  const toast = useToast()
  const navigate = useNavigate()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaSetor>()
  const [list, setList] = useState<Setores.Setor[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [nome, setNome] = useState('')
  const [slug, setSlug] = useState('')
  const [ativo, setAtivo] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!modalOpen) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [modalOpen])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos, ordenarPor, ordem])

  function load() {
    setLoading(true)
    setores
      .list({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
        ...sortParams,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [page, debouncedBusca, incluirInativos, ordenarPor, ordem])

  function openCreate() {
    setEditingId(null)
    setNome('')
    setSlug('')
    setAtivo(true)
    setModalOpen(true)
  }

  function openEdit(item: { id: number; nome: string; slug: string; ativo: boolean }) {
    setEditingId(item.id)
    setNome(item.nome)
    setSlug(item.slug)
    setAtivo(item.ativo)
    setModalOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        await setores.update(editingId, { nome: nome.trim(), slug: slug.trim(), ativo })
        toast.showSuccess('Setor atualizado.')
      } else {
        await setores.create({ nome: nome.trim(), slug: slug.trim(), ativo })
        toast.showSuccess('Setor cadastrado.')
      }
      setModalOpen(false)
      load()
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Excluir este setor?')) return
    try {
      await setores.delete(id)
      load()
    } catch (err) {
      toast.showWarning(err instanceof Error ? err.message : 'Erro ao excluir')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Setores</h1>
        <Button onClick={openCreate}>Novo setor</Button>
      </div>
      {!modalOpen && (
        <Card>
          <BarraBuscaPaginacao
            busca={busca}
            onBuscaChange={setBusca}
            placeholder="Buscar por nome"
            page={page}
            total={total}
            onPageChange={setPage}
            disabled={loading}
            extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
          />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum setor encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel coluna="nome" rotulo="Nome" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="slug" rotulo="Slug" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="ativo" rotulo="Situação" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <th className="w-px whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((s) => (
                  <tr
                    key={s.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/setores/${s.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/setores/${s.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50 focus:outline-none focus-visible:bg-slate-100 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <span className={`font-medium ${s.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>{s.nome}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">{s.slug}</td>
                    <td className="whitespace-nowrap px-4 py-3.5 sm:px-6">
                      {s.ativo ? (
                        <span className="text-slate-600 dark:text-slate-400">Ativo</span>
                      ) : (
                        <span className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">Inativo</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                      <div className="inline-flex gap-1.5">
                        <Button
                          variant="ghost"
                          onClick={() => openEdit(s)}
                          aria-label="Editar setor"
                        >
                          <IconPencil ariaHidden={false} />
                        </Button>
                        <Button variant="ghost" onClick={() => handleDelete(s.id)} aria-label="Excluir setor">
                          <IconTrash ariaHidden={false} />
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
      )}

      {modalOpen && (
        <div className="fixed inset-y-0 left-0 right-0 z-20 flex items-start justify-center bg-black/85 px-4 pb-6 pt-16 sm:px-6 md:left-[var(--sidebar-w)]">
          <Card title={editingId ? 'Editar setor' : 'Novo setor'} className="w-full max-w-md">
            <form onSubmit={handleSubmit}>
              <div className="space-y-6">
                <FormSection title="Dados do setor">
                  <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
                  <Input
                    label="Slug"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    placeholder="ex: suporte"
                    required
                  />
                </FormSection>

                <FormSection title="Situação no sistema">
                  <Switch
                    bare
                    checked={ativo}
                    onCheckedChange={setAtivo}
                    label="Setor ativo"
                    showStatusPill
                    statusOnText="Ativo"
                    statusOffText="Inativo"
                  />
                </FormSection>
              </div>

              <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
                <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <Button type="button" variant="secondary" className="w-full sm:w-auto" onClick={() => setModalOpen(false)}>
                    Cancelar
                  </Button>
                  <Button type="submit" loading={saving} className="w-full sm:w-auto">
                    Salvar
                  </Button>
                </div>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  )
}
