import { useCallback, useEffect, useState } from 'react'
import { ApiError, ticketClassificacao, type TicketClassificacao } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Switch } from '../components/ui/Switch'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { IconPencil } from '../components/ui/IconPencil'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { MODAL_PANEL_COMPACT } from '../lib/modalPanel'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'

type Aba = 'naturezas' | 'motivos'

type NaturezaForm = TicketClassificacao.NaturezaCreate
type MotivoForm = TicketClassificacao.MotivoCreate

const emptyNatureza = (): NaturezaForm => ({ nome: '', slug: '', ordem: 0, ativo: true })
const emptyMotivo = (naturezaId: number): MotivoForm => ({
  natureza_id: naturezaId,
  nome: '',
  slug: '',
  ordem: 0,
  ativo: true,
})

export function TicketNaturezaMotivoPage({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [forbidden, setForbidden] = useState(false)
  const [aba, setAba] = useState<Aba>('naturezas')

  const [naturezas, setNaturezas] = useState<TicketClassificacao.Natureza[]>([])
  const [motivos, setMotivos] = useState<TicketClassificacao.Motivo[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [filtroNaturezaId, setFiltroNaturezaId] = useState<number | ''>('')
  const [loading, setLoading] = useState(true)

  const [modalOpen, setModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [formNatureza, setFormNatureza] = useState<NaturezaForm>(emptyNatureza())
  const [formMotivo, setFormMotivo] = useState<MotivoForm>(emptyMotivo(0))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos, aba, filtroNaturezaId])

  const loadNaturezasCatalogo = useCallback(() => {
    ticketClassificacao
      .listNaturezas({ limit: 100, incluir_inativos: true })
      .then(({ items }) => setNaturezas(items))
      .catch(() => setNaturezas([]))
  }, [])

  useEffect(() => {
    loadNaturezasCatalogo()
  }, [loadNaturezasCatalogo])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    const params = {
      incluir_inativos: incluirInativos,
      busca: debouncedBusca || undefined,
      offset: (page - 1) * PAGE_SIZE_PADRAO,
      limit: PAGE_SIZE_PADRAO,
    }
    const req =
      aba === 'naturezas'
        ? ticketClassificacao.listNaturezas(params)
        : ticketClassificacao.listMotivos({
            ...params,
            natureza_id: filtroNaturezaId === '' ? undefined : Number(filtroNaturezaId),
          })
    req
      .then(({ items, total: t }) => {
        if (aba === 'naturezas') {
          setNaturezas(items as TicketClassificacao.Natureza[])
          setMotivos([])
        } else {
          setMotivos(items as TicketClassificacao.Motivo[])
        }
        setTotal(t)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setTotal(0)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar o catálogo.'))
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [aba, debouncedBusca, filtroNaturezaId, incluirInativos, page, toast])

  useEffect(() => {
    load()
  }, [load])

  function abrirNovo() {
    setEditId(null)
    if (aba === 'naturezas') {
      setFormNatureza(emptyNatureza())
    } else {
      const nid = filtroNaturezaId === '' ? naturezas[0]?.id ?? 0 : Number(filtroNaturezaId)
      setFormMotivo(emptyMotivo(nid))
    }
    setModalOpen(true)
  }

  function abrirEditarNatureza(item: TicketClassificacao.Natureza) {
    setEditId(item.id)
    setFormNatureza({ nome: item.nome, slug: item.slug, ordem: item.ordem, ativo: item.ativo })
    setModalOpen(true)
  }

  function abrirEditarMotivo(item: TicketClassificacao.Motivo) {
    setEditId(item.id)
    setFormMotivo({
      natureza_id: item.natureza_id,
      nome: item.nome,
      slug: item.slug,
      ordem: item.ordem,
      ativo: item.ativo,
    })
    setModalOpen(true)
  }

  function fecharModal() {
    setModalOpen(false)
    setEditId(null)
  }

  async function salvar() {
    setSaving(true)
    try {
      if (aba === 'naturezas') {
        const nome = formNatureza.nome.trim()
        const slug = formNatureza.slug.trim().toLowerCase()
        if (!nome || !slug) {
          toast.showWarning('Informe nome e slug da natureza.')
          return
        }
        const payload = { ...formNatureza, nome, slug, ordem: Number(formNatureza.ordem) || 0 }
        if (editId != null) {
          await ticketClassificacao.updateNatureza(editId, payload)
        } else {
          await ticketClassificacao.createNatureza(payload)
        }
      } else {
        const nome = formMotivo.nome.trim()
        const slug = formMotivo.slug.trim().toLowerCase()
        if (!formMotivo.natureza_id || !nome || !slug) {
          toast.showWarning('Informe natureza, nome e slug do motivo.')
          return
        }
        const payload = { ...formMotivo, nome, slug, ordem: Number(formMotivo.ordem) || 0 }
        if (editId != null) {
          await ticketClassificacao.updateMotivo(editId, payload)
        } else {
          await ticketClassificacao.createMotivo(payload)
        }
      }
      toast.showSuccess('Salvo com sucesso.')
      fecharModal()
      loadNaturezasCatalogo()
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSaving(false)
    }
  }

  const denied = (
    <SemPermissao
      title="Apenas administradores podem gerir naturezas e motivos."
      voltarPara="/configuracoes/tickets/natureza-motivo"
      voltarLabel="Voltar"
    />
  )

  const tabBtn = (id: Aba, rotulo: string) => (
    <button
      type="button"
      onClick={() => setAba(id)}
      aria-current={aba === id ? 'page' : undefined}
      className={
        aba === id
          ? 'border-b-2 border-sky-500 px-3 py-2.5 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:text-white'
          : 'border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
      }
    >
      {rotulo}
    </button>
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Natureza e motivo"
      actions={
        <Button type="button" onClick={abrirNovo}>
          {aba === 'naturezas' ? 'Nova natureza' : 'Novo motivo'}
        </Button>
      }
    >
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="-mb-px flex gap-1" aria-label="Catálogo de classificação">
          {tabBtn('naturezas', 'Naturezas')}
          {tabBtn('motivos', 'Motivos')}
        </nav>
      </div>

      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder={aba === 'naturezas' ? 'Buscar natureza…' : 'Buscar motivo…'}
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <div className="flex flex-wrap items-center gap-3">
              {aba === 'motivos' ? (
                <Select
                  value={filtroNaturezaId}
                  onChange={(v) => setFiltroNaturezaId(v === '' ? '' : Number(v))}
                  options={naturezas.map((n) => ({ value: n.id, label: n.nome }))}
                  includeEmpty
                  emptyLabel="Todas as naturezas"
                  aria-label="Filtrar por natureza"
                />
              ) : null}
              <FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />
            </div>
          }
        />

        {loading ? (
          <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">Carregando…</p>
        ) : aba === 'naturezas' ? (
          naturezas.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-500">Nenhuma natureza cadastrada.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 sm:px-6">Nome</th>
                  <th className="px-4 py-3 sm:px-6">Slug</th>
                  <th className="px-4 py-3 text-center sm:px-6">Ordem</th>
                  <th className="px-4 py-3 sm:px-6">Situação</th>
                  <th className="w-px px-4 py-3 sm:px-6" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {naturezas.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 dark:hover:bg-white/40">
                    <td className="px-4 py-3.5 font-medium sm:px-6">{item.nome}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-500 sm:px-6">{item.slug}</td>
                    <td className="px-4 py-3.5 text-center tabular-nums sm:px-6">{item.ordem}</td>
                    <td className="px-4 py-3.5 sm:px-6">{item.ativo ? 'Ativo' : 'Inativo'}</td>
                    <td className="px-4 py-3.5 text-right sm:px-6">
                      <button type="button" onClick={() => abrirEditarNatureza(item)} aria-label={`Editar ${item.nome}`}>
                        <IconPencil />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : motivos.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-500">Nenhum motivo cadastrado.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/40">
                <th className="px-4 py-3 sm:px-6">Natureza</th>
                <th className="px-4 py-3 sm:px-6">Motivo</th>
                <th className="px-4 py-3 sm:px-6">Slug</th>
                <th className="px-4 py-3 text-center sm:px-6">Ordem</th>
                <th className="px-4 py-3 sm:px-6">Situação</th>
                <th className="w-px px-4 py-3 sm:px-6" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {motivos.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/80 dark:hover:bg-white/40">
                  <td className="px-4 py-3.5 text-slate-600 sm:px-6">{item.natureza_nome ?? item.natureza_id}</td>
                  <td className="px-4 py-3.5 font-medium sm:px-6">{item.nome}</td>
                  <td className="px-4 py-3.5 font-mono text-xs text-slate-500 sm:px-6">{item.slug}</td>
                  <td className="px-4 py-3.5 text-center tabular-nums sm:px-6">{item.ordem}</td>
                  <td className="px-4 py-3.5 sm:px-6">{item.ativo ? 'Ativo' : 'Inativo'}</td>
                  <td className="px-4 py-3.5 text-right sm:px-6">
                    <button type="button" onClick={() => abrirEditarMotivo(item)} aria-label={`Editar ${item.nome}`}>
                      <IconPencil />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {modalOpen && (
        <div className="fixed inset-0 z-[520] flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-[2px]">
          <div role="dialog" aria-modal="true" className={MODAL_PANEL_COMPACT} onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {editId != null ? 'Editar' : 'Novo'} {aba === 'naturezas' ? 'natureza' : 'motivo'}
            </h2>
            <div className="mt-4 space-y-3">
              {aba === 'motivos' ? (
                <Select
                  label="Natureza"
                  value={formMotivo.natureza_id || ''}
                  onChange={(v) => setFormMotivo((f) => ({ ...f, natureza_id: Number(v) }))}
                  options={naturezas.map((n) => ({ value: n.id, label: n.nome }))}
                  disabled={editId != null}
                />
              ) : null}
              <Input
                label="Nome"
                value={aba === 'naturezas' ? formNatureza.nome : formMotivo.nome}
                onChange={(e) =>
                  aba === 'naturezas'
                    ? setFormNatureza((f) => ({ ...f, nome: e.target.value }))
                    : setFormMotivo((f) => ({ ...f, nome: e.target.value }))
                }
              />
              <Input
                label="Slug"
                value={aba === 'naturezas' ? formNatureza.slug : formMotivo.slug}
                onChange={(e) =>
                  aba === 'naturezas'
                    ? setFormNatureza((f) => ({ ...f, slug: e.target.value }))
                    : setFormMotivo((f) => ({ ...f, slug: e.target.value }))
                }
              />
              <Input
                label="Ordem"
                type="number"
                value={String(aba === 'naturezas' ? formNatureza.ordem : formMotivo.ordem)}
                onChange={(e) => {
                  const ordem = Number(e.target.value) || 0
                  if (aba === 'naturezas') setFormNatureza((f) => ({ ...f, ordem }))
                  else setFormMotivo((f) => ({ ...f, ordem }))
                }}
              />
              <Switch
                label="Ativo"
                checked={aba === 'naturezas' ? formNatureza.ativo ?? true : formMotivo.ativo ?? true}
                onCheckedChange={(ativo) =>
                  aba === 'naturezas'
                    ? setFormNatureza((f) => ({ ...f, ativo }))
                    : setFormMotivo((f) => ({ ...f, ativo }))
                }
              />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button type="button" variant="cancel" onClick={fecharModal} disabled={saving}>
                Cancelar
              </Button>
              <Button type="button" onClick={() => void salvar()} loading={saving}>
                Salvar
              </Button>
            </div>
          </div>
        </div>
      )}
    </ConfigListPageShell>
  )
}
