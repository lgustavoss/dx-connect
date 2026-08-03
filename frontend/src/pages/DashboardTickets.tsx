import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  ApiError,
  dashboard,
  redes,
  setores,
  type Dashboard,
  type Redes,
  type Setores,
} from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { DashboardCanalComparativo, snapshotFromGeral } from '../components/dashboard/DashboardCanalComparativo'
import { DashboardFiltroAtivo } from '../components/dashboard/DashboardFiltroAtivo'
import { DashboardNav } from '../components/dashboard/DashboardNav'
import { barClickableProps, chartTooltipProps } from '../components/dashboard/dashboardChartUtils'
import { corDrill, useDashboardDrilldown } from '../components/dashboard/useDashboardDrilldown'
import { NotaEstrelasMedia } from '../components/ui/NotaEstrelasMedia'
import { DashboardPeriodoFiltro } from '../components/dashboard/DashboardPeriodoFiltro'
import {
  MetricCard,
  formatarDiaCurto,
  formatarHoras,
  formatarIntervaloPeriodo,
} from '../components/dashboard/dashboardMetrics'
import { useDashboardPeriodo } from '../hooks/useDashboardPeriodo'

const CORES_PRIORIDADE: Record<string, string> = {
  baixa: '#94a3b8',
  normal: '#06b6d4',
  alta: '#f59e0b',
  urgente: '#ef4444',
}

function labelPrioridade(p: string): string {
  const map: Record<string, string> = {
    baixa: 'Baixa',
    normal: 'Normal',
    alta: 'Alta',
    urgente: 'Urgente',
  }
  return map[p] ?? p
}

const PRIORIDADES = [
  { value: '', label: 'Todas' },
  { value: 'baixa', label: 'Baixa' },
  { value: 'normal', label: 'Normal' },
  { value: 'alta', label: 'Alta' },
  { value: 'urgente', label: 'Urgente' },
]

function DashboardTicketsSkeleton() {
  return (
    <PageContainer>
      <div className="mb-6 h-9 w-64 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
      <div className="mb-6 h-12 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-72 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
        ))}
      </div>
    </PageContainer>
  )
}

