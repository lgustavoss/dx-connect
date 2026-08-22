import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  comercialPropostaTemplates,
  comercialPropostas,
  type ComercialProposta,
  type Crm,
} from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Input, TEXTAREA_FIELD_CLASS } from '../ui/Input'
import { Select } from '../ui/Select'
import { useToast } from '../ui/Toast'
import { maskCnpjCpf } from '../../utils/maskCnpjCpf'

const STATUS_LABEL: Record<string, string> = {
  rascunho: 'Rascunho',
  enviada: 'Enviada',
  substituida: 'Substituída',
}

const CANAL_OPTIONS = [
  { value: 'email', label: 'E-mail' },
  { value: 'impresso', label: 'Impresso' },
  { value: 'outro', label: 'Outro' },
]

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

type Props = {
  negociacao: Crm.Negociacao
  onChanged: () => void
  /** Sem o Card externo — o título fica no acordeão da página. */
  embedded?: boolean
}

export function CrmPropostaCard({ negociacao, onChanged, embedded = false }: Props) {
  const toast = useToast()
  const linhas = negociacao.linhas || []

  const [templates, setTemplates] = useState<ComercialProposta.Template[]>([])
  const [propostas, setPropostas] = useState<ComercialProposta.Proposta[]>([])
  const [templateId, setTemplateId] = useState<number | ''>('')
  const [linhaIds, setLinhaIds] = useState<number[]>([])
  const [condicoes, setCondicoes] = useState('')
  const [gerando, setGerando] = useState(false)
  const [preview, setPreview] = useState<ComercialProposta.Proposta | null>(null)

  const [enviarId, setEnviarId] = useState<number | null>(null)
  const [canal, setCanal] = useState<'email' | 'impresso' | 'outro'>('email')
  const [enviadoEm, setEnviadoEm] = useState('')
  const [avancarFunil, setAvancarFunil] = useState(true)
  const [marcando, setMarcando] = useState(false)
  const [baixandoId, setBaixandoId] = useState<number | null>(null)

  const load = useCallback(async () => {
    const [tmpls, props] = await Promise.all([
      comercialPropostaTemplates.list(),
      comercialPropostas.list(negociacao.id),
    ])
    setTemplates(tmpls)
    setPropostas(props)
    setTemplateId((prev) => {
      if (prev !== '' && tmpls.some((t) => t.id === prev)) return prev
      return tmpls[0]?.id ?? ''
    })
    const rascunho = props.find((p) => p.status === 'rascunho')
    setPreview((atual) => {
      if (atual && props.some((p) => p.id === atual.id)) {
        return props.find((p) => p.id === atual.id) || rascunho || props[0] || null
      }
      return rascunho || props[0] || null
    })
  }, [negociacao.id])

  useEffect(() => {
    void load().catch((err) => {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar as propostas.'))
    })
  }, [load, toast])

  useEffect(() => {
    setLinhaIds((negociacao.linhas || []).map((ln) => ln.id))
  }, [negociacao])

  const templateOptions = useMemo(
    () => templates.map((t) => ({ value: String(t.id), label: `${t.nome} (v${t.versao})` })),
    [templates],
  )

  function toggleLinha(id: number) {
    setLinhaIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function handleGerar() {
    if (linhas.length === 0) {
      toast.showWarning('Adicione pelo menos uma linha CNPJ antes de gerar a proposta.')
      return
    }
    if (linhaIds.length === 0) {
      toast.showWarning('Selecione pelo menos um CNPJ.')
      return
    }
    setGerando(true)
    try {
      const row = await comercialPropostas.gerar({
        negociacao_id: negociacao.id,
        template_id: templateId === '' ? null : templateId,
        linha_ids: linhaIds,
        condicoes: condicoes.trim() || null,
      })
      setPreview(row)
      toast.showSuccess('Proposta gerada. Revise o preview antes de enviar.')
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível gerar a proposta.'))
    } finally {
      setGerando(false)
    }
  }

  async function handlePdf(id: number) {
    setBaixandoId(id)
    try {
      const blob = await comercialPropostas.downloadPdf(id)
      downloadBlob(blob, `proposta-${id}.pdf`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível baixar o PDF.'))
    } finally {
      setBaixandoId(null)
    }
  }

  async function handleMarcarEnviada() {
    if (enviarId == null) return
    setMarcando(true)
    try {
      await comercialPropostas.marcarEnviada(enviarId, {
        canal,
        enviado_em: enviadoEm ? new Date(enviadoEm).toISOString() : null,
        avancar_funil: avancarFunil,
      })
      toast.showSuccess(
        avancarFunil ? 'Proposta marcada como enviada e funil atualizado.' : 'Proposta marcada como enviada.',
      )
      setEnviarId(null)
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível marcar a proposta como enviada.'))
    } finally {
      setMarcando(false)
    }
  }

  const inner = (
    <>
      <p className="mb-3 text-sm text-slate-500">
        O documento enviado ao cliente mostra só itens e valores negociados — custo e margem ficam só nesta tela.
      </p>

      {linhas.length === 0 ? (
        <p className="text-sm text-slate-500">Cadastre linhas CNPJ para gerar a proposta.</p>
      ) : (
        <div className="space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">CNPJs incluídos</p>
            {linhas.map((ln) => (
              <label key={ln.id} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={linhaIds.includes(ln.id)}
                  onChange={() => toggleLinha(ln.id)}
                  className="size-4 rounded border-slate-300"
                />
                <span>
                  {ln.razao_social || 'Sem razão social'} · {ln.cnpj ? maskCnpjCpf(ln.cnpj) : 'sem CNPJ'}
                </span>
              </label>
            ))}
          </div>
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
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Condições (opcional)
            <textarea
              value={condicoes}
              onChange={(e) => setCondicoes(e.target.value)}
              rows={3}
              className={`mt-1 ${TEXTAREA_FIELD_CLASS}`}
              placeholder="Prazo, forma de pagamento, observações visíveis ao cliente…"
            />
          </label>
          <Button onClick={() => void handleGerar()} disabled={gerando}>
            {gerando ? 'Gerando…' : 'Gerar proposta'}
          </Button>
        </div>
      )}

      {preview ? (
        <div className="mt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Preview — proposta #{preview.id} ({STATUS_LABEL[preview.status] || preview.status})
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => void handlePdf(preview.id)}
                disabled={baixandoId === preview.id}
              >
                {baixandoId === preview.id ? 'Baixando…' : 'Baixar PDF'}
              </Button>
              {preview.status === 'rascunho' ? (
                <Button variant="secondary" onClick={() => setEnviarId(preview.id)}>
                  Marcar enviada
                </Button>
              ) : null}
            </div>
          </div>
          <iframe
            title={`Preview da proposta ${preview.id}`}
            sandbox=""
            srcDoc={preview.conteudo_html_snapshot}
            className="h-80 w-full rounded-lg border border-slate-200 bg-white dark:border-slate-700"
          />
        </div>
      ) : null}

      {propostas.length > 0 ? (
        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Propostas anteriores</p>
          <ul className="space-y-2 text-sm">
            {propostas.map((p) => (
              <li
                key={p.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700"
              >
                <div>
                  <span className="font-medium text-slate-900 dark:text-slate-100">#{p.id}</span>
                  {' · '}
                  {STATUS_LABEL[p.status] || p.status}
                  {p.template_nome ? ` · ${p.template_nome} v${p.template_versao}` : ''}
                  <div className="text-xs text-slate-500">
                    {formatDateTime(p.created_at)}
                    {p.enviado_em
                      ? ` · enviada ${formatDateTime(p.enviado_em)} (${CANAL_OPTIONS.find((c) => c.value === p.canal)?.label || p.canal})`
                      : ''}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={() => setPreview(p)}>
                    Ver
                  </Button>
                  <Button variant="ghost" onClick={() => void handlePdf(p.id)} disabled={baixandoId === p.id}>
                    PDF
                  </Button>
                  {p.status !== 'substituida' && p.status !== 'enviada' ? (
                    <Button variant="ghost" onClick={() => setEnviarId(p.id)}>
                      Enviada
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {enviarId != null ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div className="w-full rounded-t-2xl bg-white p-5 shadow-xl dark:bg-slate-900 sm:max-w-md sm:rounded-2xl">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Marcar proposta como enviada</h2>
            <p className="mt-1 text-sm text-slate-500">Não envia e-mail automático — só registra o canal e a data.</p>
            <div className="mt-4 space-y-3">
              <Select
                label="Canal"
                value={canal}
                onChange={(v) => setCanal(String(v) as 'email' | 'impresso' | 'outro')}
                options={CANAL_OPTIONS}
              />
              <Input
                label="Data de envio (opcional)"
                type="datetime-local"
                value={enviadoEm}
                onChange={(e) => setEnviadoEm(e.target.value)}
              />
              <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={avancarFunil}
                  onChange={(e) => setAvancarFunil(e.target.checked)}
                  className="size-4 rounded border-slate-300"
                />
                Avançar funil para «Proposta enviada»
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="cancel" onClick={() => setEnviarId(null)} disabled={marcando}>
                  Cancelar
                </Button>
                <Button onClick={() => void handleMarcarEnviada()} disabled={marcando}>
                  {marcando ? 'Salvando…' : 'Confirmar'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )

  if (embedded) return inner
  return <Card title="Proposta comercial">{inner}</Card>
}
