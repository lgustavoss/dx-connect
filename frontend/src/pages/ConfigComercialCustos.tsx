import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  comercialCustosItens,
  comercialSalarioMinimo,
  type ComercialCustos,
} from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { Select } from '../components/ui/Select'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { IconPencil } from '../components/ui/IconPencil'
import { IconTrash } from '../components/ui/IconTrash'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { MODAL_PANEL_COMPACT } from '../lib/modalPanel'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'

type Aba = 'sm' | 'itens' | 'simular'

type PendingDelete =
  | { kind: 'sm'; id: number; rotulo: string }
  | { kind: 'item'; id: number; rotulo: string }

const TIPO_LABEL: Record<string, string> = {
  percentual_sm: '% salário mínimo',
  valor_fixo: 'Valor fixo',
  composto_tef: 'TEF (base + adicional)',
}

const emptySmForm = (): ComercialCustos.SalarioMinimoAtualizarValor => ({
  valor: '',
  vigencia_inicio: new Date().toISOString().slice(0, 10),
})

const emptyItem = (): ComercialCustos.ItemCreate => ({
  nome: '',
  slug: '',
  tipo: 'percentual_sm',
  percentual_sm: '',
  valor_fixo: '',
  tef_base: '',
  tef_adicional: '',
  aplica_tier_posto: false,
  ordem: 0,
  ativo: true,
})

/** Identificador técnico interno — gerado a partir do nome; não aparece na UI. */
function slugify(nome: string): string {
  const base = nome
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40)
  return base || 'item'
}

