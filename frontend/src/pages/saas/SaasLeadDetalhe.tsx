import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasLeads, saasPlanos, type SaasCatalogo } from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { DetailRow } from '../../components/ui/DetailRow'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SemPermissao } from '../SemPermissao'

const STATUS_OPTS = [
  { value: 'novo', label: 'Novo' },
  { value: 'em_atendimento', label: 'Em atendimento' },
  { value: 'fechado', label: 'Fechado' },
]

export function SaasLeadDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/saas/leads')
  const leadId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [converting, setConverting] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [item, setItem] = useState<Awaited<ReturnType<typeof saasLeads.get>> | null>(null)
  const [status, setStatus] = useState('novo')
  const [notas, setNotas] = useState('')
  const [planos, setPlanos] = useState<SaasCatalogo.Plano[]>([])
  const [planoId, setPlanoId] = useState<number | ''>('')

  useEffect(() => {
    saasPlanos
      .list({ ativo: true })
      .then((list) => {
        setPlanos(list)
        const trial = list.find((p) => p.codigo === 'trial')
        setPlanoId(trial?.id ?? list[0]?.id ?? '')
      })
      .catch(() => setPlanos([]))
  }, [])

  useEffect(() => {
    if (!id || Number.isNaN(leadId)) {
      setFalha({ titulo: 'Lead não encontrado.', detalhe: 'Identificador inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    saasLeads
      .get(leadId)
      .then((lead) => {
        if (cancelled) return
        setItem(lead)
        setStatus(lead.status)
        setNotas(lead.notas_internas ?? '')
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          const detail =
            typeof err.body === 'object' && err.body && 'detail' in err.body
              ? String((err.body as { detail?: unknown }).detail ?? '')
              : ''
          if (detail.toLowerCase().includes('não disponível')) setIndisponivel(true)
          else setFalha(interpretarFalhaCarregamento(err, 'Lead não encontrado.'))
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Lead não encontrado.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, leadId])

  async function salvar() {
    if (!item) return
    setSaving(true)
    try {
      const updated = await saasLeads.update(item.id, {
        status: status as 'novo' | 'em_atendimento' | 'fechado',
        notas_internas: notas.trim() || null,
      })
      setItem(updated)
      toast.showSuccess('Lead atualizado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível atualizar o lead.'))
    } finally {
      setSaving(false)
    }
  }

  async function converterEmLicenca() {
    if (!item) return
    setConverting(true)
    try {
      const licenca = await saasLeads.converter(item.id, {
        enfileirar_provisionamento: false,
        plano_id: planoId === '' ? null : Number(planoId),
      })
      toast.showSuccess('Licença criada a partir do lead.')
      navigate(`/saas/licencas/${licenca.id}`, { replace: true })
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível converter o lead.'))
    } finally {
      setConverting(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }
  if (indisponivel) {
    return (
      <SemPermissao
        title="Leads comerciais não disponíveis nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }
  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver este lead."
        voltarPara="/saas/leads"
        voltarLabel="Voltar para Leads"
      />
    )
  }
  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }
  if (!item) return null

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <button
        type="button"
        onClick={voltarAnterior}
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
      >
        <span aria-hidden>←</span> Voltar
      </button>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{item.nome}</h1>
          <p className="text-sm text-slate-500">{item.email}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {item.cliente_saas_id ? (
            <Button variant="secondary" onClick={() => navigate(`/saas/licencas/${item.cliente_saas_id}`)}>
              Abrir licença #{item.cliente_saas_id}
            </Button>
          ) : (
            <>
              <div className="min-w-[11rem]">
                <Select
                  label="Plano"
                  value={planoId}
                  onChange={(v) => setPlanoId(v === '' ? '' : Number(v))}
                  options={planos.map((p) => ({ value: p.id, label: p.nome }))}
                  includeEmpty
                  emptyLabel="Sem plano"
                  disabled={converting}
                />
              </div>
              <Button disabled={converting} loading={converting} onClick={() => void converterEmLicenca()}>
                Converter em licença
              </Button>
              <Button
                variant="secondary"
                disabled={converting}
                onClick={() => {
                  const q = new URLSearchParams({
                    lead_id: String(item.id),
                    nome: item.nome,
                    email: item.email,
                    contato_nome: item.nome,
                  })
                  if (item.empresa) q.set('empresa', item.empresa)
                  if (item.mensagem) q.set('notas', `Lead #${item.id}: ${item.mensagem.slice(0, 400)}`)
                  navigate(`/saas/licencas/novo?${q.toString()}`)
                }}
              >
                Prefill manual
              </Button>
            </>
          )}
        </div>
      </header>

      <Card title="Mensagem do prospect">
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700 dark:text-slate-200">{item.mensagem}</p>
        <dl className="mt-4">
          <DetailRow label="Empresa" value={item.empresa || '—'} />
          <DetailRow label="Origem" value={item.origem} />
        </dl>
      </Card>

      <Card title="Atendimento">
        <div className="space-y-4">
          <Select
            label="Status"
            value={status}
            onChange={(v) => setStatus(String(v))}
            options={STATUS_OPTS}
          />
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Notas internas</span>
            <textarea
              rows={3}
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            />
          </label>
          <div className="flex justify-end">
            <Button onClick={salvar} disabled={saving} loading={saving}>
              Guardar
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
