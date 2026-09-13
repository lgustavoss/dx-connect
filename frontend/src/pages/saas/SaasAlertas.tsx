import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ApiError,
  saasAlertasOps,
  saasClientes,
  type SaasAlertasOps,
  type SaasClientes,
} from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { PAGE_SIZE_PADRAO } from '../../components/ui/BarraBuscaPaginacao'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { SemPermissao } from '../SemPermissao'

const SEV_OPTS = [
  { value: 'vermelho', label: 'Vermelho' },
  { value: 'amarelo', label: 'Amarelo' },
]

const ESTADO_OPTS = [
  { value: 'ativo', label: 'Ativo' },
  { value: 'mitigado', label: 'Mitigado' },
  { value: 'resolvido', label: 'Resolvido' },
]

const MODULO_OPTS = [
  { value: 'api', label: 'API' },
  { value: 'stack', label: 'Stack' },
  { value: 'sync', label: 'Sync' },
  { value: 'auth', label: 'Auth' },
  { value: 'realtime', label: 'Realtime' },
  { value: 'jobs', label: 'Jobs' },
]

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function tempoDesde(iso: string): string {
  const start = new Date(iso).getTime()
  if (Number.isNaN(start)) return '—'
  const mins = Math.max(0, Math.floor((Date.now() - start) / 60000))
  if (mins < 60) return `${mins} min`
  const horas = Math.floor(mins / 60)
  if (horas < 48) return `${horas} h`
  return `${Math.floor(horas / 24)} d`
}

function badgeSeveridade(sev: SaasAlertasOps.Severidade): string {
  if (sev === 'vermelho') {
    return 'bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-200'
  }
  return 'bg-amber-100 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100'
}

function badgeEstado(estado: SaasAlertasOps.Estado): string {
  if (estado === 'ativo') return 'bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-200'
  if (estado === 'mitigado') return 'bg-sky-100 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'
  return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200'
}

