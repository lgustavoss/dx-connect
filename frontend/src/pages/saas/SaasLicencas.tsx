import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CabecalhoOrdenavel } from '../../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../../hooks/useOrdenacaoLista'
import { ApiError, saasClientes, saasPlanos, type SaasCatalogo, type SaasClientes } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Select'
import { ListaAcoesVerEditar } from '../../components/ui/ListaAcoesVerEditar'
import { useToast } from '../../components/ui/Toast'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../../components/ui/BarraBuscaPaginacao'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { SemPermissao } from '../SemPermissao'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import {
  STATUS_CLIENTE_SAAS,
  badgeClassStatusClienteSaaS,
  hrefAcessoCliente,
  labelStatusClienteSaaS,
  renovacaoAlerta,
} from '../../lib/saasControlPlane'

type Coluna = 'nome' | 'slug' | 'status' | 'data_renovacao'

const APROVACAO_OPTS = [
  { value: 'pendente', label: 'Aprovação pendente' },
  { value: 'aprovado', label: 'Aprovado' },
  { value: 'rejeitado', label: 'Rejeitado' },
]

const PROV_OPTS = [
  { value: 'pendente', label: 'Pendente' },
  { value: 'aguardando_ops', label: 'Aguardando ops' },
  { value: 'em_progresso', label: 'Em progresso' },
  { value: 'sucesso', label: 'Sucesso' },
  { value: 'falha', label: 'Falha' },
]

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = iso.slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return iso
  return `${day}/${m}/${y}`
}

function boolParam(v: string | null): boolean {
  return v === '1' || v === 'true'
}

