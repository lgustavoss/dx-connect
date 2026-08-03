import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { dashboard, type Dashboard } from '../../api/client'
import { useToast } from '../ui/Toast'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { barClickableProps, chartTooltipProps } from './dashboardChartUtils'
import { corDrill } from './useDashboardDrilldown'
import { exibirProtocolo } from '../../lib/exibirProtocolo'

type FiltroDemanda = {
  naturezaId: number | null
  naturezaNome: string | null
  motivoId: number | null
  motivoNome: string | null
}

type Props = {
  data: Dashboard.ChatsResponse
  de: string
  ate: string
  setorId: number | ''
  redeId?: number
  empresaId?: number
  isAdmin: boolean
  onRecarregar: () => void
}

function rotuloDesfecho(d: string): string {
  if (d === 'resolvido_sessao') return 'Resolvido na sessão'
  if (d === 'escalado_ticket') return 'Escalado para ticket'
  return d
}

export function DashboardDemandasAnalise({
  data,
  de,
  ate,
  setorId,
  redeId,
  empresaId,
  isAdmin,
  onRecarregar,
}: Props) {
  const toast = useToast()
  const [filtro, setFiltro] = useState<FiltroDemanda>({
    naturezaId: null,
    naturezaNome: null,
    motivoId: null,
    motivoNome: null,
  })
  const [itens, setItens] = useState<Dashboard.DemandaDrillItem[]>([])
  const [total, setTotal] = useState(0)
  const [loadingLista, setLoadingLista] = useState(false)
  const [acaoKey, setAcaoKey] = useState<string | null>(null)

  const temFiltro = filtro.naturezaId != null || filtro.motivoId != null

  useEffect(() => {
    if (!temFiltro) {
      setItens([])
      setTotal(0)
      return
    }
    setLoadingLista(true)
    dashboard
      .getChatsDemandas({
        de,
        ate,
        setor_id: setorId === '' ? undefined : setorId,
        rede_id: redeId,
        empresa_id: empresaId,
        natureza_id: filtro.naturezaId ?? undefined,
        motivo_id: filtro.motivoId ?? undefined,
        limit: 40,
      })
      .then((res) => {
        setItens(res.items)
        setTotal(res.total)
      })
      .catch(() => {
        setItens([])
        setTotal(0)
        toast.showError('Não foi possível carregar as demandas filtradas.')
      })
      .finally(() => setLoadingLista(false))
  }, [temFiltro, de, ate, setorId, redeId, empresaId, filtro.naturezaId, filtro.motivoId, toast])

  const naturezaChart = (data.demandas_por_natureza ?? []).map((d) => ({
    id: d.id,
    nome: d.nome,
    total: d.total,
  }))
  const motivoChart = (data.demandas_por_motivo ?? []).map((d) => ({
    id: d.id,
    nome: d.nome,
    total: d.total,
  }))

  const limparFiltro = () =>
    setFiltro({ naturezaId: null, naturezaNome: null, motivoId: null, motivoNome: null })

  const aceitar = async (s: Dashboard.SugestaoMotivoOutros) => {
    const key = `${s.natureza_id}:${s.texto_normalizado}`
    setAcaoKey(key)
    try {
      await dashboard.aceitarSugestaoMotivoOutros({
        natureza_id: s.natureza_id,
        texto_normalizado: s.texto_normalizado,
        nome: s.texto_exemplo.slice(0, 120),
      })
      toast.showSuccess('Motivo criado no catálogo a partir da sugestão.')
      onRecarregar()
    } catch {
      toast.showError('Não foi possível criar o motivo.')
    } finally {
      setAcaoKey(null)
    }
  }

  const ignorar = async (s: Dashboard.SugestaoMotivoOutros) => {
    const key = `${s.natureza_id}:${s.texto_normalizado}`
    setAcaoKey(key)
    try {
      await dashboard.ignorarSugestaoMotivoOutros({
        natureza_id: s.natureza_id,
        texto_normalizado: s.texto_normalizado,
        texto_exemplo: s.texto_exemplo,
      })
      toast.showSuccess('Sugestão ignorada.')
      onRecarregar()
    } catch {
      toast.showError('Não foi possível ignorar a sugestão.')
    } finally {
      setAcaoKey(null)
    }
  }

  return (
    <div className="mt-6 space-y-6">
      {data.demanda_maior ? (
        <Card className="border-l-4 border-l-violet-500">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Maior demanda no período</p>
          <p className="mt-1 text-xl font-bold text-slate-800 dark:text-slate-100">
            {data.demanda_maior.nome}{' '}
            <span className="text-base font-semibold text-violet-600 dark:text-violet-400">
              ({data.demanda_maior.total})
            </span>
          </p>
        </Card>
      ) : null}

      {(data.insights_demandas ?? []).length > 0 ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {data.insights_demandas.map((ins) => (
            <Card
              key={`${ins.tipo}-${ins.natureza_id}-${ins.motivo_id}`}
              className={
                ins.tipo === 'avaliar_atualizacao'
                  ? 'border-l-4 border-l-amber-500'
                  : 'border-l-4 border-l-sky-500'
              }
            >
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{ins.titulo}</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{ins.detalhe}</p>
              {ins.natureza_id != null ? (
                <Button
                  type="button"
                  variant="secondary"
                  className="mt-3"
                  onClick={() =>
                    setFiltro({
                      naturezaId: ins.natureza_id,
                      naturezaNome: null,
                      motivoId: ins.motivo_id,
                      motivoNome: null,
                    })
                  }
                >
                  Ver demandas
                </Button>
              ) : null}
            </Card>
          ))}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card
          title="Demandas por natureza"
          description="Clique numa barra para listar os chats dessa natureza"
        >
          <div className="h-72">
            {naturezaChart.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400">Nenhuma demanda registrada no período.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={naturezaChart}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip {...chartTooltipProps} />
                  <Bar
                    dataKey="total"
                    name="Demandas"
                    radius={[4, 4, 0, 0]}
                    {...barClickableProps}
                    onClick={(bar) => {
                      const p = bar?.payload as { id?: number; nome?: string }
                      if (p?.id != null && p.nome) {
                        setFiltro({
                          naturezaId: p.id,
                          naturezaNome: p.nome,
                          motivoId: null,
                          motivoNome: null,
                        })
                      }
                    }}
                  >
                    {naturezaChart.map((entry) => (
                      <Cell
                        key={entry.id}
                        fill={corDrill(
                          '#8b5cf6',
                          filtro.naturezaId === entry.id && filtro.motivoId == null,
                          temFiltro,
                        )}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card title="Demandas por motivo" description="Clique numa barra para listar os chats desse motivo">
          <div className="h-72">
            {motivoChart.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400">Nenhum motivo registrado no período.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={motivoChart}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip {...chartTooltipProps} />
                  <Bar
                    dataKey="total"
                    name="Demandas"
                    radius={[4, 4, 0, 0]}
                    {...barClickableProps}
                    onClick={(bar) => {
                      const p = bar?.payload as { id?: number; nome?: string }
                      if (p?.id != null && p.nome) {
                        setFiltro({
                          naturezaId: null,
                          naturezaNome: null,
                          motivoId: p.id,
                          motivoNome: p.nome,
                        })
                      }
                    }}
                  >
                    {motivoChart.map((entry) => (
                      <Cell
                        key={entry.id}
                        fill={corDrill('#a855f7', filtro.motivoId === entry.id, temFiltro)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      <Card
        title="Ranking por empresa"
        description="Volume de demandas no período e natureza dominante de cada cliente"
      >
        {(data.demandas_por_empresa ?? []).length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Sem demandas com empresa no período.</p>
        ) : (
          <ul className="divide-y divide-slate-200 dark:divide-slate-700">
            {data.demandas_por_empresa.map((e) => (
              <li key={`${e.empresa_id ?? 'none'}-${e.empresa_nome}`} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                <div>
                  <p className="font-medium text-slate-800 dark:text-slate-100">{e.empresa_nome}</p>
                  {e.natureza_dominante_nome ? (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Dominante: {e.natureza_dominante_nome}
                    </p>
                  ) : null}
                </div>
                <span className="font-semibold text-slate-700 dark:text-slate-200">{e.total}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {temFiltro ? (
        <Card
          title="Demandas filtradas"
          description={
            filtro.motivoNome
              ? `Motivo: ${filtro.motivoNome}`
              : filtro.naturezaNome
                ? `Natureza: ${filtro.naturezaNome}`
                : 'Filtro ativo'
          }
        >
          <div className="mb-3">
            <Button type="button" variant="secondary" onClick={limparFiltro}>
              Limpar filtro
            </Button>
          </div>
          {loadingLista ? (
            <p className="text-slate-500 dark:text-slate-400">A carregar…</p>
          ) : itens.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400">Nenhuma demanda neste filtro.</p>
          ) : (
            <>
              <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
                {total} resultado{total === 1 ? '' : 's'} (a mostrar até {itens.length})
              </p>
              <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                {itens.map((item) => (
                  <li key={item.demanda_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                    <div className="min-w-0">
                      <Link
                        to={`/chat/c/${item.chat_id}`}
                        className="font-medium text-cyan-700 hover:text-cyan-800 dark:text-cyan-400"
                      >
                        {exibirProtocolo(item.protocolo)}
                      </Link>
                      <p className="text-slate-600 dark:text-slate-400">
                        {[item.cliente_nome, item.empresa_nome].filter(Boolean).join(' · ') || '—'}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-500">
                        {item.natureza_nome}
                        {item.motivo_nome ? ` · ${item.motivo_nome}` : ''} · {rotuloDesfecho(item.desfecho)}
                        {item.descricao_curta ? ` · ${item.descricao_curta}` : ''}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      ) : null}

      {isAdmin && (data.sugestoes_motivo_outros ?? []).length > 0 ? (
        <Card
          title="Sugestões de novo motivo (a partir de «Outros»)"
          description="Mesma descrição repetida várias vezes — aceite para criar no catálogo ou ignore"
        >
          <ul className="space-y-3">
            {data.sugestoes_motivo_outros.map((s) => {
              const key = `${s.natureza_id}:${s.texto_normalizado}`
              const busy = acaoKey === key
              return (
                <li
                  key={key}
                  className="flex flex-col gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium text-slate-800 dark:text-slate-100">{s.texto_exemplo}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {s.natureza_nome} · {s.ocorrencias} ocorrências (limiar {s.limiar})
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" disabled={busy} onClick={() => void aceitar(s)}>
                      Criar motivo
                    </Button>
                    <Button type="button" variant="secondary" disabled={busy} onClick={() => void ignorar(s)}>
                      Ignorar
                    </Button>
                  </div>
                </li>
              )
            })}
          </ul>
        </Card>
      ) : null}
    </div>
  )
}