function fmtMoney(v: string | number | null | undefined): string {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function fmtPercentual(v: string | number | null | undefined): string {
  if (v == null || v === '') return '—'
  const n = Math.round(Number(v))
  if (Number.isNaN(n)) return String(v)
  return `${n}% SM`
}

function fmtDataIso(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  if (!y || !m || !d) return iso
  return `${d}/${m}/${y}`
}

export function ConfigComercialCustos({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [forbidden, setForbidden] = useState(false)
  const [aba, setAba] = useState<Aba>('sm')

  // —— SM ——
  const [smItems, setSmItems] = useState<ComercialCustos.SalarioMinimo[]>([])
  const [smTotal, setSmTotal] = useState(0)
  const [smPage, setSmPage] = useState(1)
  const [smLoading, setSmLoading] = useState(true)
  const [smModal, setSmModal] = useState(false)
  const [smForm, setSmForm] = useState(emptySmForm())
  const [smSaving, setSmSaving] = useState(false)
  const smVigente = smItems.find((r) => r.vigencia_fim == null) ?? null
  const smTemHistorico = smTotal > 0

  // —— Itens ——
  const [itens, setItens] = useState<ComercialCustos.Item[]>([])
  const [itensTotal, setItensTotal] = useState(0)
  const [itensPage, setItensPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [itensLoading, setItensLoading] = useState(true)
  const [itemModal, setItemModal] = useState(false)
  const [itemEditId, setItemEditId] = useState<number | null>(null)
  const [itemForm, setItemForm] = useState(emptyItem())
  const [itemSaving, setItemSaving] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  // —— Simular ——
  const [simItens, setSimItens] = useState<ComercialCustos.Item[]>([])
  const [simSelected, setSimSelected] = useState<number[]>([])
  const [simPdvs, setSimPdvs] = useState('1')
  const [simData, setSimData] = useState(() => new Date().toISOString().slice(0, 10))
  const [simDescontoPosto, setSimDescontoPosto] = useState(false)
  const [simTefCustoBase, setSimTefCustoBase] = useState('')
  const [simTefCustoAdic, setSimTefCustoAdic] = useState('')
  const [simTefCliBase, setSimTefCliBase] = useState('')
  const [simTefCliAdic, setSimTefCliAdic] = useState('')
  const [simResult, setSimResult] = useState<ComercialCustos.SimularResponse | null>(null)
  const [simLoading, setSimLoading] = useState(false)
  const [simCatalogLoading, setSimCatalogLoading] = useState(false)

  const simTemTefSelecionado = simItens.some(
    (i) => simSelected.includes(i.id) && i.tipo === 'composto_tef',
  )
  const simTemPostoTier = simItens.some(
    (i) => simSelected.includes(i.id) && i.aplica_tier_posto,
  )

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setItensPage(1)
  }, [debouncedBusca, incluirInativos])

  const loadSm = useCallback(() => {
    setSmLoading(true)
    setForbidden(false)
    comercialSalarioMinimo
      .list({
        offset: (smPage - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
        ordenar_por: 'vigencia_inicio',
        ordem: 'desc',
      })
      .then(({ items, total }) => {
        setSmItems(items)
        setSmTotal(total)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar o salário mínimo.'))
        setSmItems([])
        setSmTotal(0)
      })
      .finally(() => setSmLoading(false))
  }, [smPage, toast])

  const loadItens = useCallback(() => {
    setItensLoading(true)
    setForbidden(false)
    comercialCustosItens
      .list({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
        offset: (itensPage - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total }) => {
        setItens(items)
        setItensTotal(total)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os itens de custo.'))
        setItens([])
        setItensTotal(0)
      })
      .finally(() => setItensLoading(false))
  }, [debouncedBusca, incluirInativos, itensPage, toast])

  const loadSimCatalogo = useCallback(() => {
    setSimCatalogLoading(true)
    comercialCustosItens
      .list({ incluir_inativos: false, limit: 100, ordenar_por: 'ordem', ordem: 'asc' })
      .then(({ items }) => setSimItens(items))
      .catch((err) => {
        setSimItens([])
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os itens para simular.'))
      })
      .finally(() => setSimCatalogLoading(false))
  }, [toast])

  useEffect(() => {
    if (aba === 'sm') loadSm()
    else if (aba === 'itens') loadItens()
    else loadSimCatalogo()
  }, [aba, loadSm, loadItens, loadSimCatalogo])

  async function salvarSm() {
    const valor = String(smForm.valor).trim()
    if (!valor || Number(valor) <= 0) {
      toast.showWarning('Informe um valor de salário mínimo válido.')
      return
    }
    if (!smForm.vigencia_inicio) {
      toast.showWarning('Informe a data a partir da qual o valor passa a valer.')
      return
    }
    setSmSaving(true)
    try {
      await comercialSalarioMinimo.atualizarValor({
        valor,
        vigencia_inicio: smForm.vigencia_inicio,
      })
      toast.showSuccess(smTemHistorico ? 'Salário mínimo atualizado. Histórico preservado.' : 'Salário mínimo definido.')
      setSmModal(false)
      setSmForm(emptySmForm())
      loadSm()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSmSaving(false)
    }
  }

  async function confirmarExclusao() {
    if (!pendingDelete) return
    setDeleteLoading(true)
    try {
      if (pendingDelete.kind === 'sm') {
        await comercialSalarioMinimo.delete(pendingDelete.id)
        toast.showSuccess('Salário mínimo excluído.')
        loadSm()
      } else {
        await comercialCustosItens.delete(pendingDelete.id)
        toast.showSuccess('Item excluído.')
        loadItens()
        setSimSelected((prev) => prev.filter((id) => id !== pendingDelete.id))
      }
      setPendingDelete(null)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir.'))
    } finally {
      setDeleteLoading(false)
    }
  }

  async function salvarItem() {
    const nome = itemForm.nome.trim()
    if (!nome) {
      toast.showWarning('Informe o nome.')
      return
    }
    if (itemForm.tipo === 'percentual_sm' && (itemForm.percentual_sm === '' || itemForm.percentual_sm == null)) {
      toast.showWarning('Informe o percentual do salário mínimo.')
      return
    }
    if (itemForm.tipo === 'valor_fixo' && (itemForm.valor_fixo === '' || itemForm.valor_fixo == null)) {
      toast.showWarning('Informe o valor fixo.')
      return
    }
    if (
      itemForm.tipo === 'composto_tef' &&
      (itemForm.tef_base === '' || itemForm.tef_base == null || itemForm.tef_adicional === '' || itemForm.tef_adicional == null)
    ) {
      toast.showWarning('Informe TEF base e adicional por PDV.')
      return
    }
    setItemSaving(true)
    try {
      const percentual =
        itemForm.tipo === 'percentual_sm' ? String(Math.round(Number(itemForm.percentual_sm))) : null
      const basePayload = {
        nome,
        descricao: itemForm.descricao || null,
        tipo: itemForm.tipo,
        ativo: itemForm.ativo ?? true,
        percentual_sm: percentual,
        valor_fixo: itemForm.tipo === 'valor_fixo' ? itemForm.valor_fixo : null,
        tef_base: itemForm.tipo === 'composto_tef' ? itemForm.tef_base : null,
        tef_adicional: itemForm.tipo === 'composto_tef' ? itemForm.tef_adicional : null,
        aplica_tier_posto: itemForm.tipo === 'percentual_sm' ? !!itemForm.aplica_tier_posto : false,
        vigencia_inicio: itemForm.vigencia_inicio || null,
        vigencia_fim: itemForm.vigencia_fim || null,
      }
      if (itemEditId != null) {
        await comercialCustosItens.update(itemEditId, basePayload)
        toast.showSuccess('Item atualizado.')
      } else {
        let slug = slugify(nome)
        try {
          await comercialCustosItens.create({ ...basePayload, slug, ordem: 0 })
        } catch (err) {
          const detail = err instanceof ApiError ? String((err.body as { detail?: unknown })?.detail ?? err.message) : ''
          if (err instanceof ApiError && err.status === 400 && /slug/i.test(detail)) {
            slug = `${slugify(nome)}-${Date.now().toString(36).slice(-5)}`
            await comercialCustosItens.create({ ...basePayload, slug, ordem: 0 })
          } else {
            throw err
          }
        }
        toast.showSuccess('Item cadastrado.')
      }
      setItemModal(false)
      setItemEditId(null)
      setItemForm(emptyItem())
      loadItens()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setItemSaving(false)
    }
  }

  async function executarSimulacao() {
    if (simSelected.length === 0) {
      toast.showWarning('Selecione ao menos um item de custo.')
      return
    }
    const pdvs = Number(simPdvs) || 1
    const temCustoOverride = simTefCustoBase.trim() !== '' || simTefCustoAdic.trim() !== ''
    const temClienteOverride = simTefCliBase.trim() !== '' || simTefCliAdic.trim() !== ''
    if (temCustoOverride && (simTefCustoBase.trim() === '' || simTefCustoAdic.trim() === '')) {
      toast.showWarning('Informe base e adicional do custo TEF promocional, ou deixe ambos vazios.')
      return
    }
    if (temClienteOverride && (simTefCliBase.trim() === '' || simTefCliAdic.trim() === '')) {
      toast.showWarning('Informe base e adicional do valor TEF ao cliente, ou deixe ambos vazios.')
      return
    }
    if ((temCustoOverride || temClienteOverride) && !simTemTefSelecionado) {
      toast.showWarning('Inclua um item TEF na simulação para usar override.')
      return
    }
    setSimLoading(true)
    setSimResult(null)
    try {
      const tef_override =
        temCustoOverride || temClienteOverride
          ? {
              ...(temCustoOverride
                ? { tef_custo_base: simTefCustoBase, tef_custo_adicional: simTefCustoAdic }
                : {}),
              ...(temClienteOverride
                ? {
                    tef_valor_cliente_base: simTefCliBase,
                    tef_valor_cliente_adicional: simTefCliAdic,
                  }
                : {}),
            }
          : null
      const res = await comercialCustosItens.simular({
        item_ids: simSelected,
        quantidade_pdvs: pdvs,
        data_referencia: simData || null,
        desconto_posto_100k: simDescontoPosto,
        tef_override,
      })
      setSimResult(res)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível simular.'))
    } finally {
      setSimLoading(false)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Apenas administradores podem gerenciar o catálogo comercial de custos."
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

  const actionsBtn =
    aba === 'sm' ? (
      <Button
        type="button"
        onClick={() => {
          setSmForm(emptySmForm())
          setSmModal(true)
        }}
      >
        {smTemHistorico ? 'Atualizar valor' : 'Definir SM'}
      </Button>
    ) : aba === 'itens' ? (
      <Button
        type="button"
        onClick={() => {
          setItemEditId(null)
          setItemForm(emptyItem())
          setItemModal(true)
        }}
      >
        Novo item
      </Button>
    ) : null

  const conteudo = (
    <>
      {embedded ? (
        actionsBtn ? <div className="flex justify-end">{actionsBtn}</div> : null
      ) : (
        <PageHeader
          title="Catálogo de custos"
          subtitle="Salário mínimo com vigência, perfis de custo e simulador estimado."
          actions={actionsBtn}
        />
      )}

      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="-mb-px flex gap-1" aria-label="Seções do catálogo de custos">
          {tabBtn('sm', 'Salário mínimo')}
          {tabBtn('itens', 'Itens de custo')}
          {tabBtn('simular', 'Simular')}
        </nav>
      </div>

      {aba === 'sm' ? (
        <div className="space-y-4">
          <Card>
            {smLoading ? (
              <p className="py-8 text-center text-sm text-slate-500">Carregando…</p>
            ) : !smVigente ? (
              <div className="py-10 text-center">
                <p className="text-sm text-slate-500">Nenhum salário mínimo definido ainda.</p>
                <Button
                  type="button"
                  variant="secondary"
                  className="mt-4"
                  onClick={() => {
                    setSmForm(emptySmForm())
                    setSmModal(true)
                  }}
                >
                  Definir SM
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Valor vigente
                </p>
                <p className="text-3xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {fmtMoney(smVigente.valor)}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  Em vigor desde {fmtDataIso(smVigente.vigencia_inicio)}
                </p>
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  Ao atualizar, o valor anterior fica no histórico (não reescreve o passado). Simulações e custos usam o SM
                  da data de referência. A mensalidade do cliente só muda no reajuste do contrato — entre o novo SM e o
                  aniversário do contrato a margem pode apertar.
                </p>
              </div>
            )}
          </Card>

          {smTemHistorico ? (
            <Card>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Histórico de alterações</h3>
                <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <span className="whitespace-nowrap">
                    {smTotal > 0
                      ? `${(smPage - 1) * PAGE_SIZE_PADRAO + 1}–${Math.min(smPage * PAGE_SIZE_PADRAO, smTotal)} de ${smTotal}`
                      : '0'}
                  </span>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={smLoading || smPage <= 1}
                    onClick={() => setSmPage((p) => p - 1)}
                    className="px-2 py-1 text-xs"
                  >
                    Anterior
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={smLoading || smPage >= Math.max(1, Math.ceil(smTotal / PAGE_SIZE_PADRAO))}
                    onClick={() => setSmPage((p) => p + 1)}
                    className="px-2 py-1 text-xs"
                  >
                    Próxima
                  </Button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
                      <th className="px-4 py-3 sm:px-6">Valor</th>
                      <th className="px-4 py-3 sm:px-6">Período</th>
                      <th className="w-px px-4 py-3 text-right sm:px-6">
                        <span className="sr-only">Ações</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {smItems.map((row) => {
                      const vigente = row.vigencia_fim == null
                      return (
                        <tr key={row.id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-white/40">
                          <td className="px-4 py-3.5 font-medium tabular-nums text-slate-800 dark:text-slate-100 sm:px-6">
                            {fmtMoney(row.valor)}
                            {vigente ? (
                              <span className="ml-2 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-600/15 dark:bg-emerald-950/40 dark:text-emerald-300">
                                Vigente
                              </span>
                            ) : null}
                          </td>
                          <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300 sm:px-6">
                            {fmtDataIso(row.vigencia_inicio)}
                            {' → '}
                            {row.vigencia_fim ? fmtDataIso(row.vigencia_fim) : 'hoje'}
                          </td>
                          <td className="px-4 py-3.5 text-right sm:px-6">
                            {!vigente ? (
                              <Button
                                type="button"
                                variant="ghost"
                                className="!px-2 !py-2"
                                aria-label="Excluir registro do histórico"
                                onClick={() =>
                                  setPendingDelete({
                                    kind: 'sm',
                                    id: row.id,
                                    rotulo: `${fmtMoney(row.valor)} (${fmtDataIso(row.vigencia_inicio)} → ${fmtDataIso(row.vigencia_fim)})`,
                                  })
                                }
                              >
                                <IconTrash ariaHidden={false} />
                              </Button>
                            ) : (
                              <span className="sr-only">Sem exclusão do vigente — use Atualizar valor</span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      {aba === 'itens' ? (
        <Card>
          <BarraBuscaPaginacao
            busca={busca}
            onBuscaChange={setBusca}
            placeholder="Buscar por nome…"
            page={itensPage}
            total={itensTotal}
            onPageChange={setItensPage}
            disabled={itensLoading}
            extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
          />
          {itensLoading ? (
            <p className="py-8 text-center text-sm text-slate-500">Carregando…</p>
          ) : itens.length === 0 ? (
            <div className="py-10 text-center">
              <p className="text-sm text-slate-500">Nenhum item de custo cadastrado.</p>
              <Button
                type="button"
                variant="secondary"
                className="mt-4"
                onClick={() => {
                  setItemEditId(null)
                  setItemForm(emptyItem())
                  setItemModal(true)
                }}
              >
                Novo item
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
                    <th className="px-4 py-3 sm:px-6">Nome</th>
                    <th className="px-4 py-3 sm:px-6">Tipo</th>
                    <th className="px-4 py-3 sm:px-6">Parâmetros</th>
                    <th className="w-28 px-4 py-3 sm:px-6">Situação</th>
                    <th className="w-px px-4 py-3 text-right sm:px-6">
                      <span className="sr-only">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {itens.map((item) => (
                    <tr key={item.id} className="transition-colors hover:bg-slate-50/80 dark:hover:bg-white/40">
                      <td className="px-4 py-3.5 font-medium text-slate-800 dark:text-slate-100 sm:px-6">{item.nome}</td>
                      <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300 sm:px-6">
                        {TIPO_LABEL[item.tipo] ?? item.tipo}
                      </td>
                      <td className="px-4 py-3.5 tabular-nums text-slate-600 dark:text-slate-300 sm:px-6">
                        {item.tipo === 'percentual_sm'
                          ? `${fmtPercentual(item.percentual_sm)}${
                              item.aplica_tier_posto ? ' · elegível desconto volume' : ''
                            }`
                          : item.tipo === 'valor_fixo'
                            ? fmtMoney(item.valor_fixo)
                            : `${fmtMoney(item.tef_base)} + ${fmtMoney(item.tef_adicional)}/PDV`}
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
                        <div className="flex justify-end gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            className="!px-2 !py-2"
                            aria-label={`Editar ${item.nome}`}
                            onClick={() => {
                              setItemEditId(item.id)
                              setItemForm({
                                nome: item.nome,
                                slug: item.slug,
                                descricao: item.descricao ?? null,
                                tipo: (item.tipo as ComercialCustos.Tipo) || 'percentual_sm',
                                percentual_sm:
                                  item.percentual_sm != null && item.percentual_sm !== ''
                                    ? String(Math.round(Number(item.percentual_sm)))
                                    : '',
                                valor_fixo: item.valor_fixo ?? '',
                                tef_base: item.tef_base ?? '',
                                tef_adicional: item.tef_adicional ?? '',
                                aplica_tier_posto: !!item.aplica_tier_posto,
                                ordem: item.ordem,
                                ativo: item.ativo,
                                vigencia_inicio: item.vigencia_inicio ?? null,
                                vigencia_fim: item.vigencia_fim ?? null,
                              })
                              setItemModal(true)
                            }}
                          >
                            <IconPencil ariaHidden={false} />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            className="!px-2 !py-2"
                            aria-label={`Excluir ${item.nome}`}
                            onClick={() => setPendingDelete({ kind: 'item', id: item.id, rotulo: item.nome })}
                          >
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
      ) : null}

      {aba === 'simular' ? (
        <Card>
          <div className="space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Selecione perfis/módulos e a quantidade de PDVs para estimar o custo interno. TEF promocional e valor ao
            cliente são overrides só desta simulação (não alteram o catálogo).
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              id="sim-pdvs"
              label="Quantidade de PDVs"
              type="number"
              min={1}
              value={simPdvs}
              onChange={(e) => setSimPdvs(e.target.value)}
            />
            <Input
              id="sim-data"
              label="Data de referência"
              type="date"
              value={simData}
              onChange={(e) => setSimData(e.target.value)}
            />
          </div>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-200">Itens</legend>
            {simCatalogLoading ? (
              <p className="text-sm text-slate-500">Carregando itens…</p>
            ) : simItens.length === 0 ? (
              <p className="text-sm text-slate-500">Cadastre itens ativos na aba «Itens de custo».</p>
            ) : (
              <ul className="max-h-64 space-y-2 overflow-y-auto rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                {simItens.map((item) => {
                  const checked = simSelected.includes(item.id)
                  const tipoLabel = TIPO_LABEL[item.tipo] ?? item.tipo
                  return (
                    <li key={item.id}>
                      <label className="flex cursor-pointer items-start gap-2 text-sm">
                        <input
                          type="checkbox"
                          className="mt-0.5"
                          checked={checked}
                          onChange={() =>
                            setSimSelected((prev) =>
                              checked ? prev.filter((id) => id !== item.id) : [...prev, item.id],
                            )
                          }
                        />
                        <span>
                          <span className="font-medium text-slate-800 dark:text-slate-100">{item.nome}</span>
                          <span className="ml-2 text-xs text-slate-500" aria-hidden>
                            · {tipoLabel}
                            {item.aplica_tier_posto ? ' · elegível desconto volume' : ''}
                          </span>
                        </span>
                      </label>
                    </li>
                  )
                })}
              </ul>
            )}
          </fieldset>
          {simTemPostoTier ? (
            <Switch
              bare
              checked={simDescontoPosto}
              onCheckedChange={setSimDescontoPosto}
              label="Desconto posto menos de 100k L (20% SM)"
              description="Só altera itens marcados como «elegível desconto volume». Se o posto passar de 100k em algum dos 3 primeiros meses, desative."
              showStatusPill
              statusOnText="Ativo"
              statusOffText="Off"
            />
          ) : null}
          {simTemTefSelecionado ? (
            <div className="space-y-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                TEF na proposta (opcional)
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Deixe vazio para usar o padrão do catálogo. Preencha ao ativar oferta do fornecedor ou valor ao cliente.
              </p>
              {simItens.filter((i) => simSelected.includes(i.id) && i.tipo === 'composto_tef').length > 1 ? (
                <p className="rounded-md bg-amber-50 px-2.5 py-1.5 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                  Há mais de um item TEF selecionado — o custo/valor informados abaixo aplicam-se a todos. Em
                  propostas reais, selecione só um TEF.
                </p>
              ) : null}
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  id="sim-tef-custo-base"
                  label="Custo TEF base (1º PDV)"
                  type="number"
                  step="0.01"
                  min={0}
                  value={simTefCustoBase}
                  onChange={(e) => setSimTefCustoBase(e.target.value)}
                />
                <Input
                  id="sim-tef-custo-adic"
                  label="Custo TEF adicional/PDV"
                  type="number"
                  step="0.01"
                  min={0}
                  value={simTefCustoAdic}
                  onChange={(e) => setSimTefCustoAdic(e.target.value)}
                />
                <Input
                  id="sim-tef-cli-base"
                  label="Valor cliente TEF base"
                  type="number"
                  step="0.01"
                  min={0}
                  value={simTefCliBase}
                  onChange={(e) => setSimTefCliBase(e.target.value)}
                />
                <Input
                  id="sim-tef-cli-adic"
                  label="Valor cliente TEF adicional/PDV"
                  type="number"
                  step="0.01"
                  min={0}
                  value={simTefCliAdic}
                  onChange={(e) => setSimTefCliAdic(e.target.value)}
                />
              </div>
            </div>
          ) : null}
          <Button type="button" loading={simLoading} onClick={() => void executarSimulacao()}>
            Calcular estimado
          </Button>
          {simResult ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/40">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                SM na data: {fmtMoney(simResult.salario_minimo)} · PDVs: {simResult.quantidade_pdvs}
                {simResult.desconto_posto_100k ? ' · desconto volume ativo' : ''}
              </p>
              {simResult.desconto_posto_100k ? (
                <p className="mt-1 text-xs text-slate-500">
                  20% SM só nos itens elegíveis a desconto volume; os demais mantêm o % do catálogo.
                </p>
              ) : null}
              <ul className="mt-3 space-y-1 text-sm">
                {simResult.linhas.map((l) => (
                  <li key={l.item_id} className="flex flex-col gap-0.5">
                    <div className="flex justify-between gap-4">
                      <span>
                        {l.nome}
                        {l.percentual_usado != null ? (
                          <span className="ml-1 text-xs text-slate-500">
                            ({fmtPercentual(l.percentual_usado)})
                          </span>
                        ) : null}
                        {l.override_custo ? (
                          <span className="ml-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                            custo promo
                          </span>
                        ) : null}
                      </span>
                      <span className="tabular-nums font-medium">{fmtMoney(l.valor)}</span>
                    </div>
                    {l.tef_valor_cliente != null ? (
                      <p className="text-xs text-slate-500">
                        Valor ao cliente (TEF): {fmtMoney(l.tef_valor_cliente)} — não entra no total de custo
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
              <p className="mt-3 flex justify-between border-t border-slate-200 pt-3 text-base font-semibold dark:border-slate-700">
                <span>Total custo estimado</span>
                <span className="tabular-nums">{fmtMoney(simResult.total_custo ?? simResult.total)}</span>
              </p>
            </div>
          ) : null}
          </div>
        </Card>
      ) : null}

      {smModal ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[2px]"
          role="presentation"
          onClick={() => setSmModal(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="sm-modal-title"
            className={MODAL_PANEL_COMPACT}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="sm-modal-title" className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              {smTemHistorico ? 'Atualizar salário mínimo' : 'Definir salário mínimo'}
            </h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {smTemHistorico
                ? 'O valor atual continua no histórico até o dia anterior à data informada. O passado não é reescrito.'
                : 'Primeiro valor de referência. Depois, use «Atualizar valor» quando o SM oficial mudar.'}
            </p>
            <form
              className="mt-5 space-y-4"
              onSubmit={(e) => {
                e.preventDefault()
                void salvarSm()
              }}
            >
              <Input
                id="sm-valor"
                label="Novo valor (R$)"
                type="number"
                step="0.01"
                min={0.01}
                value={String(smForm.valor)}
                onChange={(e) => setSmForm((f) => ({ ...f, valor: e.target.value }))}
                required
                autoFocus
              />
              <Input
                id="sm-inicio"
                label="Válido a partir de"
                type="date"
                hint={
                  smVigente
                    ? `Deve ser depois de ${fmtDataIso(smVigente.vigencia_inicio)} (início do valor vigente).`
                    : 'Normalmente 1º de janeiro do ano do reajuste.'
                }
                value={smForm.vigencia_inicio}
                onChange={(e) => setSmForm((f) => ({ ...f, vigencia_inicio: e.target.value }))}
                required
              />
              <div className="flex justify-end gap-2 border-t border-slate-200 pt-4 dark:border-slate-800">
                <Button type="button" variant="secondary" onClick={() => setSmModal(false)}>
                  Cancelar
                </Button>
                <Button type="submit" loading={smSaving}>
                  {smTemHistorico ? 'Atualizar' : 'Definir'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {itemModal ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[2px]"
          role="presentation"
          onClick={() => setItemModal(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="item-modal-title"
            className={`${MODAL_PANEL_COMPACT} max-h-[90vh] overflow-y-auto`}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="item-modal-title" className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              {itemEditId != null ? 'Editar item de custo' : 'Novo item de custo'}
            </h3>
            <form
              className="mt-5 space-y-4"
              onSubmit={(e) => {
                e.preventDefault()
                void salvarItem()
              }}
            >
              <Input
                id="item-nome"
                label="Nome"
                value={itemForm.nome}
                onChange={(e) => setItemForm((f) => ({ ...f, nome: e.target.value }))}
                required
                autoFocus
              />
              <Select
                id="item-tipo"
                label="Tipo"
                value={itemForm.tipo}
                onChange={(v) =>
                  setItemForm((f) => ({
                    ...f,
                    tipo: (String(v) as ComercialCustos.Tipo) || 'percentual_sm',
                  }))
                }
                options={[
                  { value: 'percentual_sm', label: TIPO_LABEL.percentual_sm },
                  { value: 'valor_fixo', label: TIPO_LABEL.valor_fixo },
                  { value: 'composto_tef', label: TIPO_LABEL.composto_tef },
                ]}
              />
              {itemForm.tipo === 'percentual_sm' ? (
                <>
                  <Input
                    id="item-pct"
                    label="Percentual do SM (%)"
                    type="number"
                    step="1"
                    min={0}
                    hint="Somente números inteiros (ex.: 30). Com desconto <100k na simulação, passa a 20%."
                    value={String(itemForm.percentual_sm ?? '')}
                    onChange={(e) => {
                      const raw = e.target.value
                      if (raw === '') {
                        setItemForm((f) => ({ ...f, percentual_sm: '' }))
                        return
                      }
                      const n = Math.round(Number(raw))
                      if (!Number.isNaN(n)) setItemForm((f) => ({ ...f, percentual_sm: String(n) }))
                    }}
                    required
                  />
                  <Switch
                    bare
                    checked={!!itemForm.aplica_tier_posto}
                    onCheckedChange={(aplica_tier_posto) => setItemForm((f) => ({ ...f, aplica_tier_posto }))}
                    label="Elegível a desconto posto <100k L"
                    description="Marque em itens de posto: na simulação dá para ativar 20% SM quando o cliente declara volume baixo."
                    showStatusPill
                    statusOnText="Sim"
                    statusOffText="Não"
                  />
                </>
              ) : null}
              {itemForm.tipo === 'valor_fixo' ? (
                <Input
                  id="item-fixo"
                  label="Valor fixo (R$)"
                  type="number"
                  step="0.01"
                  min={0}
                  value={String(itemForm.valor_fixo ?? '')}
                  onChange={(e) => setItemForm((f) => ({ ...f, valor_fixo: e.target.value }))}
                  required
                />
              ) : null}
              {itemForm.tipo === 'composto_tef' ? (
                <>
                  <Input
                    id="item-tef-base"
                    label="TEF base (1º PDV)"
                    type="number"
                    step="0.01"
                    min={0}
                    value={String(itemForm.tef_base ?? '')}
                    onChange={(e) => setItemForm((f) => ({ ...f, tef_base: e.target.value }))}
                    required
                  />
                  <Input
                    id="item-tef-adic"
                    label="TEF adicional por PDV"
                    type="number"
                    step="0.01"
                    min={0}
                    value={String(itemForm.tef_adicional ?? '')}
                    onChange={(e) => setItemForm((f) => ({ ...f, tef_adicional: e.target.value }))}
                    required
                  />
                </>
              ) : null}
              <Switch
                bare
                checked={itemForm.ativo ?? true}
                onCheckedChange={(ativo) => setItemForm((f) => ({ ...f, ativo }))}
                label="Ativo"
                showStatusPill
              />
              <div className="flex justify-end gap-2 border-t border-slate-200 pt-4 dark:border-slate-800">
                <Button type="button" variant="secondary" onClick={() => setItemModal(false)}>
                  Cancelar
                </Button>
                <Button type="submit" loading={itemSaving}>
                  Salvar
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={pendingDelete != null}
        title={pendingDelete?.kind === 'sm' ? 'Excluir salário mínimo?' : 'Excluir item de custo?'}
        message={
          pendingDelete?.kind === 'sm'
            ? `Remover ${pendingDelete.rotulo} do histórico. Só use para corrigir cadastro errado — o normal é só atualizar o valor vigente.`
            : `Remover «${pendingDelete?.rotulo ?? ''}» do catálogo e do simulador.`
        }
        confirmLabel="Excluir"
        variant="danger"
        loading={deleteLoading}
        onConfirm={() => void confirmarExclusao()}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  )

  return embedded ? conteudo : <PageContainer>{conteudo}</PageContainer>
}
