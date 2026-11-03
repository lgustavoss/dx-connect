import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  faturamento,
  type Faturamento,
} from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { FaturaDocumentos } from '../components/faturamento/FaturaDocumentos'
import { TitulosReceber } from '../components/faturamento/TitulosReceber'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
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

function seloDocs(f: Faturamento.Fatura): string {
  if (f.status !== 'aprovada') return ''
  if (f.documentos_completos) return 'Completos'
  const tipos = new Set((f.anexos ?? []).map((a) => a.tipo))
  if (tipos.has('boleto') || tipos.has('nfse_pdf')) return 'Parcial'
  return 'Pendente'
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
  const { user, isFinanceiroOuAdmin } = useAuth()
  const podeGerar = isFinanceiroOuAdmin || temPermissao(user, 'faturamento.gerar')
  const podeAprovar = isFinanceiroOuAdmin || temPermissao(user, 'faturamento.aprovar')
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
  const [emiteNfse, setEmiteNfse] = useState<'' | 'sim' | 'nao'>('')
  const [detalheId, setDetalheId] = useState<number | null>(null)
  const [aba, setAba] = useState<'faturas' | 'receber'>('faturas')
  const [titulos, setTitulos] = useState<Faturamento.Titulo[]>([])
  const [tituloStatus, setTituloStatus] = useState('')
  const [loadingTitulos, setLoadingTitulos] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    faturamento
      .listFaturas({
        competencia: competencia || undefined,
        status: status || undefined,
        emite_nfse: emiteNfse === 'sim' ? true : emiteNfse === 'nao' ? false : undefined,
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
  }, [competencia, status, emiteNfse, toast])

  useEffect(() => {
    load()
  }, [load])

  const loadTitulos = useCallback(() => {
    setLoadingTitulos(true)
    faturamento
      .listTitulos({
        competencia: competencia || undefined,
        status: tituloStatus || undefined,
      })
      .then(setTitulos)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setTitulos([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os títulos.'))
        setTitulos([])
      })
      .finally(() => setLoadingTitulos(false))
  }, [competencia, tituloStatus, toast])

  useEffect(() => {
    if (aba === 'receber') loadTitulos()
  }, [aba, loadTitulos])

  useEffect(() => {
    faturamento
      .listContratosElegiveis()
      .then(setContratos)
      .catch(() => setContratos([]))
  }, [])

  const faturaDetalhe = detalheId == null ? null : list.find((f) => f.id === detalheId) ?? null

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
      toast.showSuccess('Fatura aprovada. O título a receber já está em aberto. Anexe o boleto e a nota, se houver.')
      setDetalheId(id)
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
        subtitle="Aprove a fatura do mês, anexe boleto e NFS-e (banco/prefeitura) e acompanhe o a receber."
      />

      <div className="flex flex-wrap gap-2">
        {(
          [
            ['faturas', 'Faturas'],
            ['receber', 'A receber'],
          ] as const
        ).map(([valor, label]) => (
          <button
            key={valor}
            type="button"
            onClick={() => setAba(valor)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              aba === valor
                ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

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
          {aba === 'faturas' ? (
            <>
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
          {podeGerar ? (
            <>
              <Button variant="secondary" onClick={gerarAvulsa} disabled={gerando || contratoId === ''}
              >
                Gerar fatura
              </Button>
              <Button onClick={gerarMes} disabled={gerando} loading={gerando}>
                Gerar faturas do mês
              </Button>
            </>
          ) : null}
            </>
          ) : null}
        </div>
        {aba === 'faturas' ? (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          O job automático cria faturas novas da competência (não reabre rejeitadas). «Gerar faturas do mês»
          também reabre as rejeitadas desta competência. Vencimento: dia 10 do mês seguinte.
        </p>
        ) : (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Título nasce ao aprovar a fatura. A baixa é manual — banco e prefeitura já enviam o e-mail ao cliente.
        </p>
        )}
        </div>
      </Card>

      {aba === 'receber' ? (
        <>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ['', 'Todos'],
                ['aberto', 'Em aberto'],
                ['vencido', 'Vencidos'],
                ['pago', 'Pagos'],
              ] as const
            ).map(([valor, label]) => (
              <button
                key={valor || 'tit-todos'}
                type="button"
                onClick={() => setTituloStatus(valor)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  tituloStatus === valor
                    ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <TitulosReceber
            titulos={titulos}
            loading={loadingTitulos}
            podeBaixar={podeAprovar}
            onAtualizado={(atual) => {
              setTitulos((prev) => prev.map((x) => (x.id === atual.id ? atual : x)))
            }}
          />
        </>
      ) : null}

      {aba === 'faturas' ? (
      <>
      <div className="flex flex-wrap gap-2">
        {(
          [
            ['', 'Todas as notas'],
            ['sim', 'Emite NFS-e'],
            ['nao', 'Sem NFS-e'],
          ] as const
        ).map(([valor, label]) => (
          <button
            key={valor || 'nf-todas'}
            type="button"
            onClick={() => setEmiteNfse(valor)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              emiteNfse === valor
                ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

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

      {faturaDetalhe ? (
        <FaturaDocumentos
          key={faturaDetalhe.id}
          fatura={faturaDetalhe}
          podeEditar={podeGerar}
          onChanged={(atual) => {
            setList((prev) => prev.map((x) => (x.id === atual.id ? atual : x)))
          }}
          onClose={() => setDetalheId(null)}
        />
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
                  <th className="px-4 py-3 font-medium">Documentos</th>
                  <th className="px-4 py-3 font-medium">A receber</th>
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
                      {f.status === 'aprovada' ? (
                        <span className="text-xs text-slate-600 dark:text-slate-300">{seloDocs(f)}</span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {f.titulo ? (
                        <span className="text-xs text-slate-600 dark:text-slate-300">
                          {f.titulo.status === 'pago'
                            ? 'Pago'
                            : f.titulo.status === 'vencido'
                              ? 'Vencido'
                              : 'Em aberto'}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${classeStatus(f.status)}`}>
                        {STATUS_LABEL[f.status] || f.status}
                      </span>
                      {f.rejeicao_motivo ? (
                        <p className="mt-1 max-w-xs text-xs text-slate-500">{f.rejeicao_motivo}</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        {podeAprovar && f.status === 'aguardando_aprovacao' ? (
                          <>
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
                          </>
                        ) : null}
                        <Button variant="ghost" onClick={() => setDetalheId(f.id)}>
                          Documentos
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
      </>
      ) : null}
    </PageContainer>
  )
}
