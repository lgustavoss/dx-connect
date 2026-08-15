import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ApiError,
  comercialCustosItens,
  crmFunil,
  crmLeads,
  crmNegociacoes,
  type ComercialCustos,
  type Crm,
} from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'

const TIPO_ATIVIDADE_LABEL: Record<string, string> = {
  nota: 'Nota',
  ligacao: 'Ligação',
  reuniao: 'Reunião',
  mudanca_estagio: 'Estágio',
  documento_anexado: 'Documento',
}

const TIPO_CUSTO_LABEL: Record<string, string> = {
  percentual_sm: '% salário mínimo',
  valor_fixo: 'Valor fixo',
  composto_tef: 'TEF (base + adicional)',
}

function rotuloItemCusto(item: ComercialCustos.Item): string {
  const tipo = TIPO_CUSTO_LABEL[item.tipo] || null
  return tipo ? `${item.nome} · ${tipo}` : item.nome
}

function money(v: string | number | null | undefined): string {
  if (v == null || v === '') return '—'
  const n = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function margemBaixa(linha: Crm.Linha): boolean {
  const valor = Number(linha.valor_negociado || 0)
  const margem = Number(linha.margem_calculada ?? NaN)
  if (Number.isNaN(margem)) return false
  if (margem < 0) return true
  if (valor > 0 && margem / valor < 0.1) return true
  return false
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

type LinhaForm = {
  cnpj: string
  razao_social: string
  valor_negociado: string
  quantidade_pdvs: string
  desconto_posto_100k: boolean
  item_ids: number[]
}

const emptyLinhaForm = (): LinhaForm => ({
  cnpj: '',
  razao_social: '',
  valor_negociado: '0',
  quantidade_pdvs: '1',
  desconto_posto_100k: false,
  item_ids: [],
})

export function CrmNegociacaoDetalhe() {
  const { id } = useParams<{ id: string }>()
  const negociacaoId = id ? parseInt(id, 10) : NaN
  const voltar = useVoltarAnterior('/crm/leads')
  const toast = useToast()

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [neg, setNeg] = useState<Crm.Negociacao | null>(null)
  const [lead, setLead] = useState<Crm.Lead | null>(null)
  const [estagios, setEstagios] = useState<Crm.FunilEstagio[]>([])
  const [itensCatalogo, setItensCatalogo] = useState<ComercialCustos.Item[]>([])
  const [atividades, setAtividades] = useState<Crm.Atividade[]>([])

  const [destinoEstagio, setDestinoEstagio] = useState<number | ''>('')
  const [notaEstagio, setNotaEstagio] = useState('')
  const [movendo, setMovendo] = useState(false)

  const [linhaModal, setLinhaModal] = useState<'create' | Crm.Linha | null>(null)
  const [linhaForm, setLinhaForm] = useState<LinhaForm>(emptyLinhaForm)
  const [savingLinha, setSavingLinha] = useState(false)
  const [deleteLinhaId, setDeleteLinhaId] = useState<number | null>(null)

  const [notaTexto, setNotaTexto] = useState('')
  const [savingNota, setSavingNota] = useState(false)

  const load = useCallback(async () => {
    if (!id || Number.isNaN(negociacaoId)) {
      setFalha({ titulo: 'Negociação não encontrada.', detalhe: 'Identificador inválido na URL.' })
      setLoading(false)
      return
    }
    setLoading(true)
    setForbidden(false)
    setFalha(null)
    try {
      const n = await crmNegociacoes.get(negociacaoId)
      setNeg(n)
      setDestinoEstagio('')
      const [l, funil, acts] = await Promise.all([
        crmLeads.get(n.lead_id),
        crmFunil.list(),
        crmNegociacoes.listAtividades(negociacaoId, { limit: 50, offset: 0 }),
      ])
      setLead(l)
      setEstagios(funil)
      setAtividades(acts.items)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true)
        return
      }
      const m = interpretarFalhaCarregamento(err, 'Negociação não encontrada.')
      setFalha({ titulo: m.titulo, detalhe: m.detalhe })
    } finally {
      setLoading(false)
    }
  }, [id, negociacaoId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    coletarTodasPaginas<ComercialCustos.Item>((offset, limit) =>
      comercialCustosItens.list({ offset, limit, incluir_inativos: false }),
    )
      .then((items) =>
        // Oculta cadastros de teste gerados em QA (ex.: "Posto UX 182304")
        setItensCatalogo(items.filter((i) => !/\bUX\s*\d{5,}\b/i.test(i.nome))),
      )
      .catch(() => setItensCatalogo([]))
  }, [])

  const totais = useMemo(() => {
    const linhas = neg?.linhas ?? []
    let valor = 0
    let custo = 0
    for (const ln of linhas) {
      valor += Number(ln.valor_negociado || 0)
      custo += Number(ln.total_custo || 0)
    }
    return { valor, custo, margem: valor - custo }
  }, [neg])

  function openCreateLinha() {
    setLinhaForm(emptyLinhaForm())
    setLinhaModal('create')
  }

  function openEditLinha(ln: Crm.Linha) {
    setLinhaForm({
      cnpj: ln.cnpj || '',
      razao_social: ln.razao_social || '',
      valor_negociado: String(ln.valor_negociado ?? '0'),
      quantidade_pdvs: String(ln.quantidade_pdvs ?? 1),
      desconto_posto_100k: Boolean(ln.desconto_posto_100k),
      item_ids: [...(ln.item_ids || [])],
    })
    setLinhaModal(ln)
  }

  function toggleItem(itemId: number) {
    setLinhaForm((prev) => ({
      ...prev,
      item_ids: prev.item_ids.includes(itemId)
        ? prev.item_ids.filter((x) => x !== itemId)
        : [...prev.item_ids, itemId],
    }))
  }

  async function saveLinha(e: React.FormEvent) {
    e.preventDefault()
    if (!neg) return
    setSavingLinha(true)
    try {
      const payload = {
        cnpj: linhaForm.cnpj.trim() || null,
        razao_social: linhaForm.razao_social.trim() || null,
        valor_negociado: linhaForm.valor_negociado || '0',
        quantidade_pdvs: Math.max(1, parseInt(linhaForm.quantidade_pdvs, 10) || 1),
        desconto_posto_100k: linhaForm.desconto_posto_100k,
        item_ids: linhaForm.item_ids,
      }
      if (linhaModal === 'create') {
        await crmNegociacoes.addLinha(neg.id, payload)
        toast.showSuccess('Linha CNPJ adicionada.')
      } else if (linhaModal && typeof linhaModal === 'object') {
        await crmNegociacoes.updateLinha(neg.id, linhaModal.id, payload)
        toast.showSuccess('Linha atualizada (custo/margem recalculados).')
      }
      setLinhaModal(null)
      await load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a linha.'))
    } finally {
      setSavingLinha(false)
    }
  }

  async function confirmDeleteLinha() {
    if (!neg || deleteLinhaId == null) return
    try {
      await crmNegociacoes.deleteLinha(neg.id, deleteLinhaId)
      toast.showSuccess('Linha removida.')
      setDeleteLinhaId(null)
      await load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível remover a linha.'))
    }
  }

  async function handleMoverEstagio() {
    if (!neg || destinoEstagio === '') {
      toast.showWarning('Escolha o estágio de destino.')
      return
    }
    setMovendo(true)
    try {
      await crmNegociacoes.moverEstagio(neg.id, {
        estagio_id: Number(destinoEstagio),
        nota: notaEstagio.trim() || null,
      })
      toast.showSuccess('Estágio atualizado.')
      setNotaEstagio('')
      await load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível mover o estágio.'))
    } finally {
      setMovendo(false)
    }
  }

  async function handleAddNota(e: React.FormEvent) {
    e.preventDefault()
    if (!neg || !notaTexto.trim()) return
    setSavingNota(true)
    try {
      await crmNegociacoes.addAtividade(neg.id, { tipo: 'nota', texto: notaTexto.trim() })
      setNotaTexto('')
      toast.showSuccess('Nota registrada.')
      const acts = await crmNegociacoes.listAtividades(neg.id, { limit: 50, offset: 0 })
      setAtividades(acts.items)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a nota.'))
    } finally {
      setSavingNota(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl pb-10">
        <div className="h-72 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver esta negociação."
        voltarPara="/crm/leads"
        voltarLabel="Voltar para CRM"
      />
    )
  }

  if (falha || !neg) {
    return (
      <CarregamentoFalhou
        className="mx-auto max-w-5xl space-y-4 pb-10"
        titulo={falha?.titulo || 'Negociação não encontrada.'}
        detalhe={falha?.detalhe}
        onVoltar={voltar}
      />
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 pb-10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <button
            type="button"
            onClick={voltar}
            className="text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          >
            ← Voltar
          </button>
          <h1 className="mt-1 text-xl font-semibold text-slate-900 dark:text-slate-100">
            {neg.titulo || `Negociação #${neg.id}`}
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Lead:{' '}
            <span className="font-medium text-slate-700 dark:text-slate-200">{lead?.nome || `#${neg.lead_id}`}</span>
            {' · '}
            Estágio: <span className="font-medium">{neg.estagio_nome || '—'}</span>
            {!neg.ativa ? ' · encerrada' : null}
          </p>
        </div>
        <Link
          to="/crm/leads"
          className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-400"
        >
          Lista de leads
        </Link>
      </div>

      <Card title="Avançar estágio">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-[200px] flex-1">
            <Select
              label="Novo estágio"
              value={destinoEstagio}
              onChange={(v) => setDestinoEstagio(v === '' ? '' : Number(v))}
              options={estagios
                .filter((e) => e.id !== neg.estagio_id)
                .map((e) => ({ value: e.id, label: e.nome }))}
              includeEmpty
              emptyLabel="Selecionar…"
              disabled={!neg.ativa && neg.estagio_slug === 'perdido' ? false : !neg.ativa}
            />
          </div>
          <div className="flex-1">
            <Input
              label="Nota (opcional)"
              value={notaEstagio}
              onChange={(e) => setNotaEstagio(e.target.value)}
            />
          </div>
          <Button onClick={handleMoverEstagio} disabled={movendo || destinoEstagio === ''}>
            {movendo ? 'Movendo…' : 'Mover'}
          </Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          A partir de Documentação, o CNPJ é obrigatório em todas as linhas. Sem CNPJ válido, o avanço para esse estágio
          (e posteriores) fica bloqueado.
        </p>
      </Card>

      <Card title="Linhas por CNPJ">
        <div className="mb-3 flex justify-end">
          <Button variant="secondary" onClick={openCreateLinha}>
            Adicionar linha
          </Button>
        </div>
        <div className="mb-3 grid gap-2 rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/50 sm:grid-cols-3">
          <div>
            <div className="text-xs text-slate-500">Valor negociado</div>
            <div className="font-semibold text-slate-900 dark:text-slate-100">{money(totais.valor)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Custo estimado (interno)</div>
            <div className="font-semibold text-slate-900 dark:text-slate-100">{money(totais.custo)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Margem total</div>
            <div
              className={`font-semibold ${
                totais.margem < 0 || (totais.valor > 0 && totais.margem / totais.valor < 0.1)
                  ? 'text-amber-700 dark:text-amber-300'
                  : 'text-emerald-700 dark:text-emerald-300'
              }`}
            >
              {money(totais.margem)}
            </div>
          </div>
        </div>

        {(neg.linhas || []).length === 0 ? (
          <p className="text-sm text-slate-500">Nenhuma linha CNPJ ainda.</p>
        ) : (
          <div className="space-y-3">
            {(neg.linhas || []).map((ln) => (
              <div
                key={ln.id}
                className={`rounded-xl border p-3 ${
                  margemBaixa(ln)
                    ? 'border-amber-300 bg-amber-50/60 dark:border-amber-800 dark:bg-amber-950/30'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-900 dark:text-slate-100">
                      {ln.razao_social || 'Sem razão social'}
                    </div>
                    <div className="text-xs text-slate-500">
                      CNPJ: {ln.cnpj || '— (opcional até Documentação)'} · PDVs: {ln.quantidade_pdvs}
                      {ln.desconto_posto_100k ? ' · desconto posto <100k' : ''}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      Pacote:{' '}
                      {ln.item_ids?.length
                        ? ln.item_ids
                            .map((iid) => itensCatalogo.find((i) => i.id === iid)?.nome || `#${iid}`)
                            .join(', ')
                        : '—'}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" onClick={() => openEditLinha(ln)}>
                      Editar
                    </Button>
                    <Button variant="ghost" onClick={() => setDeleteLinhaId(ln.id)}>
                      Remover
                    </Button>
                  </div>
                </div>
                <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
                  <div>
                    Valor: <strong>{money(ln.valor_negociado)}</strong>
                  </div>
                  <div>
                    Custo: <strong>{money(ln.total_custo)}</strong>
                  </div>
                  <div className={margemBaixa(ln) ? 'text-amber-800 dark:text-amber-200' : ''}>
                    Margem: <strong>{money(ln.margem_calculada)}</strong>
                    {margemBaixa(ln) ? ' · margem baixa' : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Histórico">
        <form onSubmit={handleAddNota} className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Input
              label="Nova nota"
              value={notaTexto}
              onChange={(e) => setNotaTexto(e.target.value)}
              placeholder="Registrar contato, reunião…"
            />
          </div>
          <Button type="submit" disabled={savingNota || !notaTexto.trim()}>
            {savingNota ? 'Salvando…' : 'Adicionar'}
          </Button>
        </form>
        {atividades.length === 0 ? (
          <p className="text-sm text-slate-500">Sem atividades ainda.</p>
        ) : (
          <ul className="space-y-3">
            {atividades.map((a) => (
              <li
                key={a.id}
                className="border-l-2 border-slate-200 pl-3 dark:border-slate-700"
              >
                <div className="flex flex-wrap items-baseline gap-2 text-xs text-slate-500">
                  <span className="font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                    {TIPO_ATIVIDADE_LABEL[a.tipo] || a.tipo}
                  </span>
                  <span>{formatDateTime(a.created_at)}</span>
                </div>
                <p className="mt-0.5 text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{a.texto}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {linhaModal ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl dark:bg-slate-900 sm:max-w-lg sm:rounded-2xl">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {linhaModal === 'create' ? 'Nova linha CNPJ' : 'Editar linha'}
            </h2>
            <form onSubmit={saveLinha} className="mt-4 space-y-3">
              <Input
                label="CNPJ"
                value={linhaForm.cnpj}
                onChange={(e) => setLinhaForm((p) => ({ ...p, cnpj: e.target.value }))}
                placeholder="Opcional até Documentação"
              />
              <Input
                label="Razão social"
                value={linhaForm.razao_social}
                onChange={(e) => setLinhaForm((p) => ({ ...p, razao_social: e.target.value }))}
              />
              <Input
                label="Valor negociado (R$)"
                value={linhaForm.valor_negociado}
                onChange={(e) => setLinhaForm((p) => ({ ...p, valor_negociado: e.target.value }))}
              />
              <Input
                label="Quantidade de PDVs"
                value={linhaForm.quantidade_pdvs}
                onChange={(e) => setLinhaForm((p) => ({ ...p, quantidade_pdvs: e.target.value }))}
              />
              <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={linhaForm.desconto_posto_100k}
                  onChange={(e) =>
                    setLinhaForm((p) => ({ ...p, desconto_posto_100k: e.target.checked }))
                  }
                  className="size-4 rounded border-slate-300"
                />
                Desconto posto &lt;100k L (20% SM)
              </label>
              <div>
                <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Composição do pacote</p>
                {itensCatalogo.length === 0 ? (
                  <p className="text-xs text-slate-500">
                    Nenhum item no catálogo (ou sem permissão de leitura). Peça ao admin para cadastrar custos.
                  </p>
                ) : (
                  <div className="max-h-40 space-y-1 overflow-auto rounded-lg border border-slate-200 p-2 dark:border-slate-700">
                    {itensCatalogo.map((item) => (
                      <label
                        key={item.id}
                        className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      >
                        <input
                          type="checkbox"
                          checked={linhaForm.item_ids.includes(item.id)}
                          onChange={() => toggleItem(item.id)}
                          className="size-4 rounded border-slate-300"
                        />
                        <span className="min-w-0 flex-1">{rotuloItemCusto(item)}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <Button type="button" variant="secondary" onClick={() => setLinhaModal(null)} disabled={savingLinha}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={savingLinha}>
                  {savingLinha ? 'Salvando…' : 'Salvar'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={deleteLinhaId != null}
        title="Remover linha CNPJ?"
        message="Esta ação não apaga o histórico da negociação, só esta linha."
        confirmLabel="Remover"
        variant="danger"
        onConfirm={confirmDeleteLinha}
        onCancel={() => setDeleteLinhaId(null)}
      />
    </div>
  )
}
