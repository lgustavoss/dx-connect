import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, dashboard, type Dashboard } from '../../api/client'
import { useDashboardPeriodo } from '../../hooks/useDashboardPeriodo'
import { useToast } from '../ui/Toast'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { DashboardPeriodoFiltro } from './DashboardPeriodoFiltro'
import { DashboardDemandasAnalise } from './DashboardDemandasAnalise'
import { formatarIntervaloPeriodo, MetricCard } from './dashboardMetrics'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'

type Props = {
  /** Escopo da rede (agrega todas as empresas). */
  redeId?: number
  /** Escopo de uma empresa. */
  empresaId?: number
  /** Navegação para listagens no mesmo contexto (aba ou rota). */
  onVerTickets?: () => void
  onVerChats?: () => void
  hrefTickets?: string
  hrefChats?: string
}

/**
 * Painel de análises no detalhe Rede/Empresa (#595).
 * Reutiliza APIs de dashboard + análise de demandas (#594) e filtro de período (#599).
 */
export function PainelAnalisesCliente({
  redeId,
  empresaId,
  onVerTickets,
  onVerChats,
  hrefTickets,
  hrefChats,
}: Props) {
  const toast = useToast()
  const { preset, de, ate, aplicarPreset, marcarCustom, onDeChange, onAteChange } =
    useDashboardPeriodo('este_mes')
  const [ticketsDash, setTicketsDash] = useState<Dashboard.TicketsResponse | null>(null)
  const [chatsDash, setChatsDash] = useState<Dashboard.ChatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (redeId == null && empresaId == null) return
    setLoading(true)
    setError(null)
    const ticketsParams: Parameters<typeof dashboard.getTickets>[0] = { de, ate }
    if (redeId != null) ticketsParams.rede_id = redeId
    if (empresaId != null) {
      ticketsParams.drill_tipo = 'empresa'
      ticketsParams.drill_valor = String(empresaId)
    }
    const chatsParams: Parameters<typeof dashboard.getChats>[0] = { de, ate }
    if (redeId != null) chatsParams.rede_id = redeId
    if (empresaId != null) chatsParams.empresa_id = empresaId

    Promise.all([dashboard.getTickets(ticketsParams), dashboard.getChats(chatsParams)])
      .then(([t, c]) => {
        setTicketsDash(t)
        setChatsDash(c)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setError('Sem permissão para ver estas análises.')
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Não encontramos as análises deste cliente.')
        setError(m.titulo)
        toast.showError(mensagemFalhaParaToast(m))
      })
      .finally(() => setLoading(false))
  }, [redeId, empresaId, de, ate, reloadKey, toast])

  if (loading && !ticketsDash && !chatsDash) {
    return (
      <div className="space-y-4">
        <div className="h-12 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ))}
        </div>
      </div>
    )
  }

  if (error && !ticketsDash) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <p className="text-slate-600 dark:text-slate-300">{error}</p>
        <Button type="button" onClick={() => setReloadKey((k) => k + 1)}>
          Tentar novamente
        </Button>
      </div>
    )
  }

  const abertosPeriodo = ticketsDash?.volume_por_dia.reduce((s, d) => s + d.abertos, 0) ?? 0
  const fechadosPeriodo = ticketsDash?.volume_por_dia.reduce((s, d) => s + d.fechados, 0) ?? 0
  const chatsAbertos = chatsDash?.volume_por_dia.reduce((s, d) => s + d.abertos, 0) ?? 0
  const totalDemandas = (chatsDash?.demandas_por_natureza ?? []).reduce((s, d) => s + d.total, 0)

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end lg:justify-between">
          <DashboardPeriodoFiltro
            preset={preset}
            de={de}
            ate={ate}
            onPreset={aplicarPreset}
            onCustom={marcarCustom}
            onDeChange={onDeChange}
            onAteChange={onAteChange}
          />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Período: {formatarIntervaloPeriodo(de, ate)}
          </p>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Tickets abertos no período"
          value={String(abertosPeriodo)}
          borderClass="border-l-4 border-l-slate-400"
        />
        <MetricCard
          label="Tickets fechados no período"
          value={String(fechadosPeriodo)}
          borderClass="border-l-4 border-l-emerald-400"
        />
        <MetricCard
          label="Chats iniciados"
          value={String(chatsAbertos)}
          borderClass="border-l-4 border-l-cyan-500"
        />
        <MetricCard
          label="Demandas registradas"
          value={String(totalDemandas)}
          borderClass="border-l-4 border-l-violet-500"
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {onVerTickets ? (
          <Button type="button" variant="secondary" onClick={onVerTickets}>
            Ver tickets deste contexto
          </Button>
        ) : hrefTickets ? (
          <Link to={hrefTickets}>
            <Button variant="secondary">Ver tickets deste contexto</Button>
          </Link>
        ) : null}
        {onVerChats ? (
          <Button type="button" variant="secondary" onClick={onVerChats}>
            Ver chats deste contexto
          </Button>
        ) : hrefChats ? (
          <Link to={hrefChats}>
            <Button variant="secondary">Ver chats deste contexto</Button>
          </Link>
        ) : null}
        <Link to="/dashboard/chats">
          <Button variant="secondary">Dashboard WhatsApp global</Button>
        </Link>
      </div>

      {ticketsDash && (ticketsDash.por_motivo?.length ?? 0) > 0 ? (
        <Card title="Tickets — top motivos" description="No período selecionado">
          <ul className="space-y-1">
            {ticketsDash.por_motivo.slice(0, 8).map((m) => (
              <li key={m.id} className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">{m.nome}</span>
                <span className="font-medium text-slate-800 dark:text-slate-100">{m.total}</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {redeId != null && ticketsDash && (ticketsDash.por_empresa?.length ?? 0) > 0 ? (
        <Card title="Tickets — ranking de empresas da rede" description="Volume no período">
          <ul className="space-y-1">
            {ticketsDash.por_empresa.slice(0, 10).map((e) => (
              <li key={e.id} className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">{e.nome}</span>
                <span className="font-medium text-slate-800 dark:text-slate-100">{e.total}</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {chatsDash ? (
        <DashboardDemandasAnalise
          data={chatsDash}
          de={de}
          ate={ate}
          setorId=""
          redeId={redeId}
          empresaId={empresaId}
          isAdmin
          onRecarregar={() => setReloadKey((k) => k + 1)}
        />
      ) : (
        <p className="text-slate-500 dark:text-slate-400">Sem dados de chats/demandas no período.</p>
      )}
    </div>
  )
}