export function SaasAlertas() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [clientes, setClientes] = useState<SaasClientes.Cliente[]>([])
  const [resumo, setResumo] = useState<SaasAlertasOps.Resumo | null>(null)
  const [list, setList] = useState<SaasAlertasOps.Alerta[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loadingClientes, setLoadingClientes] = useState(true)
  const [loading, setLoading] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [detalhe, setDetalhe] = useState<SaasAlertasOps.Alerta | null>(null)

  const clienteIdRaw = searchParams.get('cliente') || ''
  const clienteId = clienteIdRaw ? Number(clienteIdRaw) : null
  const clienteValido = clienteId != null && Number.isFinite(clienteId) && clienteId > 0

  const severidade = searchParams.get('severidade') || ''
  // Ausência do param = padrão "ativo"; `estado=` (vazio) = todos os estados.
  const estado = searchParams.has('estado') ? (searchParams.get('estado') ?? '') : 'ativo'
  const modulo = searchParams.get('modulo') || ''

  function patchFiltros(next: Record<string, string | null>) {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev)
      for (const [k, v] of Object.entries(next)) {
        if (v == null) p.delete(k)
        else p.set(k, v)
      }
      return p
    })
  }

  useEffect(() => {
    setPage(1)
  }, [severidade, estado, modulo, clienteId])

  useEffect(() => {
    setLoadingClientes(true)
    setForbidden(false)
    setIndisponivel(false)
    saasClientes
      .list({ ordenar_por: 'nome', ordem: 'asc', limit: 200, offset: 0 })
      .then(({ items }) => setClientes(items))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os clientes.'))
        setClientes([])
      })
      .finally(() => setLoadingClientes(false))
  }, [toast])

  const clienteOpts = useMemo(
    () =>
      clientes.map((c) => ({
        value: String(c.id),
        label: `${c.nome} (${c.slug})`,
      })),
    [clientes],
  )

  const load = useCallback(() => {
    if (!clienteValido || clienteId == null) {
      setList([])
      setTotal(0)
      setResumo(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    const params = {
      cliente_saas_id: clienteId,
      severidade: severidade || undefined,
      estado: estado || undefined,
      modulo: modulo || undefined,
      offset: (page - 1) * PAGE_SIZE_PADRAO,
      limit: PAGE_SIZE_PADRAO,
    }
    Promise.all([saasAlertasOps.resumo({ cliente_saas_id: clienteId }), saasAlertasOps.list(params)])
      .then(([r, lista]) => {
        setResumo(r)
        setList(lista.items)
        setTotal(lista.total)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os alertas.'))
        setList([])
        setTotal(0)
        setResumo(null)
      })
      .finally(() => setLoading(false))
  }, [clienteId, clienteValido, estado, modulo, page, severidade, toast])

  useEffect(() => {
    load()
  }, [load])

  const abrirDetalhe = useCallback(
    async (id: number) => {
      try {
        const row = await saasAlertasOps.get(id)
        setDetalhe(row)
      } catch (err) {
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível abrir o alerta.'))
      }
    },
    [toast],
  )

  const mitigar = useCallback(
    async (id: number) => {
      try {
        await saasAlertasOps.mitigar(id, { mensagem: 'Mitigado pela equipe Ops no painel' })
        toast.showSuccess('Alerta marcado como mitigado.')
        setDetalhe(null)
        load()
      } catch (err) {
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível mitigar o alerta.'))
      }
    },
    [load, toast],
  )

  const cards = useMemo(() => {
    if (!resumo) return []
    return [
      { label: 'Alertas abertos', value: resumo.alertas_ativos },
      { label: 'Vermelho', value: resumo.por_severidade.vermelho || 0 },
      { label: 'Amarelo', value: resumo.por_severidade.amarelo || 0 },
      { label: 'Instâncias afetadas', value: resumo.instancias_afetadas },
    ]
  }, [resumo])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE_PADRAO))
  const inicio = total === 0 ? 0 : (page - 1) * PAGE_SIZE_PADRAO + 1
  const fim = Math.min(page * PAGE_SIZE_PADRAO, total)

  if (indisponivel) {
    return (
      <SemPermissao
        title="Alertas operacionais não disponíveis nesta instância."
        detail="Este módulo só existe no painel comercial DeskRudder (control-plane)."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  return (
    <ConfigListPageShell
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para ver alertas operacionais."
          detail="Acesso restrito à equipe SaaS DeskRudder."
          voltarPara="/saas/licencas"
          voltarLabel="Voltar para Licenças"
        />
      }
      title="Alertas operacionais"
      subtitle="Selecione um cliente para ver saúde e incidentes — só no painel Ops, sem exposição na app do cliente."
      actions={
        <Button type="button" variant="secondary" onClick={() => load()} disabled={loading || !clienteValido}>
          Atualizar
        </Button>
      }
    >
      <Card className="mb-4 p-4">
        <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="alerta-cliente">
          Cliente
        </label>
        <div className="max-w-md">
          <Select
            id="alerta-cliente"
            aria-label="Selecionar cliente para ver alertas"
            value={clienteValido ? String(clienteId) : ''}
            onChange={(v) => patchFiltros({ cliente: v ? String(v) : null })}
            options={clienteOpts}
            includeEmpty
            emptyLabel="Selecione um cliente…"
            placeholder="Cliente"
            disabled={loadingClientes}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          A listagem só carrega depois da escolha do cliente, para não puxar alertas de toda a base de uma vez.
        </p>
      </Card>

      {!clienteValido ? (
        <Card className="p-8 text-center text-slate-500 dark:text-slate-400">
          Escolha um cliente acima para visualizar os alertas operacionais.
        </Card>
      ) : (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {cards.map((c) => (
              <Card key={c.label} className="p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{c.label}</p>
                <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{loading ? '…' : c.value}</p>
              </Card>
            ))}
          </div>

          {resumo && resumo.modulos_mais_incidentes.length > 0 && (
            <Card className="mb-4 p-4">
              <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-200">Módulos com mais incidentes abertos</p>
              <div className="flex flex-wrap gap-2">
                {resumo.modulos_mais_incidentes.map((m) => (
                  <button
                    key={m.modulo}
                    type="button"
                    className="rounded-lg bg-slate-100 px-3 py-1.5 text-sm text-slate-800 dark:bg-slate-800 dark:text-slate-100"
                    onClick={() => patchFiltros({ modulo: m.modulo })}
                  >
                    {m.modulo}: {m.total}
                  </button>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
              <div className="flex min-w-0 flex-1 flex-wrap gap-2">
                <div className="min-w-[9rem]">
                  <Select
                    aria-label="Filtrar por estado"
                    value={estado}
                    onChange={(v) => patchFiltros({ estado: v == null ? '' : String(v) })}
                    options={ESTADO_OPTS}
                    includeEmpty
                    emptyLabel="Todos os estados"
                    placeholder="Estado"
                    disabled={loading}
                  />
                </div>
                <div className="min-w-[9rem]">
                  <Select
                    aria-label="Filtrar por severidade"
                    value={severidade}
                    onChange={(v) => patchFiltros({ severidade: v ? String(v) : null })}
                    options={SEV_OPTS}
                    includeEmpty
                    emptyLabel="Todas"
                    placeholder="Severidade"
                    disabled={loading}
                  />
                </div>
                <div className="min-w-[9rem]">
                  <Select
                    aria-label="Filtrar por módulo"
                    value={modulo}
                    onChange={(v) => patchFiltros({ modulo: v ? String(v) : null })}
                    options={MODULO_OPTS}
                    includeEmpty
                    emptyLabel="Todos"
                    placeholder="Módulo"
                    disabled={loading}
                  />
                </div>
              </div>
              <div className="flex min-h-[2.5rem] flex-wrap items-center justify-end gap-2 text-sm text-slate-600 dark:text-slate-300">
                <span className="whitespace-nowrap">{total > 0 ? `${inicio}–${fim} de ${total}` : '0 resultados'}</span>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={loading || page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="px-2 py-1 text-xs"
                >
                  Anterior
                </Button>
                <span className="tabular-nums">
                  {page} / {totalPages}
                </span>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={loading || page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  className="px-2 py-1 text-xs"
                >
                  Próxima
                </Button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Alerta</th>
                    <th className="px-4 py-3">Módulo</th>
                    <th className="px-4 py-3">Severidade</th>
                    <th className="px-4 py-3">Estado</th>
                    <th className="px-4 py-3">Desde</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {list.length === 0 && !loading ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                        Nenhum alerta neste filtro para o cliente selecionado.
                      </td>
                    </tr>
                  ) : (
                    list.map((a) => (
                      <tr
                        key={a.id}
                        className="border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900/40"
                      >
                        <td className="px-4 py-3">
                          <div className="font-medium">{a.titulo}</div>
                          <div className="text-xs text-slate-500">{a.codigo_sinal}</div>
                        </td>
                        <td className="px-4 py-3">{a.modulo}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${badgeSeveridade(a.severidade)}`}>
                            {a.severidade}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${badgeEstado(a.estado)}`}>
                            {a.estado}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <div>{formatWhen(a.started_at)}</div>
                          <div className="text-xs text-slate-500">{tempoDesde(a.started_at)}</div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button type="button" variant="secondary" className="px-3 py-1.5 text-xs" onClick={() => abrirDetalhe(a.id)}>
                            Detalhe
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {detalhe && (
        <div
          className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          onClick={() => setDetalhe(null)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setDetalhe(null)
          }}
        >
          <div
            className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-950"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{detalhe.titulo}</h2>
                <p className="text-sm text-slate-500">
                  {detalhe.cliente_nome} · {detalhe.cliente_slug} · {detalhe.codigo_sinal}
                </p>
              </div>
              <Button type="button" variant="secondary" className="px-3 py-1.5 text-xs" onClick={() => setDetalhe(null)}>
                Fechar
              </Button>
            </div>
            <div className="mb-3 flex flex-wrap gap-2">
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeSeveridade(detalhe.severidade)}`}>
                {detalhe.severidade}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeEstado(detalhe.estado)}`}>
                {detalhe.estado}
              </span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800">{detalhe.modulo}</span>
            </div>
            <dl className="mb-4 grid grid-cols-2 gap-2 text-sm">
              <div>
                <dt className="text-slate-500">Início</dt>
                <dd>{formatWhen(detalhe.started_at)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Última evidência</dt>
                <dd>{formatWhen(detalhe.last_seen_at)}</dd>
              </div>
            </dl>
            {detalhe.evidencia && (
              <pre className="mb-4 overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">
                {JSON.stringify(detalhe.evidencia, null, 2)}
              </pre>
            )}
            <h3 className="mb-2 text-sm font-medium text-slate-800 dark:text-slate-100">Histórico</h3>
            <ul className="mb-4 space-y-2 text-sm">
              {(detalhe.eventos || []).map((ev) => (
                <li key={ev.id} className="rounded-lg border border-slate-200 p-2 dark:border-slate-700">
                  <div className="font-medium">{ev.tipo}</div>
                  <div className="text-slate-600 dark:text-slate-300">{ev.mensagem}</div>
                  <div className="text-xs text-slate-500">{formatWhen(ev.created_at)}</div>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2">
              {detalhe.estado === 'ativo' && (
                <Button type="button" onClick={() => mitigar(detalhe.id)}>
                  Marcar mitigado
                </Button>
              )}
              <Link
                to={`/saas/licencas/${detalhe.cliente_saas_id}`}
                className="inline-flex items-center rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium text-slate-800 dark:border-slate-600 dark:text-slate-100"
              >
                Abrir licença
              </Link>
            </div>
          </div>
        </div>
      )}
    </ConfigListPageShell>
  )
}