export function DashboardTickets() {
  const toast = useToast()
  const { user } = useAuth()
  const { preset, de, ate, aplicarPreset, marcarCustom, onDeChange, onAteChange } =
    useDashboardPeriodo('este_mes')
  const [redeId, setRedeId] = useState<number | ''>('')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [prioridade, setPrioridade] = useState('')
  const [data, setData] = useState<Dashboard.TicketsResponse | null>(null)
  const [snapshot, setSnapshot] = useState<Dashboard.SnapshotCanais | null>(null)
  const [redesLista, setRedesLista] = useState<Redes.Rede[]>([])
  const [setoresLista, setSetoresLista] = useState<Setores.Setor[]>([])
  const [loading, setLoading] = useState(true)
  const [semPermissao, setSemPermissao] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const drill = useDashboardDrilldown()
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    Promise.all([
      redes.list({ limit: 100, ordenar_por: 'nome', ordem: 'asc' }),
      setores.list({ limit: 100, ordenar_por: 'nome', ordem: 'asc' }),
    ])
      .then(([r, s]) => {
        setRedesLista(r.items)
        setSetoresLista(s.items)
      })
      .catch(() => {
        /* filtros opcionais */
      })
  }, [])

  useEffect(() => {
    dashboard
      .getGeral({ de, ate })
      .then((g) => setSnapshot(snapshotFromGeral(g)))
      .catch(() => undefined)
  }, [de, ate, reloadKey])

  useEffect(() => {
    setLoading(true)
    setError(null)
    setSemPermissao(false)
    dashboard
      .getTickets({
        de,
        ate,
        rede_id: redeId === '' ? undefined : redeId,
        setor_id: setorId === '' ? undefined : setorId,
        prioridade: prioridade || undefined,
        ...drill.apiParams,
      })
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setSemPermissao(true)
          toast.showWarning(err.message || 'Você não tem permissão para ver este dashboard.')
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Não encontramos os dados do dashboard de tickets.')
        setError(m.titulo)
        toast.showError(mensagemFalhaParaToast(m))
      })
      .finally(() => setLoading(false))
  }, [de, ate, redeId, setorId, prioridade, drill.apiParams, reloadKey, toast])

  const atendentesChart = useMemo(
    () => (data?.por_atendente ?? []).map((a) => ({ id: a.id, nome: a.nome, total: a.total })),
    [data],
  )

  const relatorioHref = useMemo(() => {
    const params = new URLSearchParams()
    if (de) params.set('de', de)
    if (ate) params.set('ate', ate)
    if (redeId !== '') params.set('rede_id', String(redeId))
    if (setorId !== '') params.set('setor_id', String(setorId))
    if (prioridade) params.set('prioridade', prioridade)
    const qs = params.toString()
    return qs ? `/relatorios/tickets?${qs}` : '/relatorios/tickets'
  }, [de, ate, redeId, setorId, prioridade])

  const volumeChart = useMemo(
    () =>
      (data?.volume_por_dia ?? []).map((d) => ({
        ...d,
        label: formatarDiaCurto(d.dia),
      })),
    [data],
  )

  const prioridadeChart = useMemo(
    () =>
      (data?.por_prioridade ?? [])
        .filter((p) => p.total > 0)
        .map((p) => ({
          nome: labelPrioridade(p.prioridade),
          prioridade: p.prioridade,
          total: p.total,
          fill: CORES_PRIORIDADE[p.prioridade] ?? '#64748b',
        })),
    [data],
  )

  const statusChart = useMemo(
    () => (data?.por_status ?? []).map((s) => ({ id: s.id, nome: s.nome, total: s.total })),
    [data],
  )

  const motivoChart = useMemo(
    () => (data?.por_motivo ?? []).map((m) => ({ id: m.id, nome: m.nome, total: m.total })),
    [data],
  )

  const redeChart = useMemo(
    () => (data?.por_rede ?? []).map((r) => ({ id: r.id, nome: r.nome, total: r.total })),
    [data],
  )

  const empresaChart = useMemo(
    () => (data?.por_empresa ?? []).map((e) => ({ id: e.id, nome: e.nome, total: e.total })),
    [data],
  )

  const canalChart = useMemo(
    () => (data?.por_canal ?? []).map((c) => ({ nome: c.rotulo, canal: c.canal, total: c.total })),
    [data],
  )

  const csatChart = useMemo(() => {
    if (!data?.csat.por_nota) return []
    return [1, 2, 3, 4, 5].map((n) => ({
      nota: `${n}★`,
      notaValor: String(n),
      total: data.csat.por_nota[String(n)] ?? 0,
    }))
  }, [data])

  const semDados =
    data != null &&
    data.volume_por_dia.every((d) => d.abertos === 0 && d.fechados === 0) &&
    data.por_status.length === 0

  if (loading && !data) {
    return <DashboardTicketsSkeleton />
  }

  if (semPermissao) {
    return (
      <PageContainer>
        <SemPermissao
          title="Você não tem permissão para acessar o dashboard de tickets."
          voltarPara="/"
          voltarLabel="Voltar ao dashboard"
        />
      </PageContainer>
    )
  }

  if (error && !data) {
    return (
      <PageContainer className="flex flex-col items-center gap-4 py-16 text-center">
        <p className="text-slate-600 dark:text-slate-300">{error}</p>
        <Button type="button" onClick={() => setReloadKey((k) => k + 1)}>
          Tentar novamente
        </Button>
      </PageContainer>
    )
  }

  if (!data) return null

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard — Tickets"
        subtitle={`Indicadores de atendimento · ${formatarIntervaloPeriodo(data.de, data.ate)}`}
      />

      <DashboardNav
        actions={
          <>
            <Link to="/tickets/novo">
              <Button>Novo ticket</Button>
            </Link>
            {user?.role === 'admin' ? (
              <Link to={relatorioHref}>
                <Button variant="secondary">Exportar planilha</Button>
              </Link>
            ) : null}
          </>
        }
      />

      {snapshot ? <DashboardCanalComparativo snapshot={snapshot} /> : null}

      {drill.rotuloFiltro ? (
        <DashboardFiltroAtivo rotulo={drill.rotuloFiltro} onLimpar={drill.limpar} />
      ) : null}

      <Card className="mb-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
          <DashboardPeriodoFiltro
            preset={preset}
            de={de}
            ate={ate}
            onPreset={aplicarPreset}
            onCustom={marcarCustom}
            onDeChange={onDeChange}
            onAteChange={onAteChange}
          />
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            Rede
            <select
              value={redeId}
              onChange={(e) => setRedeId(e.target.value ? Number(e.target.value) : '')}
              className="min-w-[10rem] rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="">Todas</option>
              {redesLista.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.nome}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            Setor
            <select
              value={setorId}
              onChange={(e) => setSetorId(e.target.value ? Number(e.target.value) : '')}
              className="min-w-[10rem] rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="">Todos</option>
              {setoresLista.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-400">
            Prioridade
            <select
              value={prioridade}
              onChange={(e) => setPrioridade(e.target.value)}
              className="min-w-[10rem] rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              {PRIORIDADES.map((p) => (
                <option key={p.value || 'todas'} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          label="Tempo médio de resolução"
          dica="Quanto tempo, em média, leva para encerrar um ticket — da abertura até o fechamento. Considera apenas tickets encerrados no período selecionado."
          value={formatarHoras(data.mttr_horas)}
          hint="Da abertura até o encerramento"
          borderClass="border-l-4 border-l-cyan-500"
        />
        <MetricCard
          label="Espera na fila"
          dica="Tempo médio que o ticket ficou aguardando até receber o primeiro atendente responsável."
          value={formatarHoras(data.fila_tempo_medio_horas)}
          hint="Até o primeiro responsável"
          borderClass="border-l-4 border-l-amber-400"
        />
        <MetricCard
          label="Satisfação do cliente"
          dica="Nota média de 1 a 5 estrelas que os clientes deram após o atendimento do ticket (CSAT)."
          hint={
            data.csat.total_avaliacoes === 0
              ? 'Nenhuma avaliação no período'
              : `${data.csat.total_avaliacoes} ${data.csat.total_avaliacoes === 1 ? 'avaliação' : 'avaliações'} no período`
          }
          borderClass="border-l-4 border-l-violet-400"
        >
          <div className="mt-2">
            <NotaEstrelasMedia media={data.csat.media} size="md" />
          </div>
        </MetricCard>
      </div>

      {semDados ? (
        <Card>
          <p className="text-center text-slate-500 dark:text-slate-400">
            Nenhum ticket no período selecionado. Ajuste os filtros ou abra tickets para ver métricas aqui.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <Card
            title="Volume por dia"
            description="Quantidade de tickets abertos e encerrados em cada dia do período"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={volumeChart}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip {...chartTooltipProps} />
                  <Legend />
                  <Line type="monotone" dataKey="abertos" name="Abertos" stroke="#06b6d4" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="fechados" name="Fechados" stroke="#64748b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card
            title="Tickets abertos por status"
            description="Clique em um status para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {statusChart.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Nenhum ticket aberto.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={statusChart} layout="vertical" margin={{ left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="nome" width={120} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Tickets"
                      radius={[0, 4, 4, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { id?: number; nome?: string }
                        if (p?.id != null && p.nome) drill.toggle('status', String(p.id), p.nome)
                      }}
                    >
                      {statusChart.map((entry) => (
                        <Cell
                          key={entry.id}
                          fill={corDrill('#06b6d4', drill.isSelected('status', String(entry.id)), drill.hasSelection)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Tickets abertos por prioridade"
            description="Clique em uma prioridade para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {prioridadeChart.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Nenhum ticket aberto.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={prioridadeChart}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Tickets"
                      radius={[4, 4, 0, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { prioridade?: string; nome?: string }
                        if (p?.prioridade && p.nome) drill.toggle('prioridade', p.prioridade, p.nome)
                      }}
                    >
                      {prioridadeChart.map((entry) => (
                        <Cell
                          key={entry.prioridade}
                          fill={corDrill(
                            entry.fill,
                            drill.isSelected('prioridade', entry.prioridade),
                            drill.hasSelection,
                          )}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Motivos mais frequentes"
            description="Clique em um motivo para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {motivoChart.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Sem dados de motivo.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={motivoChart} layout="vertical" margin={{ left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="nome" width={120} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Tickets"
                      radius={[0, 4, 4, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { id?: number; nome?: string }
                        if (p?.id != null && p.nome) drill.toggle('motivo', String(p.id), p.nome)
                      }}
                    >
                      {motivoChart.map((entry) => (
                        <Cell
                          key={entry.id}
                          fill={corDrill('#8b5cf6', drill.isSelected('motivo', String(entry.id)), drill.hasSelection)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Redes com mais tickets"
            description="Clique em uma rede para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {redeChart.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Sem dados de rede.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={redeChart} layout="vertical" margin={{ left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="nome" width={120} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Tickets"
                      radius={[0, 4, 4, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { id?: number; nome?: string }
                        if (p?.id != null && p.nome) drill.toggle('rede', String(p.id), p.nome)
                      }}
                    >
                      {redeChart.map((entry) => (
                        <Cell
                          key={entry.id}
                          fill={corDrill('#0ea5e9', drill.isSelected('rede', String(entry.id)), drill.hasSelection)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Empresas com mais tickets"
            description="Clique em uma empresa para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {empresaChart.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Sem dados de empresa.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={empresaChart} layout="vertical" margin={{ left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="nome" width={120} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Tickets"
                      radius={[0, 4, 4, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { id?: number; nome?: string }
                        if (p?.id != null && p.nome) drill.toggle('empresa', String(p.id), p.nome)
                      }}
                    >
                      {empresaChart.map((entry) => (
                        <Cell
                          key={entry.id}
                          fill={corDrill('#6366f1', drill.isSelected('empresa', String(entry.id)), drill.hasSelection)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Como o ticket foi aberto"
            description="Clique em uma origem para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {canalChart.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Sem dados.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={canalChart}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Tickets"
                      radius={[4, 4, 0, 0]}
                      fill="#10b981"
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { canal?: string; nome?: string }
                        if (p?.canal && p.nome) drill.toggle('canal', p.canal, p.nome)
                      }}
                    >
                      {canalChart.map((entry) => (
                        <Cell
                          key={entry.canal}
                          fill={corDrill('#10b981', drill.isSelected('canal', entry.canal), drill.hasSelection)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Distribuição das avaliações"
            description="Clique em uma nota para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {data.csat.total_avaliacoes === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Sem avaliações no período.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={csatChart}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="nota" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Avaliações"
                      radius={[4, 4, 0, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { notaValor?: string; nota?: string }
                        if (p?.notaValor && p.nota) drill.toggle('nota', p.notaValor, p.nota)
                      }}
                    >
                      {csatChart.map((entry) => (
                        <Cell
                          key={entry.notaValor}
                          fill={corDrill('#ec4899', drill.isSelected('nota', entry.notaValor), drill.hasSelection)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          {user?.role === 'admin' && atendentesChart.length > 0 ? (
            <Card
              title="Atendentes com mais tickets"
              description="Clique em um atendente para filtrar os demais gráficos e indicadores"
              className="xl:col-span-2"
            >
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={atendentesChart} layout="vertical" margin={{ left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="nome" width={140} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Tickets"
                      radius={[0, 4, 4, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { id?: number; nome?: string }
                        if (p?.id != null && p.nome) drill.toggle('atendente', String(p.id), p.nome)
                      }}
                    >
                      {atendentesChart.map((entry) => (
                        <Cell
                          key={entry.id}
                          fill={corDrill(
                            '#06b6d4',
                            drill.isSelected('atendente', String(entry.id)),
                            drill.hasSelection,
                          )}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          ) : null}
        </div>
      )}
    </PageContainer>
  )
}