export function SaasLicencas({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<Coluna>()
  const [list, setList] = useState<SaasClientes.Cliente[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [planos, setPlanos] = useState<SaasCatalogo.Plano[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [resumo, setResumo] = useState<SaasClientes.Resumo | null>(null)

  const statusFiltro = searchParams.get('status') || ''
  const planoFiltro = searchParams.get('plano_id') || ''
  const aprovacaoFiltro = searchParams.get('aprovacao_status') || ''
  const provStatusFiltro = searchParams.get('provisionamento_status') || ''
  const provFila = boolParam(searchParams.get('provisionamento_fila'))
  const vencendo = boolParam(searchParams.get('vencendo'))
  const vencidas = boolParam(searchParams.get('vencidas'))

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

  function aplicarAtalhoResumo(kind: 'renovacao' | 'provisionamento' | 'aprovacoes') {
    if (kind === 'renovacao') {
      patchFiltros({
        vencendo: '1',
        vencidas: null,
        aprovacao_status: null,
        provisionamento_fila: null,
        provisionamento_status: null,
        status: null,
        plano_id: null,
      })
      return
    }
    if (kind === 'aprovacoes') {
      patchFiltros({
        aprovacao_status: 'pendente',
        vencendo: null,
        vencidas: null,
        provisionamento_fila: null,
        provisionamento_status: null,
      })
      return
    }
    // provisionamento
    const preferFalha = (resumo?.provisionamento_falha ?? 0) > 0
    patchFiltros({
      provisionamento_fila: preferFalha ? null : '1',
      provisionamento_status: preferFalha ? 'falha' : null,
      vencendo: null,
      vencidas: null,
      aprovacao_status: null,
    })
  }

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [
    debouncedBusca,
    statusFiltro,
    planoFiltro,
    aprovacaoFiltro,
    provStatusFiltro,
    provFila,
    vencendo,
    vencidas,
    ordenarPor,
    ordem,
  ])

  useEffect(() => {
    saasPlanos
      .list()
      .then(setPlanos)
      .catch(() => setPlanos([]))
  }, [])

  const loadResumo = useCallback(() => {
    saasClientes
      .resumo()
      .then(setResumo)
      .catch(() => setResumo(null))
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasClientes
      .list({
        busca: debouncedBusca || undefined,
        status: statusFiltro || undefined,
        plano_id: planoFiltro ? Number(planoFiltro) : undefined,
        aprovacao_status: aprovacaoFiltro || undefined,
        provisionamento_status: provFila ? undefined : provStatusFiltro || undefined,
        provisionamento_fila: provFila || undefined,
        vencendo: vencendo || undefined,
        vencidas: vencidas || undefined,
        ...sortParams,
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
          setList([])
          setTotal(0)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          setList([])
          setTotal(0)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos a lista de licenças.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [
    aprovacaoFiltro,
    debouncedBusca,
    page,
    planoFiltro,
    provFila,
    provStatusFiltro,
    sortParams,
    statusFiltro,
    toast,
    vencendo,
    vencidas,
  ])

  useEffect(() => {
    load()
    loadResumo()
  }, [load, loadResumo])

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel de licenças não disponível nesta instância."
        detail="Este módulo só existe na instância comercial DeskRudder (control-plane)."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para gerir licenças SaaS."
      detail="Peça a um administrador acesso ao painel comercial."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Licenças SaaS"
      actions={<Button onClick={() => navigate('/saas/licencas/novo')}>Nova licença</Button>}
    >
      {resumo ? (
        <div className="mb-4 grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-[repeat(5,minmax(0,1fr))]">
          <ResumoCard
            label="Clientes"
            value={String(resumo.clientes_total)}
            hint={`${resumo.por_status.ativo ?? 0} ativos · ${resumo.por_status.trial ?? 0} trial`}
          />
          <ResumoCard
            label="Renovação"
            value={String(resumo.vencendo_em_breve)}
            hint={`${resumo.vencidas_ativas} vencida(s) · ${resumo.janela_renovacao_dias}d`}
            tone={resumo.vencidas_ativas > 0 || resumo.vencendo_em_breve > 0 ? 'warn' : undefined}
            onClick={() => aplicarAtalhoResumo('renovacao')}
          />
          <ResumoCard
            label="Provisionamento"
            value={String(resumo.provisionamento_pendente)}
            hint={`${resumo.provisionamento_falha} falha(s) na fila`}
            tone={resumo.provisionamento_falha > 0 || resumo.provisionamento_pendente > 0 ? 'warn' : undefined}
            onClick={() => aplicarAtalhoResumo('provisionamento')}
          />
          <ResumoCard
            label="Aprovações"
            value={String(resumo.aprovacoes_pendentes ?? 0)}
            hint="go-live pendente"
            tone={(resumo.aprovacoes_pendentes ?? 0) > 0 ? 'warn' : undefined}
            onClick={() => aplicarAtalhoResumo('aprovacoes')}
          />
          <ResumoCard
            label="Leads"
            value={String(resumo.leads_novos)}
            hint={`${resumo.leads_em_atendimento} em atendimento`}
            linkTo="/saas/leads"
          />
        </div>
      ) : null}
      {resumo?.instancias && resumo.instancias.length > 0 ? (
        <Card title="Instâncias (porta / stack)" className="mb-4">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-700">
                  <th className="py-2 pr-3 font-medium">Slug</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                  <th className="py-2 pr-3 font-medium">Porta</th>
                  <th className="py-2 pr-3 font-medium">Stack</th>
                  <th className="py-2 pr-3 font-medium">Provisionamento</th>
                  <th className="py-2 font-medium">Acesso</th>
                </tr>
              </thead>
              <tbody>
                {resumo.instancias.map((inst) => {
                  const acesso = hrefAcessoCliente({
                    instanciaUrl: inst.instancia_url,
                    slug: inst.slug,
                    apiPort: inst.api_port,
                    baseDomain: resumo.base_dominio_provisionamento,
                  })
                  return (
                    <tr
                      key={inst.id}
                      className="border-b border-slate-100 dark:border-slate-800"
                    >
                      <td className="py-2 pr-3">
                        <Link
                          to={`/saas/licencas/${inst.id}`}
                          className="font-medium text-sky-600 hover:underline dark:text-sky-400"
                        >
                          {inst.slug}
                        </Link>
                        <span className="ml-2 text-slate-500">{inst.nome}</span>
                      </td>
                      <td className="py-2 pr-3">{labelStatusClienteSaaS(inst.status)}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{inst.api_port ?? '—'}</td>
                      <td className="py-2 pr-3">{inst.stack_status || '—'}</td>
                      <td className="py-2 pr-3">{inst.provisionamento_status || '—'}</td>
                      <td className="py-2">
                        {acesso ? (
                          <a
                            href={acesso.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sky-600 hover:underline dark:text-sky-400"
                          >
                            Abrir
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por nome, slug ou e-mail…"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
        />
        <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
          <Select
            label="Status"
            labelStyle="overline"
            className="min-w-0"
            aria-label="Filtrar por status"
            value={statusFiltro}
            onChange={(v) => patchFiltros({ status: String(v) || null })}
            options={STATUS_CLIENTE_SAAS.map((s) => ({ value: s.value, label: s.label }))}
            includeEmpty
            emptyLabel="Todos"
            placeholder="Todos"
            disabled={loading}
          />
          <Select
            label="Plano"
            labelStyle="overline"
            className="min-w-0"
            aria-label="Filtrar por plano"
            value={planoFiltro}
            onChange={(v) => patchFiltros({ plano_id: v === '' ? null : String(v) })}
            options={planos.map((p) => ({ value: String(p.id), label: p.nome }))}
            includeEmpty
            emptyLabel="Todos"
            placeholder="Todos"
            disabled={loading}
          />
          <Select
            label="Aprovação"
            labelStyle="overline"
            className="min-w-0"
            aria-label="Filtrar por aprovação"
            value={aprovacaoFiltro}
            onChange={(v) => patchFiltros({ aprovacao_status: String(v) || null })}
            options={APROVACAO_OPTS}
            includeEmpty
            emptyLabel="Qualquer"
            placeholder="Qualquer"
            disabled={loading}
          />
          <Select
            label="Provisionamento"
            labelStyle="overline"
            className="min-w-0"
            aria-label="Filtrar por provisionamento"
            value={provFila ? 'fila' : provStatusFiltro}
            onChange={(v) => {
              const s = String(v)
              if (s === 'fila') {
                patchFiltros({ provisionamento_fila: '1', provisionamento_status: null })
              } else if (!s) {
                patchFiltros({ provisionamento_fila: null, provisionamento_status: null })
              } else {
                patchFiltros({ provisionamento_fila: null, provisionamento_status: s })
              }
            }}
            options={[{ value: 'fila', label: 'Em fila / falha' }, ...PROV_OPTS]}
            includeEmpty
            emptyLabel="Qualquer"
            placeholder="Qualquer"
            disabled={loading}
          />
          {(statusFiltro ||
            planoFiltro ||
            aprovacaoFiltro ||
            provStatusFiltro ||
            provFila ||
            vencendo ||
            vencidas) && (
            <div className="flex items-end sm:col-span-2 lg:col-span-4 xl:col-span-1">
              <Button
                variant="secondary"
                className="w-full xl:w-auto"
                disabled={loading}
                onClick={() =>
                  patchFiltros({
                    status: null,
                    plano_id: null,
                    aprovacao_status: null,
                    provisionamento_status: null,
                    provisionamento_fila: null,
                    vencendo: null,
                    vencidas: null,
                  })
                }
              >
                Limpar filtros
              </Button>
            </div>
          )}
        </div>
        {vencendo || vencidas ? (
          <p className="mb-3 text-xs text-amber-800 dark:text-amber-200">
            Filtro ativo:{' '}
            {vencendo ? 'renovação na janela de alerta' : null}
            {vencendo && vencidas ? ' · ' : null}
            {vencidas ? 'renovação vencida' : null}
          </p>
        ) : null}
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhuma licença cadastrada.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel
                    coluna="nome"
                    rotulo="Cliente"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <CabecalhoOrdenavel
                    coluna="slug"
                    rotulo="Slug"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Plano
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Valor/mês
                  </th>
                  <CabecalhoOrdenavel
                    coluna="status"
                    rotulo="Status"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <CabecalhoOrdenavel
                    coluna="data_renovacao"
                    rotulo="Renovação"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                  />
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Instância
                  </th>
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((item) => {
                  const acesso = hrefAcessoCliente({
                    instanciaUrl: item.instancia_url,
                    slug: item.slug,
                    apiPort: item.api_port,
                    baseDomain: resumo?.base_dominio_provisionamento,
                  })
                  return (
                    <tr
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => navigate(`/saas/licencas/${item.id}`)}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' || ev.key === ' ') {
                          ev.preventDefault()
                          navigate(`/saas/licencas/${item.id}`)
                        }
                      }}
                      className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/50 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                    >
                      <td className="px-4 py-3.5 sm:px-6">
                        <span className="font-medium text-slate-800 dark:text-slate-100">{item.nome}</span>
                        {item.aprovacao_status === 'pendente' ? (
                          <span className="mt-0.5 block text-xs font-medium text-amber-700 dark:text-amber-300">
                            Aprovação pendente
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-slate-600 sm:px-6 dark:text-slate-300">
                        {item.slug}
                      </td>
                      <td className="px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300">
                        {item.plano || '—'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 tabular-nums text-slate-700 sm:px-6 dark:text-slate-200">
                        {item.preco_mensal_efetivo != null
                          ? `R$ ${Number(item.preco_mensal_efetivo).toLocaleString('pt-BR', {
                              minimumFractionDigits: 0,
                              maximumFractionDigits: 2,
                            })}`
                          : '—'}
                        {item.preco_mensal_negociado != null ? (
                          <span className="mt-0.5 block text-[11px] text-amber-700 dark:text-amber-300">
                            Negociado
                          </span>
                        ) : item.preco_mensal_estimado != null ? (
                          <span className="mt-0.5 block text-[11px] text-slate-400">Catálogo</span>
                        ) : null}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 sm:px-6">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClassStatusClienteSaaS(item.status)}`}
                        >
                          {labelStatusClienteSaaS(item.status)}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300">
                        <span>{formatDate(item.data_renovacao)}</span>
                        {(() => {
                          const alerta = renovacaoAlerta(item.dias_para_renovacao)
                          if (!alerta || alerta === 'ok') return null
                          return (
                            <span
                              className={`mt-1 block text-xs font-medium ${
                                alerta === 'vencido'
                                  ? 'text-amber-700 dark:text-amber-300'
                                  : 'text-sky-700 dark:text-sky-300'
                              }`}
                            >
                              {alerta === 'vencido'
                                ? `Vencida há ${Math.abs(item.dias_para_renovacao ?? 0)}d`
                                : `Vence em ${item.dias_para_renovacao}d`}
                            </span>
                          )
                        })()}
                      </td>
                      <td className="px-4 py-3.5 sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                        {acesso ? (
                          <a
                            href={acesso.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={
                              acesso.modo === 'local'
                                ? 'Local: health na porta API (DNS público não resolve)'
                                : acesso.label
                            }
                            className="text-sky-600 hover:underline dark:text-sky-400"
                          >
                            Abrir
                          </a>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                        <ListaAcoesVerEditar
                          onVer={() => navigate(`/saas/licencas/${item.id}`)}
                          onEditar={() => navigate(`/saas/licencas/${item.id}/editar`)}
                          verLabel="Visualizar licença"
                          editarLabel="Editar licença"
                        />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </ConfigListPageShell>
  )
}

function ResumoCard({
  label,
  value,
  hint,
  tone,
  linkTo,
  onClick,
}: {
  label: string
  value: string
  hint: string
  tone?: 'warn'
  linkTo?: string
  onClick?: () => void
}) {
  const body = (
    <div
      className={`flex h-full min-h-[6.75rem] w-full min-w-0 flex-col rounded-2xl border px-4 py-3 ${
        tone === 'warn'
          ? 'border-amber-200 bg-amber-50/80 dark:border-amber-800/40 dark:bg-amber-950/30'
          : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/40'
      } ${onClick || linkTo ? 'transition hover:ring-2 hover:ring-sky-400/40' : ''}`}
    >
      <p className="shrink-0 truncate text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-1 shrink-0 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">{value}</p>
      <p className="mt-auto pt-2 text-xs leading-snug text-slate-500 line-clamp-2 dark:text-slate-400">{hint}</p>
    </div>
  )
  if (linkTo) {
    return (
      <Link to={linkTo} className="block h-full w-full min-w-0">
        {body}
      </Link>
    )
  }
  if (onClick) {
    return (
      <button type="button" className="block h-full w-full min-w-0 text-left" onClick={onClick}>
        {body}
      </button>
    )
  }
  return <div className="h-full w-full min-w-0">{body}</div>
}
