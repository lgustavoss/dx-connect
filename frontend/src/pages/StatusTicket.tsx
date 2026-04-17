import { useState, useEffect, useCallback } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { ApiError, statusTicket, type StatusTicket } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { IconPencil } from '../components/ui/IconPencil'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { FormSection } from '../components/ui/FormSection'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

type ColunaStatus = 'nome' | 'slug' | 'ordem' | 'ativo'

export function StatusTicketPage() {
  const toast = useToast()
  const { ordenarPor, ordem: ordemLista, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaStatus>()
  const [list, setList] = useState<StatusTicket.Status[]>([])
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
  const [ordem, setOrdem] = useState(0)
  const [ativo, setAtivo] = useState(true)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)

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
  }, [debouncedBusca, incluirInativos, ordenarPor, ordemLista])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    statusTicket
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
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          setTotal(0)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de status de ticket.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  function openCreate() {
    setEditingId(null)
    setNome('')
    setSlug('')
    setOrdem(total)
    setAtivo(true)
    setModalOpen(true)
  }

  function openEdit(item: StatusTicket.Status) {
    setEditingId(item.id)
    setNome(item.nome)
    setSlug(item.slug)
    setOrdem(item.ordem)
    setAtivo(item.ativo)
    setModalOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        await statusTicket.update(editingId, { nome: nome.trim(), slug: slug.trim(), ordem, ativo })
        toast.showSuccess('Status atualizado.')
      } else {
        await statusTicket.create({ nome: nome.trim(), slug: slug.trim(), ordem, ativo })
        toast.showSuccess('Status cadastrado.')
      }
      setModalOpen(false)
      load()
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro')
    } finally {
      setSaving(false)
    }
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para listar status de ticket."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <div className="flex justify-between">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Status de ticket</h1>
        <Button onClick={openCreate}>Novo status</Button>
      </div>
      {!modalOpen && (
        <Card>
          <BarraBuscaPaginacao
            busca={busca}
            onBuscaChange={setBusca}
            placeholder="Buscar por nome ou slug"
            page={page}
            total={total}
            onPageChange={setPage}
            disabled={loading}
            extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
          />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum status encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel coluna="nome" rotulo="Nome" ordenarPor={ordenarPor} ordem={ordemLista} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="slug" rotulo="Slug" ordenarPor={ordenarPor} ordem={ordemLista} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="ordem" rotulo="Ordem" ordenarPor={ordenarPor} ordem={ordemLista} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="ativo" rotulo="Situação" ordenarPor={ordenarPor} ordem={ordemLista} aoOrdenar={aoOrdenarColuna} />
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
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
                    onClick={() => openEdit(s)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        openEdit(s)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <span className={`font-medium ${s.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>{s.nome}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">{s.slug}</td>
                    <td className="whitespace-nowrap px-4 py-3.5 tabular-nums text-slate-600 sm:px-6 dark:text-slate-400">{s.ordem}</td>
                    <td className="whitespace-nowrap px-4 py-3.5 sm:px-6">
                      {s.ativo ? (
                        <span className="text-slate-600 dark:text-slate-400">Ativo</span>
                      ) : (
                        <span className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">Inativo</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                      <Button variant="ghost" onClick={() => openEdit(s)} aria-label="Editar">
                        <IconPencil />
                      </Button>
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
          <Card title={editingId ? 'Editar status' : 'Novo status'} className="w-full max-w-md">
            <form onSubmit={handleSubmit}>
              <div className="space-y-6">
                <FormSection title="Dados do status">
                  <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
                  <Input
                    label="Slug"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    placeholder="ex: aguardando_atendimento"
                    required
                  />
                  <Input label="Ordem" type="number" value={ordem} onChange={(e) => setOrdem(Number(e.target.value))} />
                </FormSection>

                <FormSection title="Situação no sistema">
                  <Switch
                    bare
                    checked={ativo}
                    onCheckedChange={setAtivo}
                    label="Status ativo"
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
