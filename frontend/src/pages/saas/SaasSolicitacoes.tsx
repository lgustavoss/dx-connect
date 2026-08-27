import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, saasSolicitacoes, type SaasSolicitacoesProduto } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../../components/ui/BarraBuscaPaginacao'
import { Card } from '../../components/ui/Card'
import { useToast } from '../../components/ui/Toast'
import {
  classesBadgeStatusSolicitacao,
  classesBadgeTipoSolicitacao,
  rotuloStatusSolicitacao,
  rotuloTipoSolicitacao,
  SAAS_SOLICITACAO_FASES,
} from '../../lib/saasSolicitacoes'
import { SemPermissao } from '../SemPermissao'

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function Chip({
  active,
  onClick,
  children,
  count,
  tone,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
  count?: number
  tone?: 'sky' | 'rose' | 'default'
}) {
  const toneActive =
    tone === 'sky'
      ? 'border-sky-500 bg-sky-50 text-sky-900 dark:border-sky-400 dark:bg-sky-950/50 dark:text-sky-100'
      : tone === 'rose'
        ? 'border-rose-500 bg-rose-50 text-rose-900 dark:border-rose-400 dark:bg-rose-950/50 dark:text-rose-100'
        : 'border-cyan-500 bg-cyan-50 text-cyan-950 dark:border-cyan-400 dark:bg-cyan-950/40 dark:text-cyan-50'

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
        active
          ? toneActive
          : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300 dark:hover:border-slate-600 dark:hover:bg-slate-800/60'
      }`}
    >
      {children}
      {count != null ? (
        <span
          className={`tabular-nums text-xs ${
            active ? 'opacity-80' : 'text-slate-400 dark:text-slate-500'
          }`}
        >
          {count}
        </span>
      ) : null}
    </button>
  )
}

export function SaasSolicitacoes() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const [list, setList] = useState<SaasSolicitacoesProduto.ListaItem[]>([])
  const [resumo, setResumo] = useState<SaasSolicitacoesProduto.Resumo | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)

  const tipoFiltro = searchParams.get('tipo') || ''
  const faseFiltro = searchParams.get('fase') || ''

  function patchFiltros(next: Record<string, string | null>) {
    setSearchParams(
      (prev) => {
        const p = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(next)) {
          if (v == null || v === '') p.delete(k)
          else p.set(k, v)
        }
        return p
      },
      { replace: true },
    )
    setPage(1)
  }

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca])

  const loadResumo = useCallback(() => {
    saasSolicitacoes
      .resumo()
      .then(setResumo)
      .catch(() => setResumo(null))
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasSolicitacoes
      .list({
        busca: debouncedBusca || undefined,
        tipo: tipoFiltro || undefined,
        fase: faseFiltro || undefined,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
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
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos as solicitações.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, page, tipoFiltro, faseFiltro, toast])

  useEffect(() => {
    load()
    loadResumo()
  }, [load, loadResumo])

  if (indisponivel) {
    return (
      <SemPermissao
        title="Fila de sugestões não disponível nesta instância."
        detail="Este módulo só existe na instância comercial DeskRudder."
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
          title="Você não tem permissão para ver a fila de sugestões."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      }
      title="Sugestões e erros"
      subtitle="Pedidos das instâncias. Filtre por tipo e fase para ver o que aguarda, o que está em desenvolvimento e o que já fechou."
    >
      <div className="space-y-4">
        <Card>
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Tipo
              </p>
              <div className="flex flex-wrap gap-2">
                <Chip
                  active={!tipoFiltro}
                  count={resumo?.total}
                  onClick={() => patchFiltros({ tipo: null })}
                >
                  Todos
                </Chip>
                <Chip
                  active={tipoFiltro === 'sugestao'}
                  count={resumo?.sugestoes}
                  tone="sky"
                  onClick={() =>
                    patchFiltros({ tipo: tipoFiltro === 'sugestao' ? null : 'sugestao' })
                  }
                >
                  Sugestões
                </Chip>
                <Chip
                  active={tipoFiltro === 'problema'}
                  count={resumo?.problemas}
                  tone="rose"
                  onClick={() =>
                    patchFiltros({ tipo: tipoFiltro === 'problema' ? null : 'problema' })
                  }
                >
                  Erros
                </Chip>
              </div>
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Fase
              </p>
              <div className="flex flex-wrap gap-2">
                <Chip
                  active={!faseFiltro}
                  onClick={() => patchFiltros({ fase: null })}
                >
                  Todas
                </Chip>
                {SAAS_SOLICITACAO_FASES.map((f) => (
                  <Chip
                    key={f.value}
                    active={faseFiltro === f.value}
                    count={
                      f.value === 'aguardando'
                        ? resumo?.aguardando
                        : f.value === 'desenvolvimento'
                          ? resumo?.desenvolvimento
                          : resumo?.finalizadas
                    }
                    onClick={() =>
                      patchFiltros({ fase: faseFiltro === f.value ? null : f.value })
                    }
                  >
                    {f.label}
                  </Chip>
                ))}
              </div>
              {faseFiltro ? (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  {SAAS_SOLICITACAO_FASES.find((f) => f.value === faseFiltro)?.hint}
                </p>
              ) : null}
            </div>
          </div>
        </Card>

        <Card>
          <BarraBuscaPaginacao
            busca={busca}
            onBuscaChange={setBusca}
            placeholder="Buscar por protocolo, título, cliente, slug ou autor…"
            page={page}
            total={total}
            onPageChange={setPage}
            disabled={loading}
          />
          {loading ? (
            <div className="h-32 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ) : list.length === 0 ? (
            <p className="px-2 py-8 text-center text-sm text-slate-500 dark:text-slate-400">
              Nenhum pedido neste filtro.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                    <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">
                      Tipo
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">
                      Protocolo
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">
                      Cliente
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">
                      Título
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">
                      Status
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">
                      Quando
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {list.map((item) => (
                    <tr
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => navigate(`/saas/solicitacoes/${item.id}`)}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' || ev.key === ' ') {
                          ev.preventDefault()
                          navigate(`/saas/solicitacoes/${item.id}`)
                        }
                      }}
                      className={`cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/5 ${
                        item.tipo === 'problema'
                          ? 'border-l-2 border-l-rose-400/80'
                          : 'border-l-2 border-l-sky-400/60'
                      }`}
                    >
                      <td className="px-4 py-3 sm:px-6">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeTipoSolicitacao(item.tipo)}`}
                        >
                          {rotuloTipoSolicitacao(item.tipo)}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-sm text-cyan-800 dark:text-cyan-300 sm:px-6">
                        {item.protocolo || '—'}
                      </td>
                      <td className="px-4 py-3 sm:px-6">
                        <p className="font-medium text-slate-900 dark:text-slate-50">
                          {item.cliente_nome || item.instance_slug}
                        </p>
                        <p className="font-mono text-xs text-slate-500">{item.instance_slug}</p>
                      </td>
                      <td className="px-4 py-3 sm:px-6">
                        <p className="font-medium text-slate-800 dark:text-slate-100">{item.titulo}</p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {item.autor_nome || '—'}
                          {(item.peso_clientes || 1) > 1
                            ? ` · ${item.peso_clientes} clientes`
                            : ''}
                          {item.versao_contexto ? ` · v${item.versao_contexto}` : ''}
                        </p>
                      </td>
                      <td className="px-4 py-3 sm:px-6">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeStatusSolicitacao(item.status)}`}
                        >
                          {item.status_rotulo || rotuloStatusSolicitacao(item.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-slate-500 sm:px-6">
                        {formatWhen(item.created_at_origem || item.ingested_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </ConfigListPageShell>
  )
}
