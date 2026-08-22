import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  faturamento,
  type Faturamento,
} from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'

const STATUS_LABEL: Record<string, string> = {
  aguardando_aprovacao: 'Aguardando aprovação',
  aprovada: 'Aprovada',
  rejeitada: 'Rejeitada',
  cancelada: 'Cancelada',
}

const STATUS_FILTROS = ['', 'aguardando_aprovacao', 'aprovada', 'rejeitada'] as const

function competenciaAtual(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function formatMoney(v: string | number): string {
  const n = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso.includes('T') ? iso : `${iso}T00:00:00`)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('pt-BR')
}

function classeStatus(status: string): string {
  if (status === 'aprovada') return 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
  if (status === 'rejeitada') return 'bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-300'
  if (status === 'aguardando_aprovacao')
    return 'bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

export function Faturamento() {
  const toast = useToast()
  const [list, setList] = useState<Faturamento.Fatura[]>([])
  const [contratos, setContratos] = useState<Faturamento.ContratoElegivel[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [status, setStatus] = useState('')
  const [competencia, setCompetencia] = useState(competenciaAtual)
  const [gerando, setGerando] = useState(false)
  const [contratoId, setContratoId] = useState<number | ''>('')
  const [rejeitarId, setRejeitarId] = useState<number | null>(null)
  const [motivo, setMotivo] = useState('')
  const [savingId, setSavingId] = useState<number | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    faturamento
      .listFaturas({
        competencia: competencia || undefined,
        status: status || undefined,
      })
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar as faturas.'))
        setList([])
      })
      .finally(() => setLoading(false))
  }, [competencia, status, toast])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    faturamento
      .listContratosElegiveis()
      .then(setContratos)
      .catch(() => setContratos([]))
  }, [])

  const contratoOptions = useMemo(
    () =>
      contratos.map((c) => ({
        value: c.id,
        label: `${c.razao_social || c.empresa_nome || `Contrato #${c.id}`} — ${formatMoney(c.valor_mensalidade)}`,
      })),
    [contratos],
  )

  async function gerarMes() {
    setGerando(true)
    try {
      const r = await faturamento.gerarCompetencia({ competencia: competencia || undefined })
      const novas = r.criadas
      const reabertas = r.reabertas ?? 0
      if (novas || reabertas) {
        const partes = [
          novas ? `${novas} nova(s)` : null,
          reabertas ? `${reabertas} rejeitada(s) reaberta(s)` : null,
        ].filter(Boolean)
        toast.showSuccess(`${partes.join(', ')} em ${r.competencia}.`)
      } else {
        toast.showSuccess(`Nenhuma fatura nova — ${r.existentes} já existiam em ${r.competencia}.`)
      }
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível gerar as faturas do mês.'))
    } finally {
      setGerando(false)
    }
  }

  async function gerarAvulsa() {
    if (contratoId === '') {
      toast.showWarning('Escolha o contrato.')
      return
    }
    setGerando(true)
    try {
      await faturamento.gerarFatura({
        contrato_id: Number(contratoId),
        competencia: competencia || undefined,
      })
      toast.showSuccess('Fatura gerada para conferência.')
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível gerar a fatura.'))
    } finally {
      setGerando(false)
    }
  }

  async function aprovar(id: number) {
    setSavingId(id)
    try {
      await faturamento.aprovar(id)
      toast.showSuccess('Fatura aprovada. Boleto e NFS-e ficam para o próximo lote.')
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível aprovar.'))
    } finally {
      setSavingId(null)
    }
  }

  async function confirmarRejeicao() {
    if (rejeitarId == null) return
    if (motivo.trim().length < 3) {
      toast.showWarning('Informe o motivo da rejeição.')
      return
    }
    setSavingId(rejeitarId)
    try {
      await faturamento.rejeitar(rejeitarId, motivo.trim())
      toast.showSuccess('Fatura rejeitada. Gere de novo depois de corrigir o contrato.')
      setRejeitarId(null)
      setMotivo('')
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível rejeitar.'))
    } finally {
      setSavingId(null)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver o faturamento."
        detail="A conferência de faturas é só para o setor Financeiro e administradores."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Faturamento"
        subtitle="Faturas internas do mês para o financeiro conferir e aprovar. Boleto e nota fiscal só depois da aprovação."
      />

      <Card>
        <div className="space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-40">
            <Input
              label="Competência"
              type="month"
              value={competencia}
              onChange={(e) => setCompetencia(e.target.value)}
            />
          </div>
          <div className="min-w-[220px] flex-1">
            <Select
              label="Contrato (gerar avulsa)"
              value={contratoId}
              onChange={(v) => setContratoId(v === '' ? '' : Number(v))}
              options={contratoOptions}
              includeEmpty
              emptyLabel="Escolher contrato…"
            />
          </div>
          <Button variant="secondary" onClick={gerarAvulsa} disabled={gerando || contratoId === ''}>
            Gerar fatura
          </Button>
          <Button onClick={gerarMes} disabled={gerando} loading={gerando}>
            Gerar faturas do mês
          </Button>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          O job automático cria faturas novas da competência (não reabre rejeitadas). «Gerar faturas do mês»
          também reabre as rejeitadas desta competência. Vencimento: dia 10 do mês seguinte.
        </p>
        </div>
      </Card>

      <div className="flex flex-wrap gap-2">
        {STATUS_FILTROS.map((s) => (
          <button
            key={s || 'todos'}
            type="button"
            onClick={() => setStatus(s)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              status === s
                ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'
            }`}
          >
            {s ? STATUS_LABEL[s] : 'Todas'}
          </button>
        ))}
      </div>

      {rejeitarId != null ? (
        <Card className="space-y-3">
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Motivo da rejeição</p>
          <textarea
            className={TEXTAREA_FIELD_CLASS}
            rows={3}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Explique o que precisa ser corrigido antes de gerar de novo."
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={confirmarRejeicao} variant="danger" disabled={savingId === rejeitarId}>
              Confirmar rejeição
            </Button>
            <Button
              variant="cancel"
              onClick={() => {
                setRejeitarId(null)
                setMotivo('')
              }}
            >
              Cancelar
            </Button>
          </div>
        </Card>
      ) : null}

      <Card>
        {loading ? (
          <p className="text-sm text-slate-500">Carregando faturas…</p>
        ) : list.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhuma fatura nesta competência.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-700">
                  <th className="px-4 py-3 font-medium">Cliente</th>
                  <th className="px-4 py-3 font-medium">Competência</th>
                  <th className="px-4 py-3 font-medium">Valor</th>
                  <th className="px-4 py-3 font-medium">Vencimento</th>
                  <th className="px-4 py-3 font-medium">NFS-e</th>
                  <th className="px-4 py-3 font-medium">Estado</th>
                  <th className="px-4 py-3 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {list.map((f) => (
                  <tr key={f.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800 dark:text-slate-100">
                        {f.razao_social || f.empresa_nome || `Contrato #${f.contrato_id}`}
                      </div>
                      <div className="font-mono text-xs text-slate-500">{f.cnpj || '—'}</div>
                    </td>
                    <td className="px-4 py-3 tabular-nums">{f.competencia}</td>
                    <td className="px-4 py-3 tabular-nums">{formatMoney(f.valor)}</td>
                    <td className="px-4 py-3">{formatDate(f.vencimento)}</td>
                    <td className="px-4 py-3">{f.emite_nfse ? 'Sim' : 'Não'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${classeStatus(f.status)}`}>
                        {STATUS_LABEL[f.status] || f.status}
                      </span>
                      {f.rejeicao_motivo ? (
                        <p className="mt-1 max-w-xs text-xs text-slate-500">{f.rejeicao_motivo}</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      {f.status === 'aguardando_aprovacao' ? (
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="secondary"
                            disabled={savingId === f.id}
                            onClick={() => aprovar(f.id)}
                          >
                            Aprovar
                          </Button>
                          <Button
                            variant="ghost"
                            disabled={savingId === f.id}
                            onClick={() => {
                              setRejeitarId(f.id)
                              setMotivo('')
                            }}
                          >
                            Rejeitar
                          </Button>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageContainer>
  )
}
