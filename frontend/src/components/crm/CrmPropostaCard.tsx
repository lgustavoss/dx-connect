import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  comercialPropostaTemplates,
  comercialPropostas,
  whatsappChats,
  type ComercialProposta,
  type Crm,
} from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { TEXTAREA_FIELD_CLASS } from '../ui/Input'
import { Select } from '../ui/Select'
import { useToast } from '../ui/Toast'
import { useAuth } from '../../contexts/AuthContext'
import { temPermissao } from '../../lib/permissoes'
import { maskCnpjCpf } from '../../utils/maskCnpjCpf'

const STATUS_LABEL: Record<string, string> = {
  rascunho: 'Rascunho',
  enviada: 'Enviada',
  substituida: 'Substituída',
}

const CANAL_LABEL: Record<string, string> = {
  email: 'E-mail',
  impresso: 'Impresso',
  outro: 'Outro',
  whatsapp: 'WhatsApp',
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

type Props = {
  negociacao: Crm.Negociacao
  onChanged: () => void
  /** Sem o Card externo — o título fica no acordeão da página. */
  embedded?: boolean
}

export function CrmPropostaCard({ negociacao, onChanged, embedded = false }: Props) {
  const toast = useToast()
  const { user } = useAuth()
  const podeEmitir = temPermissao(user, 'propostas.emitir')
  const linhas = negociacao.linhas || []
  const chats = useMemo(() => negociacao.chats || [], [negociacao])

  const [templates, setTemplates] = useState<ComercialProposta.Template[]>([])
  const [propostas, setPropostas] = useState<ComercialProposta.Proposta[]>([])
  const [templateId, setTemplateId] = useState<number | ''>('')
  const [linhaIds, setLinhaIds] = useState<number[]>([])
  const [condicoes, setCondicoes] = useState('')
  const [gerando, setGerando] = useState(false)
  const [preview, setPreview] = useState<ComercialProposta.Proposta | null>(null)
  const [baixandoId, setBaixandoId] = useState<number | null>(null)
  const [enviandoId, setEnviandoId] = useState<number | null>(null)
  const [chatEscolhido, setChatEscolhido] = useState<number | ''>('')

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

  useEffect(() => {
    setChatEscolhido((prev) => {
      if (prev !== '' && chats.some((c) => c.id === prev)) return prev
      return chats[0]?.id ?? ''
    })
  }, [chats])

  const templateOptions = useMemo(
    () => templates.map((t) => ({ value: String(t.id), label: `${t.nome} (v${t.versao})` })),
    [templates],
  )

  const chatOptions = useMemo(
    () => chats.map((c) => ({ value: String(c.id), label: c.cliente_nome || c.wa_id })),
    [chats],
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
      toast.showSuccess('Proposta gerada. Revise o preview e envie.')
      await load()
      onChanged()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível gerar a proposta.'))
    } finally {
      setGerando(false)
    }
  }

  /** O envio é o fato que move o funil — não existe mais «marcar enviada» solto (#1321). */
  async function registrarEnvio(proposta: ComercialProposta.Proposta, canal: 'impresso' | 'whatsapp') {
    await comercialPropostas.marcarEnviada(proposta.id, { canal, avancar_funil: true })
    toast.showSuccess(
      canal === 'whatsapp'
        ? 'Proposta enviada no WhatsApp. Funil movido para «Proposta enviada».'
        : 'PDF baixado e envio registrado. Funil movido para «Proposta enviada».',
    )
    await load()
    onChanged()
  }

  async function handlePdf(proposta: ComercialProposta.Proposta) {
    setBaixandoId(proposta.id)
    try {
      const blob = await comercialPropostas.downloadPdf(proposta.id)
      downloadBlob(blob, `proposta-${proposta.id}.pdf`)
      if (proposta.status === 'rascunho' && podeEmitir) {
        await registrarEnvio(proposta, 'impresso')
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível baixar o PDF.'))
    } finally {
      setBaixandoId(null)
    }
  }

  async function handleWhatsapp(proposta: ComercialProposta.Proposta) {
    if (chatEscolhido === '') {
      toast.showWarning('Vincule um chat do WhatsApp a esta negociação para enviar por lá.')
      return
    }
    setEnviandoId(proposta.id)
    try {
      const blob = await comercialPropostas.downloadPdf(proposta.id)
      const file = new File([blob], `proposta-${proposta.id}.pdf`, { type: 'application/pdf' })
      await whatsappChats.enviarMidia(Number(chatEscolhido), file, `Proposta comercial #${proposta.id}`)
      await registrarEnvio(proposta, 'whatsapp')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a proposta no WhatsApp.'))
    } finally {
      setEnviandoId(null)
    }
  }

  function acoesDeEnvio(proposta: ComercialProposta.Proposta) {
    if (!podeEmitir) {
      return (
        <Button
          variant="secondary"
          onClick={() => void handlePdf(proposta)}
          disabled={baixandoId === proposta.id}
        >
          {baixandoId === proposta.id ? 'Baixando…' : 'Baixar PDF'}
        </Button>
      )
    }
    if (proposta.status !== 'rascunho') {
      return (
        <Button
          variant="secondary"
          onClick={() => void handlePdf(proposta)}
          disabled={baixandoId === proposta.id}
        >
          {baixandoId === proposta.id ? 'Baixando…' : 'Baixar PDF'}
        </Button>
      )
    }
    return (
      <>
        {chats.length > 0 ? (
          <Button
            variant="secondary"
            onClick={() => void handleWhatsapp(proposta)}
            disabled={enviandoId === proposta.id}
          >
            {enviandoId === proposta.id ? 'Enviando…' : 'Enviar por WhatsApp'}
          </Button>
        ) : null}
        <Button
          variant="secondary"
          onClick={() => void handlePdf(proposta)}
          disabled={baixandoId === proposta.id}
        >
          {baixandoId === proposta.id ? 'Baixando…' : 'Baixar e registrar envio'}
        </Button>
      </>
    )
  }

  const inner = (
    <>
      <p className="mb-3 text-sm text-slate-500">
        O documento enviado ao cliente mostra só itens e valores negociados — custo e margem ficam só nesta tela.
        Gerar não muda o funil: o envio (WhatsApp do chat vinculado, ou download) registra o fato e move para
        «Proposta enviada».
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
          {podeEmitir ? (
            <Button onClick={() => void handleGerar()} disabled={gerando}>
              {gerando ? 'Gerando…' : 'Gerar proposta'}
            </Button>
          ) : null}
        </div>
      )}

      {preview ? (
        <div className="mt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Preview — proposta #{preview.id} ({STATUS_LABEL[preview.status] || preview.status})
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {chats.length > 1 && preview.status === 'rascunho' ? (
                <div className="w-52">
                  <Select
                    label="Chat do WhatsApp"
                    value={chatEscolhido === '' ? '' : String(chatEscolhido)}
                    onChange={(v) => setChatEscolhido(v ? Number(v) : '')}
                    options={chatOptions}
                  />
                </div>
              ) : null}
              {acoesDeEnvio(preview)}
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
                      ? ` · enviada ${formatDateTime(p.enviado_em)} (${CANAL_LABEL[p.canal || ''] || p.canal})`
                      : ''}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="ghost" onClick={() => setPreview(p)}>
                    Ver
                  </Button>
                  {acoesDeEnvio(p)}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  )

  if (embedded) return inner
  return <Card title="Proposta comercial">{inner}</Card>
}
