import { useState, useEffect, useMemo, type ReactNode } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { Link } from 'react-router-dom'
import { ApiError, dashboard, type Dashboard } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { IconEye } from '../components/ui/IconEye'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { exibirProtocolo } from '../lib/exibirProtocolo'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { DashboardCanalComparativo, snapshotFromGeral } from '../components/dashboard/DashboardCanalComparativo'
import { DashboardNav } from '../components/dashboard/DashboardNav'
import { DashboardPeriodoFiltro } from '../components/dashboard/DashboardPeriodoFiltro'
import { formatarIntervaloPeriodo } from '../components/dashboard/dashboardMetrics'
import { NotaEstrelasMedia } from '../components/ui/NotaEstrelasMedia'
import { useDashboardPeriodo } from '../hooks/useDashboardPeriodo'

type ColunaUltimos = 'protocolo' | 'empresa' | 'assunto' | 'status'

function DashboardSkeleton() {
  return (
    <PageContainer>
      <div className="mb-6 h-9 w-48 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-900/60"
          />
        ))}
      </div>
      <div className="mt-6 h-72 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900/60" />
    </PageContainer>
  )
}

function rotuloEstadoChat(estado: string): string {
  const map: Record<string, string> = {
    aguardando_atendente: 'Aguardando',
    em_atendimento: 'Em atendimento',
    aguardando_avaliacao: 'Aguard. avaliação',
    encerrado: 'Encerrado',
  }
  return map[estado] ?? estado
}

