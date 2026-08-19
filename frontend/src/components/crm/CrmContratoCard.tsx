import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  comercialContratoTemplates,
  comercialContratos,
  type ComercialContrato,
  type Crm,
} from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { useToast } from '../ui/Toast'
import { maskCnpjCpf } from '../../utils/maskCnpjCpf'

const STATUS_LABEL: Record<string, string> = {
  rascunho: 'Rascunho',
  enviado: 'Enviado',
  assinado: 'Assinado',
  cancelado: 'Cancelado',
  renovado: 'Renovado',
}

const ATIVOS = new Set(['rascunho', 'enviado', 'assinado'])

function money(v: string | number | null | undefined): string {
  if (v == null || v === '') return '—'
  const n = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function percent(v: string | number | null | undefined): string {
  if (v == null || v === '') return '—'
  const n = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(n)) return String(v)
  return `${n.toLocaleString('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 0 })}%`
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('pt-BR')
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function textoDiasFidelidade(dias: number | null | undefined): string {
  if (dias == null) return '—'
  if (dias > 1) return `${dias} dias restantes`
  if (dias === 1) return '1 dia restante'
  if (dias === 0) return 'Encerra hoje'
  const abs = Math.abs(dias)
  return abs === 1 ? 'Fidelidade encerrada há 1 dia' : `Fidelidade encerrada há ${abs} dias`
}

type Props = {
  negociacao: Crm.Negociacao
  onChanged: () => void
  /** Sem o Card externo — o título fica no acordeão da página. */
  embedded?: boolean
}

export function CrmContratoCard({ negociacao, onChanged, embedded = false }: Props) {
  const toast = useToast()
  const linhas = negociacao.linhas || []

  const [templates, setTemplates] = useState<ComercialContrato.Template[]>([])
  const [contratos, setContratos] = useState<ComercialContrato.Contrato[]>([])
  const [linhaId, setLinhaId] = useState<number | ''>('')
  const [templateId, setTemplateId] = useState<number | ''>('')
  const [dataInicio, setDataInicio] = useState('')
  const [fidelidadeMeses, setFidelidadeMeses] = useState('12')
  const [setupValor, setSetupValor] = useState('')
  const [setupIsento, setSetupIsento] = useState(false)
  const [deslocamento, setDeslocamento] = useState(true)
  const [alimentacao, setAlimentacao] = useState(true)
  const [hospedagem, setHospedagem] = useState(true)
  const [multaMax, setMultaMax] = useState('3')
  const [gerando, setGerando] = useState(false)
  const [preview, setPreview] = useState<ComercialContrato.Contrato | null>(null)
  const [baixandoId, setBaixandoId] = useState<number | null>(null)
  const [enviandoId, setEnviandoId] = useState<number | null>(null)
  const [assinandoId, setAssinandoId] = useState<number | null>(null)
  const [avancarFunil, setAvancarFunil] = useState(true)
  const [cancelarId, setCancelarId] = useState<number | null>(null)
  const [cancelando, setCancelando] = useState(false)

  const load = useCallback(async () => {
    const [tmpls, rows] = await Promise.all([
      comercialContratoTemplates.list(),
      comercialContratos.list({ negociacao_id: negociacao.id }),
    ])
    setTemplates(tmpls)
    setContratos(rows)
    setTemplateId((prev) => {
      if (prev !== '' && tmpls.some((t) => t.id === prev)) return prev
      return tmpls[0]?.id ?? ''
    })
    const ativo = rows.find((c) => ATIVOS.has(c.status))
    setPreview((atual) => {
      if (atual && rows.some((c) => c.id === atual.id)) {
        return rows.find((c) => c.id === atual.id) || ativo || rows[0] || null
      }
      return ativo || rows[0] || null
    })
  }, [negociacao.id])

  useEffect(() => {
    void load().catch((err) => {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os contratos.'))
    })
  }, [load, toast])

  useEffect(() => {
    setLinhaId((prev) => {
      if (prev !== '' && linhas.some((ln) => ln.id === prev)) return prev
      return linhas[0]?.id ?? ''
    })
  }, [linhas])

  const templateOptions = useMemo(
    () => templates.map((t) => ({ value: String(t.id), label: `${t.nome} (v${t.versao})` })),
    [templates],
  )

  const linhaOptions = useMemo(
    () =>
      linhas.map((ln) => ({
        value: String(ln.id),
        label: `${ln.razao_social || 'Sem razão social'} · ${ln.cnpj ? maskCnpjCpf(ln.cnpj) : 'sem CNPJ'}`,
      })),
    [linhas],
  )

  const linhaSel = linhas.find((ln) => ln.id === linhaId)
  const contratoDaLinha = contratos.find(
    (c) => c.negociacao_linha_cnpj_id === linhaId && ATIVOS.has(c.status),
  )
  const podeGerar =
    linhaId !== '' && (!contratoDaLinha || contratoDaLinha.status === 'rascunho')

  useEffect(() => {
    if (!preview?.conteudo_html_snapshot && preview?.id) {
      void comercialContratos
        .get(preview.id)
        .then((full) => setPreview(full))
        .catch(() => undefined)
    }
  }, [preview?.id, preview?.conteudo_html_snapshot])

  async function handleGerar() {
    if (linhaId === '') {
      toast.showWarning('Selecione o CNPJ do contrato.')
      return
    }
    const meses = Number(fidelidadeMeses)
    if (!Number.isInteger(meses) || meses < 1 || meses > 60) {
      toast.showWarning('Fidelidade deve ser entre 1 e 60 meses.')
      return
    }
    const multa = Number(multaMax)
    if (!Number.isInteger(multa) || multa < 0 || multa > 12) {
      toast.showWarning('Multa deve ser entre 0 e 12 mensalidades.')
      return
    }
    setGerando(true)
    try {
      const row = await comercialContratos.gerar({
        linha_id: linhaId,
        template_id: templateId === '' ? null : templateId,
        data_inicio: dataInicio || null,
        fidelidade_meses: meses,
        setup_valor: setupIsento ? null : setupValor.trim() || null,
        setup_isento: setupIsento,
        deslocamento_cliente: deslocamento,
        alimentacao_cliente: alimentacao,
        hospedagem_cliente: hospedagem,
        multa_max_mensalidades: multa,
      })
      setPreview(row)
      toast.showSuccess(
        contratoDaLinha ? 'Contrato atualizado. Revise o preview.' : 'Contrato gerado. Revise o preview.',
      )
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível gerar o contrato.'))
    } finally {
      setGerando(false)
    }
  }

  async function handlePdf(id: number) {
    setBaixandoId(id)
    try {
      const blob = await comercialContratos.downloadPdf(id)
      downloadBlob(blob, `contrato-${id}.pdf`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível baixar o PDF.'))
    } finally {
      setBaixandoId(null)
    }
  }

  async function handleEnviado(id: number) {
    setEnviandoId(id)
    try {
      const row = await comercialContratos.marcarEnviado(id)
      setPreview(row)
      toast.showSuccess('Contrato marcado como enviado (registro manual).')
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível marcar como enviado.'))
    } finally {
      setEnviandoId(null)
    }
  }

  async function handleAssinado(id: number) {
    setAssinandoId(id)
    try {
      const row = await comercialContratos.marcarAssinado(id, { avancar_funil: avancarFunil })
      setPreview(row)
      toast.showSuccess(
        avancarFunil ? 'Contrato assinado e funil atualizado.' : 'Contrato marcado como assinado.',
      )
      setAssinandoId(null)
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível marcar como assinado.'))
      setAssinandoId(null)
    }
  }

  async function handleCancelar() {
    if (cancelarId == null) return
    setCancelando(true)
    try {
      await comercialContratos.cancelar(cancelarId)
      toast.showSuccess('Contrato cancelado.')
      setCancelarId(null)
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível cancelar o contrato.'))
    } finally {
      setCancelando(false)
    }
  }

  const interno = preview?.interno
  const linhaInterno = linhaSel

  const inner = (
    <>
      <p className="mb-3 text-sm text-slate-500">
        Um contrato por CNPJ. O PDF do cliente não inclui custo nem margem — esses valores ficam só neste
        painel.
      </p>

      {linhas.length === 0 ? (
        <p className="text-sm text-slate-500">Cadastre linhas CNPJ para gerar o contrato.</p>
      ) : (
        <div className="space-y-3">
          <Select
            label="CNPJ"
            value={linhaId === '' ? '' : String(linhaId)}
            onChange={(v) => setLinhaId(v ? Number(v) : '')}
            options={linhaOptions}
          />
          {contratoDaLinha && contratoDaLinha.status !== 'rascunho' ? (
            <p className="text-xs text-amber-800 dark:text-amber-200">
              Esta linha já tem contrato {STATUS_LABEL[contratoDaLinha.status] || contratoDaLinha.status}.
              Para gerar outro, cancele o atual (não é possível após assinado).
            </p>
          ) : null}
          {podeGerar ? (
            <>
          {templateOptions.length > 0 ? (
            <Select
              label="Modelo"
              value={templateId === '' ? '' : String(templateId)}
              onChange={(v) => setTemplateId(v ? Number(v) : '')}
              options={templateOptions}
            />
          ) : (
            <p className="text-xs text-slate-500">Nenhum modelo ativo. O sistema usa o padrão na primeira geração.</p>
          )}
          <div className="grid gap-3 sm:grid-cols-3">
            <Input
              label="Início da vigência"
              type="date"
              hint="Vazio = hoje"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
            />
            <Input
              label="Fidelidade (meses)"
              type="number"
              min={1}
              max={60}
              value={fidelidadeMeses}
              onChange={(e) => setFidelidadeMeses(e.target.value)}
            />
            <Input
              label="Multa (mensalidades)"
              type="number"
              min={0}
              max={12}
              value={multaMax}
              onChange={(e) => setMultaMax(e.target.value)}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Setup (fora da mensalidade)"
              type="number"
              step="0.01"
              min={0}
              value={setupValor}
              onChange={(e) => setSetupValor(e.target.value)}
              disabled={setupIsento}
              placeholder="Valor único de implantação"
            />
            <label className="flex items-center gap-2 pt-6 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={setupIsento}
                onChange={(e) => setSetupIsento(e.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Setup isento
            </label>
          </div>
          <div className="flex flex-wrap gap-4 text-sm text-slate-700 dark:text-slate-300">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={deslocamento}
                onChange={(e) => setDeslocamento(e.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Deslocamento por conta do cliente
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={alimentacao}
                onChange={(e) => setAlimentacao(e.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Alimentação por conta do cliente
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={hospedagem}
                onChange={(e) => setHospedagem(e.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Hospedagem por conta do cliente
            </label>
          </div>
          <Button onClick={() => void handleGerar()} disabled={gerando}>
            {gerando
              ? 'Gerando…'
              : contratoDaLinha?.status === 'rascunho'
                ? 'Atualizar contrato'
                : 'Gerar contrato'}
          </Button>
            </>
          ) : null}
        </div>
      )}

      {preview ? (
        <div className="mt-4 space-y-3">
          <div className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800/50">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
              Painel interno (não vai no PDF)
            </p>
            <div className="grid gap-2 sm:grid-cols-3">
              <div>
                <div className="text-xs text-slate-500">Custo</div>
                <div className="font-semibold">{money(interno?.total_custo ?? linhaInterno?.total_custo)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Lucro bruto</div>
                <div className="font-semibold">{money(interno?.lucro_bruto)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Margem</div>
                <div className="font-semibold">{percent(interno?.margem_percentual)}</div>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Preview — contrato #{preview.id} ({STATUS_LABEL[preview.status] || preview.status})
              </p>
              <p className="text-xs text-slate-500">
                {preview.razao_social || '—'} · {preview.cnpj ? maskCnpjCpf(preview.cnpj) : 'sem CNPJ'} · mensalidade{' '}
                {money(preview.valor_mensalidade)} · fidelidade {preview.fidelidade_meses} meses (
                {textoDiasFidelidade(preview.dias_restantes_fidelidade)})
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => void handlePdf(preview.id)}
                disabled={baixandoId === preview.id}
              >
                {baixandoId === preview.id ? 'Baixando…' : 'Baixar PDF'}
              </Button>
              {preview.status === 'rascunho' ? (
                <Button
                  variant="secondary"
                  onClick={() => void handleEnviado(preview.id)}
                  disabled={enviandoId === preview.id}
                >
                  {enviandoId === preview.id ? 'Salvando…' : 'Marcar enviado'}
                </Button>
              ) : null}
              {preview.status === 'rascunho' || preview.status === 'enviado' ? (
                <>
                  <Button variant="secondary" onClick={() => setAssinandoId(preview.id)}>
                    Marcar assinado
                  </Button>
                  <Button variant="ghost" onClick={() => setCancelarId(preview.id)}>
                    Cancelar contrato
                  </Button>
                </>
              ) : null}
            </div>
          </div>
          <iframe
            title={`Preview do contrato ${preview.id}`}
            sandbox=""
            srcDoc={preview.conteudo_html_snapshot || ''}
            className="h-80 w-full rounded-lg border border-slate-200 bg-white dark:border-slate-700"
          />
        </div>
      ) : null}

      {contratos.length > 1 ? (
        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Contratos desta negociação</p>
          <ul className="space-y-2 text-sm">
            {contratos.map((c) => (
              <li
                key={c.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700"
              >
                <div>
                  <span className="font-medium text-slate-900 dark:text-slate-100">#{c.id}</span>
                  {' · '}
                  {STATUS_LABEL[c.status] || c.status}
                  {' · '}
                  {c.razao_social || (c.cnpj ? maskCnpjCpf(c.cnpj) : `linha ${c.negociacao_linha_cnpj_id}`)}
                  <div className="text-xs text-slate-500">
                    {formatDateTime(c.created_at)}
                    {c.enviado_em ? ` · enviado ${formatDateTime(c.enviado_em)}` : ''}
                    {c.assinado_em ? ` · assinado ${formatDateTime(c.assinado_em)}` : ''}
                    {' · '}
                    {textoDiasFidelidade(c.dias_restantes_fidelidade)}
                    {c.data_fim_fidelidade ? ` (até ${formatDate(c.data_fim_fidelidade)})` : ''}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={() => setPreview(c)}>
                    Ver
                  </Button>
                  <Button variant="ghost" onClick={() => void handlePdf(c.id)} disabled={baixandoId === c.id}>
                    PDF
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {assinandoId != null ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div className="w-full rounded-t-2xl bg-white p-5 shadow-xl dark:bg-slate-900 sm:max-w-md sm:rounded-2xl">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Marcar contrato como assinado</h2>
            <p className="mt-1 text-sm text-slate-500">
              Registro manual — a assinatura eletrónica (ClickSign) fica para um lote seguinte.
            </p>
            <label className="mt-4 inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={avancarFunil}
                onChange={(e) => setAvancarFunil(e.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Avançar funil para «Contrato assinado»
            </label>
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="secondary" onClick={() => setAssinandoId(null)}>
                Voltar
              </Button>
              <Button onClick={() => void handleAssinado(assinandoId)}>Confirmar</Button>
            </div>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={cancelarId != null}
        title="Cancelar contrato?"
        message="O rascunho ou o enviado deixa de valer. Depois de assinado não dá para cancelar nesta tela."
        confirmLabel="Cancelar contrato"
        cancelLabel="Voltar"
        variant="danger"
        loading={cancelando}
        onConfirm={() => void handleCancelar()}
        onCancel={() => setCancelarId(null)}
      />
    </>
  )

  if (embedded) return inner
  return <Card title="Contrato comercial">{inner}</Card>
}
