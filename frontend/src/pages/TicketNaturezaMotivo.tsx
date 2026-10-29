import { useCallback, useEffect, useMemo, useState } from 'react'
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
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
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
  const { user } = useAuth()
  const podeCriar = temPermissao(user, 'natureza.criar')
  const podeEditar = temPermissao(user, 'natureza.editar')
  const [forbidden, setForbidden] = useState(false)
  const [aba, setAba] = useState<Aba>('naturezas')

  const [catalogoNaturezas, setCatalogoNaturezas] = useState<TicketClassificacao.Natureza[]>([])
  const [naturezas, setNaturezas] = useState<TicketClassificacao.Natureza[]>([])
  const [motivos, setMotivos] = useState<TicketClassificacao.Motivo[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [filtroNaturezaId, setFiltroNaturezaId] = useState<number | ''>('')
  const [abertas, setAbertas] = useState<number[]>([])
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
      .then(({ items }) => setCatalogoNaturezas(items))
      .catch(() => setCatalogoNaturezas([]))
  }, [])

  useEffect(() => {
    loadNaturezasCatalogo()
  }, [loadNaturezasCatalogo])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    if (aba === 'naturezas') {
      ticketClassificacao
        .listNaturezas({
          incluir_inativos: incluirInativos,
          busca: debouncedBusca || undefined,
          offset: (page - 1) * PAGE_SIZE_PADRAO,
          limit: PAGE_SIZE_PADRAO,
        })
        .then(({ items, total: t }) => {
          setNaturezas(items)
          setMotivos([])
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
      return
    }

    ticketClassificacao
      .listMotivos({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
        natureza_id: filtroNaturezaId === '' ? undefined : Number(filtroNaturezaId),
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setMotivos(items)
        setNaturezas([])
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

  const gruposMotivo = useMemo(() => {
    const porNatureza = new Map<number, TicketClassificacao.Motivo[]>()
    for (const motivo of motivos) {
      const lista = porNatureza.get(motivo.natureza_id) ?? []
      lista.push(motivo)
      porNatureza.set(motivo.natureza_id, lista)
    }
    const idsOrdem = catalogoNaturezas.map((n) => n.id)
    const ids = [
      ...idsOrdem.filter((id) => porNatureza.has(id)),
      ...[...porNatureza.keys()].filter((id) => !idsOrdem.includes(id)),
    ]
    if (filtroNaturezaId !== '') {
      return ids
        .filter((id) => id === Number(filtroNaturezaId))
        .map((id) => ({
          naturezaId: id,
          nome:
            catalogoNaturezas.find((n) => n.id === id)?.nome ??
            porNatureza.get(id)?.[0]?.natureza_nome ??
            `Natureza #${id}`,
          itens: porNatureza.get(id) ?? [],
        }))
    }
    return ids.map((id) => ({
      naturezaId: id,
      nome:
        catalogoNaturezas.find((n) => n.id === id)?.nome ??
        porNatureza.get(id)?.[0]?.natureza_nome ??
        `Natureza #${id}`,
      itens: porNatureza.get(id) ?? [],
    }))
  }, [catalogoNaturezas, filtroNaturezaId, motivos])

  useEffect(() => {
    if (aba !== 'motivos') return
    const ids = gruposMotivo.map((g) => g.naturezaId)
    setAbertas((atual) =>
      atual.length === ids.length && atual.every((id, i) => id === ids[i]) ? atual : ids,
    )
  }, [aba, gruposMotivo])

  function abrirNovo() {
    setEditId(null)
    if (aba === 'naturezas') {
      setFormNatureza(emptyNatureza())
    } else {
      const nid = filtroNaturezaId === '' ? catalogoNaturezas[0]?.id ?? 0 : Number(filtroNaturezaId)
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

  function alternarGrupo(naturezaId: number) {
    setAbertas((atual) =>
      atual.includes(naturezaId) ? atual.filter((id) => id !== naturezaId) : [...atual, naturezaId],
    )
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
      title="Sem permissão para gerir naturezas e motivos."
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
        podeCriar ? (
          <Button type="button" onClick={abrirNovo}>
            {aba === 'naturezas' ? 'Nova natureza' : 'Novo motivo'}
          </Button>
        ) : undefined
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
          pageSize={PAGE_SIZE_PADRAO}
          onPageChange={setPage}
          disabled={loading}
          extra={
            aba === 'motivos' ? (
              <Select
                value={filtroNaturezaId}
                onChange={(v) => setFiltroNaturezaId(v === '' ? '' : Number(v))}
                options={catalogoNaturezas.map((n) => ({ value: n.id, label: n.nome }))}
                includeEmpty
                emptyLabel="Todas as naturezas"
                aria-label="Filtrar por natureza"
                className="w-full"
              />
            ) : undefined
          }
          juntoPaginacao={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
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
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/80 focus-within:bg-slate-50/80 dark:hover:bg-white/5 dark:focus-within:bg-slate-800/50"
                  >
                    <td className="px-4 py-3.5 font-medium sm:px-6">{item.nome}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-500 sm:px-6">{item.slug}</td>
                    <td className="px-4 py-3.5 text-center tabular-nums sm:px-6">{item.ordem}</td>
                    <td className="px-4 py-3.5 sm:px-6">{item.ativo ? 'Ativo' : 'Inativo'}</td>
                    <td className="px-4 py-3.5 text-right sm:px-6">
                      {podeEditar ? (
                        <button type="button" onClick={() => abrirEditarNatureza(item)} aria-label={`Editar ${item.nome}`}>
                          <IconPencil />
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : gruposMotivo.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-500">Nenhum motivo cadastrado.</p>
        ) : (
          <div className="space-y-2">
            {gruposMotivo.map((grupo) => {
              const aberta = abertas.includes(grupo.naturezaId)
              return (
                <section
                  key={grupo.naturezaId}
                  className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800"
                >
                  <button
                    type="button"
                    aria-expanded={aberta}
                    onClick={() => alternarGrupo(grupo.naturezaId)}
                    className="flex w-full items-center justify-between gap-3 bg-slate-50/80 px-4 py-3 text-left transition hover:bg-slate-100/80 dark:bg-slate-800/40 dark:hover:bg-slate-800/70"
                  >
                    <span className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                      <svg
                        className={`size-4 shrink-0 text-slate-400 transition-transform ${aberta ? 'rotate-90' : ''}`}
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        aria-hidden
                      >
                        <path
                          fillRule="evenodd"
                          d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                          clipRule="evenodd"
                        />
                      </svg>
                      {grupo.nome}
                    </span>
                    <span className="text-xs font-medium tabular-nums text-slate-500 dark:text-slate-400">
                      {grupo.itens.length} {grupo.itens.length === 1 ? 'motivo' : 'motivos'}
                    </span>
                  </button>
                  {aberta ? (
                    grupo.itens.length === 0 ? (
                      <p className="px-4 py-6 text-center text-sm text-slate-500">Nenhum motivo nesta natureza.</p>
                    ) : (
                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr className="border-y border-slate-100 bg-white text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-950/40">
                            <th className="px-4 py-2.5 sm:px-6">Motivo</th>
                            <th className="px-4 py-2.5 sm:px-6">Slug</th>
                            <th className="px-4 py-2.5 text-center sm:px-6">Ordem</th>
                            <th className="px-4 py-2.5 sm:px-6">Situação</th>
                            <th className="w-px px-4 py-2.5 sm:px-6" />
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                          {grupo.itens.map((item) => (
                            <tr
                              key={item.id}
                              className="hover:bg-slate-50/80 focus-within:bg-slate-50/80 dark:hover:bg-white/5 dark:focus-within:bg-slate-800/50"
                            >
                              <td className="px-4 py-3 font-medium sm:px-6">{item.nome}</td>
                              <td className="px-4 py-3 font-mono text-xs text-slate-500 sm:px-6">{item.slug}</td>
                              <td className="px-4 py-3 text-center tabular-nums sm:px-6">{item.ordem}</td>
                              <td className="px-4 py-3 sm:px-6">{item.ativo ? 'Ativo' : 'Inativo'}</td>
                              <td className="px-4 py-3 text-right sm:px-6">
                                {podeEditar ? (
                                  <button
                                    type="button"
                                    onClick={() => abrirEditarMotivo(item)}
                                    aria-label={`Editar ${item.nome}`}
                                  >
                                    <IconPencil />
                                  </button>
                                ) : null}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )
                  ) : null}
                </section>
              )
            })}
          </div>
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
                  options={catalogoNaturezas.map((n) => ({ value: n.id, label: n.nome }))}
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
                description={
                  aba === 'naturezas'
                    ? 'Não dá para desativar se houver motivo ativo, ou ticket ou chat ainda em aberto. Encerrados não impedem.'
                    : 'Não dá para desativar se algum ticket ou chat ainda em aberto usa este motivo. Encerrados não impedem.'
                }
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
