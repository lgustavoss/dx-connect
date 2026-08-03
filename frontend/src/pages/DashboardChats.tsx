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
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ApiError, dashboard, setores, type Dashboard, type Setores } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { DashboardCanalComparativo } from '../components/dashboard/DashboardCanalComparativo'
import { DashboardFiltroAtivo } from '../components/dashboard/DashboardFiltroAtivo'
import { DashboardNav } from '../components/dashboard/DashboardNav'
import { barClickableProps, chartTooltipProps } from '../components/dashboard/dashboardChartUtils'
import { corDrill, useDashboardDrilldown } from '../components/dashboard/useDashboardDrilldown'
import { NotaEstrelasMedia } from '../components/ui/NotaEstrelasMedia'
import { DashboardDemandasAnalise } from '../components/dashboard/DashboardDemandasAnalise'
import { DashboardPeriodoFiltro } from '../components/dashboard/DashboardPeriodoFiltro'
import {
  MetricCard,
  formatarDiaCurto,
  formatarHoras,
  formatarIntervaloPeriodo,
  formatarPct,
} from '../components/dashboard/dashboardMetrics'
import { useDashboardPeriodo } from '../hooks/useDashboardPeriodo'

const CORES_ENCERRAMENTO = ['#06b6d4', '#94a3b8']

