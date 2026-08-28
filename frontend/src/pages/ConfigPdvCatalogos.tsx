import { useCallback, useEffect, useState } from 'react'
import { ApiError, pdvRotulos, pdvTiposAcessoRemoto, type PdvCatalogo } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { IconPencil } from '../components/ui/IconPencil'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { MODAL_PANEL_COMPACT } from '../lib/modalPanel'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'

type Aba = 'rotulos' | 'tipos-acesso'

type CatalogoApi = {
  list: (params?: {
    incluir_inativos?: boolean
    busca?: string
    offset?: number
    limit?: number
  }) => Promise<{ items: PdvCatalogo.Item[]; total: number }>
  create: (data: PdvCatalogo.Create) => Promise<PdvCatalogo.Item>
  update: (id: number, data: PdvCatalogo.Update) => Promise<PdvCatalogo.Item>
}

const ABAS: {
  id: Aba
  rotulo: string
  titulo: string
  descricao: string
  exemplos: string
  placeholderBusca: string
  vazio: string
  novoRotulo: string
  modalNovo: string
  modalEditar: string
  sucessoCriar: string
  sucessoSalvar: string
  api: CatalogoApi
}[] = [
  {
    id: 'rotulos',
    rotulo: 'Rótulos',
    titulo: 'Rótulos de dispositivo',
    descricao:
      'Identificam o papel físico do terminal no posto — como caixa principal, caixa auxiliar ou bombas.',
    exemplos: 'Ex.: Caixa Principal, Caixa 2, Bomba 01',
    placeholderBusca: 'Buscar rótulo…',
    vazio: 'Nenhum rótulo cadastrado.',
    novoRotulo: 'Novo rótulo',
    modalNovo: 'Novo rótulo de dispositivo',
    modalEditar: 'Editar rótulo de dispositivo',
    sucessoCriar: 'Rótulo cadastrado.',
    sucessoSalvar: 'Rótulo atualizado.',
    api: pdvRotulos,
  },
  {
    id: 'tipos-acesso',
    rotulo: 'Acesso remoto',
    titulo: 'Tipos de acesso remoto',
    descricao: 'Ferramentas usadas para suporte remoto ao PDV — independente do rótulo do dispositivo.',
    exemplos: 'Ex.: AnyDesk, TeamViewer, RustDesk',
    placeholderBusca: 'Buscar tipo…',
    vazio: 'Nenhum tipo de acesso cadastrado.',
    novoRotulo: 'Novo tipo',
    modalNovo: 'Novo tipo de acesso remoto',
    modalEditar: 'Editar tipo de acesso remoto',
    sucessoCriar: 'Tipo de acesso cadastrado.',
    sucessoSalvar: 'Tipo de acesso atualizado.',
    api: pdvTiposAcessoRemoto,
  },
]

const emptyForm = (): PdvCatalogo.Create => ({
  nome: '',
  ordem_exibicao: 0,
  ativo: true,
})

