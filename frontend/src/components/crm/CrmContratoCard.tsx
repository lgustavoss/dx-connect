import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  comercialContratoPolitica,
  comercialContratoTemplates,
  comercialContratos,
  crmNegociacoes,
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
import { CrmDadosFiscaisFields } from './CrmDadosFiscaisFields'
import { emptyFiscal, fiscaisDaLinha, fiscalPayload, formatPercentualPt, parsePercentualPt } from './crmFiscais'
import { marcarTicketAtivo, TICKETS_PATH } from '../../lib/ticketAtivo'
import { exibirProtocolo } from '../../lib/exibirProtocolo'

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

function pluralPt(n: number, singular: string, plural: string): string {
  return `${n} ${n === 1 ? singular : plural}`
}

function percent(v: string | number | null | undefined): string {
  if (v == null || v === '') return '—'
  const n = typeof v === 'number' ? v : parsePercentualPt(String(v))
  if (Number.isNaN(n)) return String(v)
  return `${formatPercentualPt(n)}%`
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
  lead?: Crm.Lead | null
  onChanged: () => void
  /** Sem o Card externo — o título fica no acordeão da página. */
  embedded?: boolean
}

export function CrmContratoCard({ negociacao, lead = null, onChanged, embedded = false }: Props) {
  const toast = useToast()
  const navigate = useNavigate()
  const linhas = negociacao.linhas || []
  const pdfInputRef = useRef<HTMLInputElement>(null)

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
  const [semReajuste, setSemReajuste] = useState(false)
  const [reajustePct, setReajustePct] = useState('')
  const [reajusteRotulo, setReajusteRotulo] = useState('')
  const [politica, setPolitica] = useState<ComercialContrato.Politica | null>(null)
  const [gerando, setGerando] = useState(false)
  const [preview, setPreview] = useState<ComercialContrato.Contrato | null>(null)
  const [baixandoId, setBaixandoId] = useState<number | null>(null)
  const [baixandoAssinadoId, setBaixandoAssinadoId] = useState<number | null>(null)
  const [enviandoId, setEnviandoId] = useState<number | null>(null)
  const [assinandoId, setAssinandoId] = useState<number | null>(null)
  const [avancarFunil, setAvancarFunil] = useState(true)
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [referenciaAnexo, setReferenciaAnexo] = useState('')
  const [anexandoPdf, setAnexandoPdf] = useState(false)
  const [cancelarId, setCancelarId] = useState<number | null>(null)
  const [cancelando, setCancelando] = useState(false)
  const [fiscais, setFiscais] = useState<Crm.DadosFiscais>(emptyFiscal)
  const [editarGeracao, setEditarGeracao] = useState(false)

  const load = useCallback(async () => {
    const [tmpls, rows, pol] = await Promise.all([
      comercialContratoTemplates.list(),
      comercialContratos.list({ negociacao_id: negociacao.id }),
      comercialContratoPolitica.get(),
    ])
    setTemplates(tmpls)
    setContratos(rows)
    setPolitica(pol)
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
  const mostrarFormularioGeracao = podeGerar && (!contratoDaLinha || editarGeracao)

  useEffect(() => {
    setEditarGeracao(false)
  }, [linhaId])

  useEffect(() => {
    if (!linhaSel) {
      setFiscais(emptyFiscal())
      return
    }
    setFiscais(fiscaisDaLinha(linhaSel, lead))
  }, [linhaId, lead?.email, lead?.telefone, JSON.stringify(linhaSel?.dados_fiscais)])

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
    if (!semReajuste && reajustePct.trim()) {
      const n = parsePercentualPt(reajustePct)
      if (!Number.isFinite(n) || n < 0 || n > 100) {
        toast.showWarning('O percentual de reajuste deve estar entre 0 e 100.')
        return
      }
    }
    setGerando(true)
    try {
      await crmNegociacoes.updateLinha(negociacao.id, linhaId, {
        dados_fiscais: fiscalPayload(fiscais),
      })
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
        sem_reajuste: semReajuste,
        reajuste_percentual: semReajuste || !reajustePct.trim() ? null : String(parsePercentualPt(reajustePct)),
        reajuste_rotulo: reajusteRotulo.trim() || null,
      })
      setPreview(row)
      setEditarGeracao(false)
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

  async function handlePdfAssinado(id: number, nome?: string | null) {
    setBaixandoAssinadoId(id)
    try {
      const blob = await comercialContratos.downloadPdfAssinado(id)
      downloadBlob(blob, nome || `contrato-${id}-assinado.pdf`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível baixar o PDF assinado.'))
    } finally {
      setBaixandoAssinadoId(null)
    }
  }

  async function handleAnexarPdf(id: number) {
    if (!pdfFile) {
      toast.showWarning('Escolha o PDF assinado para anexar.')
      return
    }
    setAnexandoPdf(true)
    try {
      const row = await comercialContratos.anexarPdfAssinado(id, pdfFile, referenciaAnexo)
      setPreview(row)
      setPdfFile(null)
      if (pdfInputRef.current) pdfInputRef.current.value = ''
      toast.showSuccess('PDF assinado anexado. Já podes marcar o contrato como assinado.')
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível anexar o PDF assinado.'))
    } finally {
      setAnexandoPdf(false)
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
    const atual = contratos.find((c) => c.id === id) || preview
    if (!atual?.tem_pdf_assinado) {
      toast.showWarning('Anexe o PDF assinado antes de marcar o contrato como assinado.')
      return
    }
    setAssinandoId(id)
    try {
      const row = await comercialContratos.marcarAssinado(id, {
        avancar_funil: avancarFunil,
      })
      setPreview(row)
      toast.showSuccess(
        avancarFunil
          ? 'Contrato assinado, Rede/Empresa vinculadas e funil atualizado.'
          : 'Contrato marcado como assinado. Rede e Empresa foram criadas ou vinculadas.',
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
    const eraRescisao = preview?.id === cancelarId && preview.status === 'assinado'
    setCancelando(true)
    try {
      const row = await comercialContratos.cancelar(cancelarId)
      toast.showSuccess(eraRescisao ? 'Contrato rescindido.' : 'Contrato cancelado.')
      setCancelarId(null)
      setPreview(row)
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível cancelar o contrato.'))
    } finally {
      setCancelando(false)
    }
  }

  const cancelandoAssinado =
    cancelarId != null && (preview?.id === cancelarId ? preview.status === 'assinado' : false)
  const multaPreview = cancelandoAssinado ? preview?.multa_rescisao : null

  const interno = preview?.interno
  const linhaInterno = linhaSel

  const inner = (
    <>
      <p className="mb-3 text-sm text-slate-500">
        Um contrato por CNPJ. O PDF do cliente não inclui custo nem margem — esses valores ficam só neste
        painel. O nome da Rede (acima) e os dados fiscais abaixo são obrigatórios para gerar.
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
              {contratoDaLinha.status === 'assinado'
                ? ' Para gerar outro, rescinda o atual (com estimativa de multa, se aplicável).'
                : ' Para gerar outro, cancele o atual.'}
            </p>
          ) : null}
          {podeGerar && contratoDaLinha?.status === 'rascunho' && !editarGeracao ? (
            <Button variant="secondary" onClick={() => setEditarGeracao(true)}>
              Alterar rascunho
            </Button>
          ) : null}
          {mostrarFormularioGeracao ? (
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
          <div className="space-y-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Reajuste anual</p>
            <p className="text-xs text-slate-500">
              Padrão da instância:{' '}
              {politica
                ? Number(politica.reajuste_percentual) > 0
                  ? `${percent(politica.reajuste_percentual)}${politica.reajuste_rotulo ? ` · ${politica.reajuste_rotulo}` : ''}`
                  : politica.reajuste_rotulo || 'sem reajuste'
                : '—'}
              . O admin altera em Cadastros → Modelos de contrato. Sem consulta automática a índice.
            </p>
            <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={semReajuste}
                onChange={(e) => setSemReajuste(e.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Sem reajuste neste contrato
            </label>
            {semReajuste ? null : (
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Percentual (override)"
                  inputMode="decimal"
                  value={reajustePct}
                  onChange={(e) => setReajustePct(e.target.value.replace(/[^\d,.]/g, ''))}
                  hint="Vazio = padrão da instância. Ex.: 5,5"
                />
                <Input
                  label="Rótulo (override)"
                  value={reajusteRotulo}
                  onChange={(e) => setReajusteRotulo(e.target.value)}
                  placeholder={politica?.reajuste_rotulo || 'Ex.: IGPM'}
                />
              </div>
            )}
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
          <CrmDadosFiscaisFields
            value={fiscais}
            onChange={(patch) => setFiscais((p) => ({ ...p, ...patch }))}
            disabled={gerando}
          />
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
                {money(preview.valor_mensalidade)} · fidelidade {preview.fidelidade_meses} meses
                {preview.status === 'cancelado'
                  ? ' · contrato cancelado'
                  : ` (${textoDiasFidelidade(preview.dias_restantes_fidelidade)})`}
                {Number(preview.reajuste_percentual) > 0
                  ? ` · reajuste ${percent(preview.reajuste_percentual)}${preview.reajuste_rotulo ? ` ${preview.reajuste_rotulo}` : ''}`
                  : ' · sem reajuste'}
              </p>
              {preview.status === 'assinado' && preview.multa_rescisao ? (
                <div className="mt-2 max-w-xl space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
                  {preview.multa_rescisao.aplicavel && preview.multa_rescisao.valor_estimado != null ? (
                    <p>
                      Estimativa de multa se rescindir agora:{' '}
                      <strong>
                        {pluralPt(
                          preview.multa_rescisao.mensalidades_estimadas,
                          'mensalidade',
                          'mensalidades',
                        )}
                      </strong>
                      {' × '}
                      {money(preview.multa_rescisao.valor_mensalidade)}
                      {' = '}
                      <strong>{money(preview.multa_rescisao.valor_estimado)}</strong>
                      {' '}
                      (
                      {pluralPt(
                        preview.multa_rescisao.meses_restantes,
                        'mês restante',
                        'meses restantes',
                      )}
                      ; teto {preview.multa_rescisao.multa_max_mensalidades}).
                    </p>
                  ) : preview.multa_rescisao.dentro_fidelidade ? (
                    <p>
                      Dentro da fidelidade (
                      {pluralPt(
                        preview.multa_rescisao.meses_restantes,
                        'mês restante',
                        'meses restantes',
                      )}
                      ), mas o teto de multa é 0 — sem estimativa.
                    </p>
                  ) : (
                    <p>Fora da fidelidade — sem estimativa de multa na rescisão.</p>
                  )}
                  <p className="opacity-90">{preview.multa_rescisao.aviso}</p>
                </div>
              ) : null}
              {preview.empresa_id || preview.rede_id ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {preview.empresa_id ? (
                    <Button
                      variant="secondary"
                      onClick={() => navigate(`/empresas/${preview.empresa_id}`)}
                    >
                      Abrir empresa
                    </Button>
                  ) : null}
                  {preview.rede_id ? (
                    <Button variant="secondary" onClick={() => navigate(`/redes/${preview.rede_id}`)}>
                      Abrir rede
                    </Button>
                  ) : null}
                </div>
              ) : null}
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
                  <Button
                    variant="secondary"
                    onClick={() => setAssinandoId(preview.id)}
                    disabled={!preview.tem_pdf_assinado}
                  >
                    Marcar assinado
                  </Button>
                  <Button variant="ghost" onClick={() => setCancelarId(preview.id)}>
                    Cancelar contrato
                  </Button>
                </>
              ) : null}
              {preview.status === 'assinado' ? (
                <Button variant="ghost" onClick={() => setCancelarId(preview.id)}>
                  Rescindir
                </Button>
              ) : null}
            </div>
            {preview.status === 'assinado' && preview.implantacao_ticket_id ? (
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Ticket de implantação:{' '}
                <Link
                  to={TICKETS_PATH}
                  onClick={() => marcarTicketAtivo(preview.implantacao_ticket_id as number)}
                  className="font-medium text-cyan-700 underline dark:text-cyan-400"
                >
                  {exibirProtocolo(preview.implantacao_ticket_protocolo || String(preview.implantacao_ticket_id))}
                </Link>
              </p>
            ) : null}
          </div>
          <iframe
            title={`Preview do contrato ${preview.id}`}
            sandbox=""
            srcDoc={preview.conteudo_html_snapshot || ''}
            className="h-80 w-full rounded-lg border border-slate-200 bg-white dark:border-slate-700"
          />
        </div>
      ) : null}

      {preview && (preview.status === 'rascunho' || preview.status === 'enviado' || preview.tem_pdf_assinado) ? (
        <div className="mt-3 space-y-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">PDF assinado</p>
          <p className="text-xs text-slate-500">
            Exporte o PDF gerado, assine no ClickSign ou outro e anexe aqui. Referência/protocolo é opcional.
            Marcar assinado só fica disponível depois do anexo — isso cria ou vincula Rede e Empresa (sem PDVs).
          </p>
          {preview.tem_pdf_assinado ? (
            <p className="text-sm text-slate-700 dark:text-slate-300">
              Anexado: {preview.pdf_assinado_nome_original || 'PDF'}
              {preview.referencia_externa ? ` · ref. ${preview.referencia_externa}` : ''}
            </p>
          ) : null}
          {preview.tem_pdf_assinado ? (
            <Button
              variant="secondary"
              onClick={() => void handlePdfAssinado(preview.id, preview.pdf_assinado_nome_original)}
              disabled={baixandoAssinadoId === preview.id}
            >
              {baixandoAssinadoId === preview.id ? 'Baixando…' : 'Baixar PDF assinado'}
            </Button>
          ) : null}
          {preview.status === 'rascunho' || preview.status === 'enviado' ? (
            <div className="space-y-3">
              <input
                ref={pdfInputRef}
                id="contrato-pdf-assinado"
                type="file"
                accept="application/pdf,.pdf"
                className="sr-only"
                aria-label="Ficheiro PDF assinado"
                onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
              />
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => pdfInputRef.current?.click()}
                >
                  {preview.tem_pdf_assinado ? 'Escolher outro PDF' : 'Anexar PDF assinado'}
                </Button>
                {pdfFile ? (
                  <span className="text-sm text-slate-600 dark:text-slate-300">{pdfFile.name}</span>
                ) : (
                  <span className="text-xs text-slate-500">Só ficheiros PDF</span>
                )}
              </div>
              <Input
                label="Referência / protocolo (opcional)"
                value={referenciaAnexo}
                onChange={(e) => setReferenciaAnexo(e.target.value)}
                placeholder="Ex.: envelope ClickSign"
              />
              <Button onClick={() => void handleAnexarPdf(preview.id)} disabled={anexandoPdf || !pdfFile}>
                {anexandoPdf ? 'Anexando…' : preview.tem_pdf_assinado ? 'Substituir PDF assinado' : 'Enviar anexo'}
              </Button>
            </div>
          ) : null}
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
              Confirma o PDF anexado
              {preview?.referencia_externa ? ` (ref. ${preview.referencia_externa})` : ''}. A Rede e a
              Empresa do CNPJ são criadas ou vinculadas; PDVs ficam para a implantação.
            </p>
            <div className="mt-4 space-y-1">
              <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={avancarFunil}
                  onChange={(e) => setAvancarFunil(e.target.checked)}
                  className="size-4 rounded border-slate-300"
                />
                Avançar funil para «Contrato assinado»
              </label>
              <p className="pl-6 text-xs text-slate-500">
                Pode pular proposta ou outros estágios — há cliente que manda a documentação e já fecha o
                contrato. Desmarque só se quiser deixar o funil onde está.
              </p>
            </div>
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
        title={cancelandoAssinado ? 'Rescindir contrato assinado?' : 'Cancelar contrato?'}
        message={
          cancelandoAssinado
            ? 'O contrato deixa de estar ativo. Rede e Empresa já criadas não são removidas.'
            : 'O rascunho ou o enviado deixa de valer.'
        }
        confirmLabel={cancelandoAssinado ? 'Rescindir' : 'Cancelar contrato'}
        cancelLabel="Voltar"
        variant="danger"
        loading={cancelando}
        onConfirm={() => void handleCancelar()}
        onCancel={() => setCancelarId(null)}
      >
        {multaPreview ? (
          <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
            {multaPreview.aplicavel && multaPreview.valor_estimado != null ? (
              <p>
                Estimativa de multa:{' '}
                <strong>{pluralPt(multaPreview.mensalidades_estimadas, 'mensalidade', 'mensalidades')}</strong>
                {' × '}
                {money(multaPreview.valor_mensalidade)}
                {' = '}
                <strong>{money(multaPreview.valor_estimado)}</strong>
                {' '}
                ({pluralPt(multaPreview.meses_restantes, 'mês restante', 'meses restantes')} na
                fidelidade; teto {multaPreview.multa_max_mensalidades}).
              </p>
            ) : multaPreview.dentro_fidelidade ? (
              <p>
                Dentro da fidelidade (
                {pluralPt(multaPreview.meses_restantes, 'mês restante', 'meses restantes')}), mas o
                teto de multa neste contrato é 0 — sem estimativa.
              </p>
            ) : (
              <p>Fora do período de fidelidade (ou sem meses restantes) — sem estimativa de multa.</p>
            )}
            <p className="text-xs opacity-90">{multaPreview.aviso}</p>
          </div>
        ) : null}
      </ConfirmDialog>
    </>
  )

  if (embedded) return inner
  return <Card title="Contrato comercial">{inner}</Card>
}
