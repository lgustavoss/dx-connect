import { useState, useEffect, useMemo } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { Link } from 'react-router-dom'
import { ApiError, dashboard } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { IconEye } from '../components/ui/IconEye'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'

type ColunaUltimos = 'protocolo' | 'empresa' | 'assunto' | 'status'

export function Dashboard() {
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna } = useOrdenacaoLista<ColunaUltimos>()
  const [data, setData] = useState<Awaited<ReturnType<typeof dashboard.get>> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setForbidden(false)
    dashboard
      .get()
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          toast.showWarning(err.message || 'Você não tem permissão para ver o dashboard.')
          return
        }
        const msg = err instanceof Error ? err.message : 'Erro ao carregar'
        setError(msg)
        toast.showError(msg)
      })
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recarrega só quando reloadKey muda
  }, [reloadKey])

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
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <span className="text-slate-500 dark:text-slate-400">Carregando dashboard...</span>
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para acessar o dashboard."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil e vínculos de setor."
          voltarPara="/tickets"
          voltarLabel="Ir para Tickets"
        />
      </div>
    )
  }

  if (error || !data) {
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

  const { resumo } = data

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Dashboard</h1>
        <Link to="/tickets/novo">
          <Button>Novo ticket</Button>
        </Link>
      </div>

      {/* Cards de resumo */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="border-l-4 border-l-slate-400">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total de tickets</p>
          <p className="mt-1 text-3xl font-bold text-slate-800 dark:text-slate-100">{resumo.total_tickets}</p>
        </Card>
        <Card className="border-l-4 border-l-amber-400">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Abertos hoje</p>
          <p className="mt-1 text-3xl font-bold text-slate-800 dark:text-slate-100">{resumo.abertos_hoje}</p>
        </Card>
        <Card className="border-l-4 border-l-emerald-400 sm:col-span-2 lg:col-span-1">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Por status</p>
          <ul className="mt-2 space-y-1">
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

      {/* Últimos tickets */}
      <Card title="Últimos tickets">
        {ultimos_tickets.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum ticket ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700/80 text-slate-600 dark:text-slate-400">
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
                  <tr key={t.id} className="border-b border-slate-100 dark:border-slate-700/60">
                    <td className="py-3 pr-4 font-mono text-slate-800 dark:text-slate-100">{t.protocolo}</td>
                    <td className="py-3 pr-4">{t.empresa_nome ?? t.empresa_id}</td>
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
    </div>
  )
}