function MetricCard({
  label,
  value,
  hint,
  borderClass,
  href,
  hrefLabel,
  children,
}: {
  label: string
  value?: string | number
  hint?: string
  borderClass: string
  href?: string
  hrefLabel?: string
  children?: ReactNode
}) {
  return (
    <Card className={`flex flex-col ${borderClass}`}>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
      {children ?? (
        <p className="mt-1 text-3xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
      )}
      {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
      {href && hrefLabel ? (
        <Link to={href} className="mt-3 text-sm font-medium text-cyan-700 hover:text-cyan-800 dark:text-cyan-400 dark:hover:text-cyan-300">
          {hrefLabel} →
        </Link>
      ) : null}
    </Card>
  )
}

export function Dashboard() {
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna } = useOrdenacaoLista<ColunaUltimos>()
  const { preset, de, ate, aplicarPreset, marcarCustom, onDeChange, onAteChange } =
    useDashboardPeriodo('este_mes')
  const [geral, setGeral] = useState<Dashboard.GeralResponse | null>(null)
  const [data, setData] = useState<Awaited<ReturnType<typeof dashboard.get>> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setForbidden(false)
    Promise.all([dashboard.getGeral({ de, ate }), dashboard.get()])
      .then(([geralRes, dashRes]) => {
        setGeral(geralRes)
        setData(dashRes)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          toast.showWarning(err.message || 'Você não tem permissão para ver o dashboard.')
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Não encontramos os dados do dashboard.')
        const msg = [m.titulo, m.detalhe].filter(Boolean).join(' ')
        setError(msg)
        toast.showError(mensagemFalhaParaToast(err, msg))
      })
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps -- toast estável; recarrega com período/reload
  }, [reloadKey, de, ate])

  const ultimos_tickets = useMemo(() => data?.ultimos_tickets ?? [], [data?.ultimos_tickets])

  const ultimosOrdenados = useMemo(() => {
    if (!ordenarPor) return ultimos_tickets
    const m = ordem === 'asc' ? 1 : -1
    const cmp = (a: string, b: string) => m * a.localeCompare(b, 'pt-BR')
    const rows = [...ultimos_tickets]
    rows.sort((x, y) => {
      let r = 0
      if (ordenarPor === 'protocolo') r = cmp(x.protocolo, y.protocolo)
      else if (ordenarPor === 'empresa')
        r = cmp(x.empresa_nome ?? String(x.empresa_id ?? ''), y.empresa_nome ?? String(y.empresa_id ?? ''))
      else if (ordenarPor === 'assunto') r = cmp(x.assunto, y.assunto)
      else r = cmp(x.status_nome ?? String(x.status_id ?? ''), y.status_nome ?? String(y.status_id ?? ''))
      return r
    })
    return rows
  }, [ultimos_tickets, ordenarPor, ordem])

  if (loading) {
    return <DashboardSkeleton />
  }

  if (forbidden) {
    return (
      <PageContainer>
        <SemPermissao
          title="Você não tem permissão para acessar o dashboard."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil e vínculos de setor."
          voltarPara="/tickets"
          voltarLabel="Ir para Tickets"
        />
      </PageContainer>
    )
  }

  if (error || !data || !geral) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 px-4">
        <p className="max-w-md text-center text-slate-600 dark:text-slate-400">
          {error ?? 'Dados não disponíveis.'}
        </p>
        <Button type="button" onClick={() => setReloadKey((k) => k + 1)}>
          Tentar novamente
        </Button>
      </div>
    )
  }

  const { resumo, resumo_chats } = data

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        subtitle={`CSAT e indicadores · ${formatarIntervaloPeriodo(geral.de, geral.ate)}`}
      />

      <DashboardNav
        actions={
          <>
            <Link to="/tickets/novo">
              <Button variant="secondary">Novo ticket</Button>
            </Link>
            <Link to="/chat/atendendo">
              <Button variant="secondary">Ir para WhatsApp</Button>
            </Link>
          </>
        }
      />

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
          <p className="text-xs text-slate-500 dark:text-slate-400 lg:max-w-xs">
            Filas e SLA são situação atual. O período aplica-se à satisfação (CSAT).
          </p>
        </div>
      </Card>

      {geral ? <DashboardCanalComparativo snapshot={snapshotFromGeral(geral)} /> : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          label="Tickets abertos"
          value={geral.tickets_abertos}
          borderClass="border-l-4 border-l-slate-400"
          href="/tickets?situacao=abertos"
          hrefLabel="Ver tickets abertos"
        />
        <MetricCard
          label="Fila sem responsável"
          value={geral.tickets_sem_responsavel}
          borderClass="border-l-4 border-l-amber-400"
          href="/tickets?sem_responsavel=1"
          hrefLabel="Ver tickets sem responsável"
        />
        <MetricCard
          label="SLA violado (abertos)"
          value={geral.sla_violacoes_abertas}
          borderClass="border-l-4 border-l-red-500"
          hint="Tickets abertos com meta de SLA estourada"
          href="/tickets?situacao=abertos&sla_violado=1"
          hrefLabel="Ver tickets com SLA violado"
        />
        <MetricCard
          label="SLA em risco (abertos)"
          value={geral.sla_em_risco_abertas}
          borderClass="border-l-4 border-l-amber-500"
          hint="Tickets abertos próximos do limite de SLA"
          href="/tickets?situacao=abertos&sla_em_risco=1"
          hrefLabel="Ver tickets com SLA em risco"
        />
        <MetricCard
          label="WhatsApp aguardando"
          value={geral.chats_aguardando_atendente}
          borderClass="border-l-4 border-l-emerald-400"
          href="/chat/atendendo"
          hrefLabel="Ir para fila WhatsApp"
        />
        <MetricCard
          label="WhatsApp em atendimento"
          value={geral.chats_em_atendimento}
          borderClass="border-l-4 border-l-cyan-500"
          href="/chat/atendendo"
          hrefLabel="Ver central de atendimento"
        />
        <MetricCard
          label="Satisfação — tickets"
          borderClass="border-l-4 border-l-violet-400"
          hint={`${formatarIntervaloPeriodo(geral.de, geral.ate)} · ${geral.csat_tickets.total_avaliacoes} avaliações`}
        >
          <div className="mt-2">
            <NotaEstrelasMedia media={geral.csat_tickets.media} size="lg" />
          </div>
        </MetricCard>
        <MetricCard
          label="Satisfação — WhatsApp"
          borderClass="border-l-4 border-l-pink-400"
          hint={`${formatarIntervaloPeriodo(geral.de, geral.ate)} · ${geral.csat_chats.total_avaliacoes} avaliações`}
        >
          <div className="mt-2">
            <NotaEstrelasMedia media={geral.csat_chats.media} size="lg" />
          </div>
        </MetricCard>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Tickets</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card className="border-l-4 border-l-slate-300">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total de tickets</p>
              <p className="mt-1 text-3xl font-bold text-slate-800 dark:text-slate-100">{resumo.total_tickets}</p>
            </Card>
            <Card className="border-l-4 border-l-amber-300">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Abertos hoje</p>
              <p className="mt-1 text-3xl font-bold text-slate-800 dark:text-slate-100">{resumo.abertos_hoje}</p>
            </Card>
          </div>
          <Card title="Por status">
            <ul className="space-y-1">
              {resumo.por_status.length === 0 ? (
                <li className="text-slate-500 dark:text-slate-400">Nenhum ticket</li>
              ) : (
                resumo.por_status.map((s) => (
                  <li key={s.status_id} className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">{s.status_nome}</span>
                    <span className="font-medium text-slate-800 dark:text-slate-100">{s.total}</span>
                  </li>
                ))
              )}
            </ul>
          </Card>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">WhatsApp</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card className="border-l-4 border-l-emerald-300">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total de conversas</p>
              <p className="mt-1 text-3xl font-bold text-slate-800 dark:text-slate-100">{resumo_chats.total_chats}</p>
            </Card>
            <Card className="border-l-4 border-l-teal-300">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Iniciadas hoje</p>
              <p className="mt-1 text-3xl font-bold text-slate-800 dark:text-slate-100">{resumo_chats.iniciados_hoje}</p>
            </Card>
          </div>
          <Card title="Por situação">
            <ul className="space-y-1">
              {resumo_chats.por_estado.length === 0 ? (
                <li className="text-slate-500 dark:text-slate-400">Nenhuma conversa</li>
              ) : (
                resumo_chats.por_estado.map((e) => (
                  <li key={e.estado} className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">{e.rotulo}</span>
                    <span className="font-medium text-slate-800 dark:text-slate-100">{e.total}</span>
                  </li>
                ))
              )}
            </ul>
          </Card>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title="Últimos tickets">
        {ultimos_tickets.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum ticket ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800/80 text-slate-600 dark:text-slate-400">
                  <CabecalhoOrdenavel
                    coluna="protocolo"
                    rotulo="Protocolo"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <CabecalhoOrdenavel
                    coluna="empresa"
                    rotulo="Empresa"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <CabecalhoOrdenavel
                    coluna="assunto"
                    rotulo="Assunto"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <CabecalhoOrdenavel
                    coluna="status"
                    rotulo="Status"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="pb-2 pr-4 font-medium normal-case"
                  />
                  <th className="pb-2 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {ultimosOrdenados.map((t) => (
                  <tr key={t.id} className="border-b border-slate-100 dark:border-slate-800/60">
                    <td
                      className="max-w-[10rem] truncate py-3 pr-4 font-mono text-slate-800 dark:text-slate-100"
                      title={exibirProtocolo(t.protocolo)}
                    >
                      {exibirProtocolo(t.protocolo)}
                    </td>
                    <td className="py-3 pr-4">
                      {t.empresa_nome ??
                        (t.empresa_nome ?? (t.empresa_id != null ? String(t.empresa_id) : '—'))}
                    </td>
                    <td className="py-3 pr-4">{t.assunto}</td>
                    <td className="py-3 pr-4">{t.status_nome ?? t.status_id}</td>
                    <td className="py-3">
                      <Link
                        to={`/tickets/${t.id}`}
                        aria-label="Ver ticket"
                        className="inline-flex shrink-0"
                      >
                        <Button
                          type="button"
                          variant="ghost"
                          className="inline-flex size-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white p-0 text-slate-600 shadow-sm hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700/80 dark:bg-slate-900/50 dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-slate-100"
                        >
                          <IconEye className="size-5 shrink-0" ariaHidden={false} />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-4">
          <Link to="/tickets">
            <Button variant="secondary">Ver todos os tickets</Button>
          </Link>
        </div>
      </Card>

        <Card title="Últimas conversas WhatsApp">
          {data.ultimos_chats.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400">Nenhuma conversa ainda.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800/80 text-slate-600 dark:text-slate-400">
                    <th className="pb-2 pr-4 font-medium">Protocolo</th>
                    <th className="pb-2 pr-4 font-medium">Cliente</th>
                    <th className="pb-2 pr-4 font-medium">Situação</th>
                    <th className="pb-2 font-medium">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ultimos_chats.map((c) => (
                    <tr key={c.id} className="border-b border-slate-100 dark:border-slate-800/60">
                      <td className="py-3 pr-4 font-mono text-slate-800 dark:text-slate-100">{c.protocolo}</td>
                      <td className="py-3 pr-4">{c.cliente_nome ?? '—'}</td>
                      <td className="py-3 pr-4">{rotuloEstadoChat(c.estado)}</td>
                      <td className="py-3">
                        <Link to={`/chat/c/${c.id}`}>
                          <Button type="button" variant="ghost" className="text-sm">
                            Abrir
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-4">
            <Link to="/chat/atendendo">
              <Button variant="secondary">Ir para WhatsApp</Button>
            </Link>
          </div>
        </Card>
      </div>
    </PageContainer>
  )
}