export function ConfigPdvCatalogos({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [forbidden, setForbidden] = useState(false)
  const [aba, setAba] = useState<Aba>('rotulos')
  const config = ABAS.find((t) => t.id === aba) ?? ABAS[0]

  const [items, setItems] = useState<PdvCatalogo.Item[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [loading, setLoading] = useState(true)

  const [modalOpen, setModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState<PdvCatalogo.Create>(emptyForm())
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos, aba])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    config.api
      .list({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items: rows, total: t }) => {
        setItems(rows)
        setTotal(t)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setItems([])
          setTotal(0)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, `Não foi possível carregar ${config.titulo.toLowerCase()}.`))
        setItems([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [config.api, config.titulo, debouncedBusca, incluirInativos, page, toast])

  useEffect(() => {
    load()
  }, [load])

  function abrirNovo() {
    setEditId(null)
    setForm(emptyForm())
    setModalOpen(true)
  }

  function abrirEditar(item: PdvCatalogo.Item) {
    setEditId(item.id)
    setForm({
      nome: item.nome,
      ordem_exibicao: item.ordem_exibicao,
      ativo: item.ativo,
    })
    setModalOpen(true)
  }

  function fecharModal() {
    setModalOpen(false)
    setEditId(null)
    setForm(emptyForm())
  }

  async function salvar() {
    const nome = form.nome.trim()
    if (!nome) {
      toast.showWarning('Informe o nome.')
      return
    }
    setSaving(true)
    try {
      const payload = {
        nome,
        ordem_exibicao: Number(form.ordem_exibicao) || 0,
        ativo: form.ativo ?? true,
      }
      if (editId != null) {
        await config.api.update(editId, payload)
        toast.showSuccess(config.sucessoSalvar)
      } else {
        await config.api.create(payload)
        toast.showSuccess(config.sucessoCriar)
      }
      fecharModal()
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSaving(false)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Apenas administradores podem gerir os catálogos de PDV."
        voltarPara="/"
        voltarLabel="Voltar"
      />
    )
  }

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

  const actionsBtn = (
    <Button type="button" onClick={abrirNovo}>
      {config.novoRotulo}
    </Button>
  )

  const conteudo = (
    <>
      {embedded ? (
        <div className="flex justify-end">{actionsBtn}</div>
      ) : (
        <PageHeader
          title="Catálogos de PDV"
          subtitle="Padrões globais usados no cadastro de terminais por empresa."
          actions={actionsBtn}
        />
      )}

      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="-mb-px flex gap-1" aria-label="Tipo de catálogo">
          {ABAS.map((t) => tabBtn(t.id, t.rotulo))}
        </nav>
      </div>

      {!embedded ? (
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          <span className="font-medium text-slate-800 dark:text-slate-200">{config.titulo}.</span>{' '}
          {config.descricao} {config.exemplos}
        </p>
      ) : null}

      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder={config.placeholderBusca}
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
        />

        {loading ? (
          <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">Carregando…</p>
        ) : items.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">{config.vazio}</p>
            <Button type="button" variant="secondary" className="mt-4" onClick={abrirNovo}>
              {config.novoRotulo}
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
                  <th className="px-4 py-3 sm:px-6">Nome</th>
                  <th className="w-24 px-4 py-3 text-center sm:px-6">Ordem</th>
                  <th className="w-32 px-4 py-3 sm:px-6">Situação</th>
                  <th className="w-px px-4 py-3 text-right sm:px-6">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className="transition-colors hover:bg-slate-50/80 focus-within:bg-slate-50/80 dark:hover:bg-white/5 dark:focus-within:bg-slate-800/50"
                  >
                    <td className="px-4 py-3.5 font-medium text-slate-800 dark:text-slate-100 sm:px-6">{item.nome}</td>
                    <td className="px-4 py-3.5 text-center tabular-nums text-slate-600 dark:text-slate-400 sm:px-6">
                      {item.ordem_exibicao}
                    </td>
                    <td className="px-4 py-3.5 sm:px-6">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          item.ativo
                            ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/15 dark:bg-emerald-950/40 dark:text-emerald-300'
                            : 'bg-slate-100 text-slate-500 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-400'
                        }`}
                      >
                        {item.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6">
                      <Button
                        type="button"
                        variant="ghost"
                        className="!px-2 !py-2"
                        onClick={() => abrirEditar(item)}
                        aria-label={`Editar ${item.nome}`}
                      >
                        <IconPencil ariaHidden={false} />
                      </Button>
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
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[2px]"
          role="presentation"
          onClick={fecharModal}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="pdv-catalogo-modal-title"
            className={MODAL_PANEL_COMPACT}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="pdv-catalogo-modal-title" className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              {editId != null ? config.modalEditar : config.modalNovo}
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{config.exemplos}</p>

            <form
              className="mt-5 space-y-4"
              onSubmit={(e) => {
                e.preventDefault()
                void salvar()
              }}
            >
              <Input
                id={`pdv-catalogo-nome-${aba}`}
                label="Nome"
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                autoFocus
                required
              />
              <Input
                id={`pdv-catalogo-ordem-${aba}`}
                label="Ordem de exibição"
                type="number"
                hint="Menor número aparece primeiro nas listas de seleção."
                value={String(form.ordem_exibicao ?? 0)}
                onChange={(e) => setForm((f) => ({ ...f, ordem_exibicao: Number(e.target.value) || 0 }))}
              />
              <Switch
                bare
                checked={form.ativo ?? true}
                onCheckedChange={(ativo) => setForm((f) => ({ ...f, ativo }))}
                label="Ativo"
                showStatusPill
              />
              <div className="flex justify-end gap-2 border-t border-slate-200 pt-4 dark:border-slate-800">
                <Button type="button" variant="cancel" onClick={fecharModal}>
                  Cancelar
                </Button>
                <Button type="submit" loading={saving}>
                  Salvar
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  )

  return embedded ? conteudo : <PageContainer>{conteudo}</PageContainer>
}