function DashboardChatsSkeleton() {
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

export function DashboardChats() {
  const toast = useToast()
  const { user } = useAuth()
  const { preset, de, ate, aplicarPreset, marcarCustom, onDeChange, onAteChange } =
    useDashboardPeriodo('este_mes')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [data, setData] = useState<Dashboard.ChatsResponse | null>(null)
  const [setoresLista, setSetoresLista] = useState<Setores.Setor[]>([])
  const [loading, setLoading] = useState(true)
  const [semPermissao, setSemPermissao] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const drill = useDashboardDrilldown()
  const [reloadKey, setReloadKey] = useState(0)

  const relatorioHref = useMemo(() => {
    const params = new URLSearchParams()
    if (de) params.set('de', de)
    if (ate) params.set('ate', ate)
    if (setorId !== '') params.set('setor_id', String(setorId))
    const qs = params.toString()
    return qs ? `/relatorios/chats?${qs}` : '/relatorios/chats'
  }, [de, ate, setorId])

  useEffect(() => {
    setores
      .list({ limit: 100, ordenar_por: 'nome', ordem: 'asc' })
      .then((s) => setSetoresLista(s.items))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    setSemPermissao(false)
    dashboard
      .getChats({
        de,
        ate,
        setor_id: setorId === '' ? undefined : setorId,
        ...drill.apiParams,
      })
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setSemPermissao(true)
          toast.showWarning(err.message || 'Você não tem permissão para ver este dashboard.')
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Não encontramos os dados do dashboard de WhatsApp.')
        setError(m.titulo)
        toast.showError(mensagemFalhaParaToast(m))
      })
      .finally(() => setLoading(false))
  }, [de, ate, setorId, drill.apiParams, reloadKey, toast])

  const atendentesChart = useMemo(
    () => (data?.por_atendente ?? []).map((a) => ({ id: a.id, nome: a.nome, total: a.total })),
    [data],
  )

  const volumeChart = useMemo(
    () =>
      (data?.volume_por_dia ?? []).map((d) => ({
        ...d,
        label: formatarDiaCurto(d.dia),
      })),
    [data],
  )

  const avaliacoesChart = useMemo(() => {
    if (!data?.avaliacoes.por_nota) return []
    return [1, 2, 3, 4, 5].map((n) => ({
      nota: `${n}★`,
      notaValor: String(n),
      total: data.avaliacoes.por_nota[String(n)] ?? 0,
    }))
  }, [data])

  const encerramentosChart = useMemo(
    () => (data?.encerramentos ?? []).map((e) => ({ nome: e.rotulo, tipo: e.tipo, total: e.total })),
    [data],
  )

  const estadoChart = useMemo(
    () =>
      (data?.por_estado_atual ?? []).map((e) => ({
        nome: e.rotulo,
        chave: e.chave ?? e.rotulo,
        total: e.total,
      })),
    [data],
  )

  const semDados =
    data != null &&
    data.volume_por_dia.every((d) => d.abertos === 0 && d.fechados === 0) &&
    data.por_estado_atual.every((e) => e.total === 0)

  if (loading && !data) {
    return <DashboardChatsSkeleton />
  }

  if (semPermissao) {
    return (
      <PageContainer>
        <SemPermissao
          title="Você não tem permissão para acessar o dashboard de WhatsApp."
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
        title="Dashboard — WhatsApp"
        subtitle={`Indicadores de atendimento · ${formatarIntervaloPeriodo(data.de, data.ate)}`}
      />

      <DashboardNav
        actions={
          <>
            <Link to="/chat/atendendo">
              <Button>Ir para atendimento</Button>
            </Link>
            <Link to="/whatsapp/avaliacoes">
              <Button variant="secondary">Ver avaliações</Button>
            </Link>
            {user?.role === 'admin' ? (
              <Link to={relatorioHref}>
                <Button variant="secondary">Exportar planilha</Button>
              </Link>
            ) : null}
          </>
        }
      />

      <DashboardCanalComparativo snapshot={data.snapshot} />

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
        </div>
      </Card>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Espera na fila"
          dica="Tempo médio entre a primeira mensagem do cliente e o momento em que um atendente assume o chat."
          value={formatarHoras(data.tempo_espera_medio_horas)}
          hint="Até o atendente assumir"
          borderClass="border-l-4 border-l-amber-400"
        />
        <MetricCard
          label="Duração do atendimento"
          dica="Tempo médio com o chat em atendimento, da assunção até o encerramento."
          value={formatarHoras(data.tempo_atendimento_medio_horas)}
          hint="Da assunção ao encerramento"
          borderClass="border-l-4 border-l-cyan-500"
        />
        <MetricCard
          label="Satisfação do cliente"
          dica="Nota média de 1 a 5 estrelas após conversas no WhatsApp."
          hint={
            data.avaliacoes.total_avaliacoes === 0
              ? 'Nenhuma avaliação no período'
              : `${data.avaliacoes.total_avaliacoes} ${data.avaliacoes.total_avaliacoes === 1 ? 'avaliação' : 'avaliações'}`
          }
          borderClass="border-l-4 border-l-violet-400"
        >
          <div className="mt-2">
            <NotaEstrelasMedia media={data.avaliacoes.media} size="md" />
          </div>
        </MetricCard>
        <MetricCard
          label="Chats com ticket vinculado"
          dica="Percentual de conversas abertas no período que geraram ou foram ligadas a um ticket."
          value={formatarPct(data.pct_com_ticket_vinculado)}
          hint="Integração ticket ↔ WhatsApp"
          borderClass="border-l-4 border-l-emerald-400"
        />
      </div>

      {semDados ? (
        <Card>
          <p className="text-center text-slate-500 dark:text-slate-400">
            Nenhum chat no período selecionado. Ajuste os filtros ou aguarde novas conversas.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <Card
            title="Conversas por dia"
            description="Chats iniciados e encerrados em cada dia do período"
          >
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={volumeChart}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip {...chartTooltipProps} />
                  <Legend />
                  <Line type="monotone" dataKey="abertos" name="Iniciados" stroke="#10b981" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="fechados" name="Encerrados" stroke="#64748b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card
            title="Chats abertos agora"
            description="Clique em uma situação para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {estadoChart.every((e) => e.total === 0) ? (
                <p className="text-slate-500 dark:text-slate-400">Nenhum chat aberto no momento.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={estadoChart}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip {...chartTooltipProps} />
                    <Bar
                      dataKey="total"
                      name="Chats"
                      radius={[4, 4, 0, 0]}
                      {...barClickableProps}
                      onClick={(bar) => {
                        const p = bar?.payload as { chave?: string; nome?: string }
                        if (p?.chave && p.nome) drill.toggle('estado', p.chave, p.nome)
                      }}
                    >
                      {estadoChart.map((entry) => (
                        <Cell
                          key={entry.chave}
                          fill={corDrill('#10b981', drill.isSelected('estado', entry.chave), drill.hasSelection)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Como os chats foram encerrados"
            description="Clique em um tipo de encerramento para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {encerramentosChart.every((e) => e.total === 0) ? (
                <p className="text-slate-500 dark:text-slate-400">Nenhum encerramento no período.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={encerramentosChart}
                      dataKey="total"
                      nameKey="nome"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label={({ name, value }) => `${name}: ${value}`}
                      {...barClickableProps}
                      onClick={(entry) => {
                        const p = entry as { tipo?: string; nome?: string }
                        if (p.tipo && p.nome) drill.toggle('encerramento', p.tipo, p.nome)
                      }}
                    >
                      {encerramentosChart.map((entry, i) => (
                        <Cell
                          key={entry.tipo}
                          fill={corDrill(
                            CORES_ENCERRAMENTO[i % CORES_ENCERRAMENTO.length],
                            drill.isSelected('encerramento', entry.tipo),
                            drill.hasSelection,
                          )}
                        />
                      ))}
                    </Pie>
                    <Tooltip {...chartTooltipProps} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          <Card
            title="Distribuição das avaliações"
            description="Clique em uma nota para filtrar os demais gráficos e indicadores"
          >
            <div className="h-72">
              {data.avaliacoes.total_avaliacoes === 0 ? (
                <p className="text-slate-500 dark:text-slate-400">Sem avaliações no período.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={avaliacoesChart}>
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
                      {avaliacoesChart.map((entry) => (
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
              title="Atendentes com mais chats assumidos"
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
                      name="Chats assumidos"
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
                            '#0ea5e9',
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

      <DashboardDemandasAnalise
        data={data}
        de={de}
        ate={ate}
        setorId={setorId}
        isAdmin={user?.role === 'admin'}
        onRecarregar={() => setReloadKey((k) => k + 1)}
      />
    </PageContainer>
  )
}
