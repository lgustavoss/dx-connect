import { useState, useEffect, useMemo, useId, useCallback } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  tickets,
  statusTicket,
  empresas,
  setores,
  atendentes,
  ApiError,
  type Tickets,
  type StatusTicket,
  type Empresas,
  type Setores,
  type Atendentes,
} from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Button } from '../components/ui/Button'
import { Select } from '../components/ui/Select'
import { PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { useToast } from '../components/ui/Toast'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { useAuth } from '../contexts/AuthContext'
import { useAlertaFilaSemResponsavel } from '../hooks/useAlertaFilaSemResponsavel'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { exibirProtocolo } from '../lib/exibirProtocolo'
import { rotuloPrioridade, classeBadgePrioridade } from '../lib/ticketPrioridade'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'

type ColunaOrdenacao =
  | 'protocolo'
  | 'rede'
  | 'empresa'
  | 'setor'
  | 'assunto'
  | 'status'
  | 'responsavel'
  | 'fechado_em'

const searchIcon = (
  <svg className="size-4 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
)

function formatarTempoNaFila(filaDesdeAt: string | undefined | null): string {
  if (!filaDesdeAt) return '—'
  const min = Math.max(0, Math.floor((Date.now() - new Date(filaDesdeAt).getTime()) / 60000))
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m > 0 ? `${h}h ${m}min` : `${h}h`
}

export function Tickets() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const { isAdmin, user } = useAuth()
  useAlertaFilaSemResponsavel(Boolean(user))
  const [forbidden, setForbidden] = useState(false)

  const situacao = useMemo<'abertos' | 'fechados'>(() => {
    const s = searchParams.get('situacao')
    return s === 'fechados' ? 'fechados' : 'abertos'
  }, [searchParams])

  const [list, setList] = useState<Tickets.Ticket[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [filtroStatus, setFiltroStatus] = useState<number | ''>('')
  const [filtroEmpresa, setFiltroEmpresa] = useState<number | ''>('')
  const [filtroSetor, setFiltroSetor] = useState<number | ''>('')
  const [statusList, setStatusList] = useState<StatusTicket.Status[]>([])
  const [empresasOpt, setEmpresasOpt] = useState<Empresas.EmpresaListaItem[]>([])
  const [setoresOpt, setSetoresOpt] = useState<Setores.Setor[]>([])
  const [atendentesOpt, setAtendentesOpt] = useState<Atendentes.Atendente[]>([])
  /** '' | 'sem_responsavel' | 'com_responsavel' | 'meus */
  const [filtroFila, setFiltroFila] = useState<'' | 'sem_responsavel' | 'com_responsavel' | 'meus'>(() => {
    const sr = searchParams.get('sem_responsavel')
    return sr === '1' || sr === 'true' ? 'sem_responsavel' : ''
  })
  const [filtroAtendente, setFiltroAtendente] = useState<number | ''>('')
  const [maisFiltrosAberto, setMaisFiltrosAberto] = useState(false)
  const painelFiltrosId = useId()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaOrdenacao>()

  const resetarPagina = useCallback(() => setPage(1), [])

  /** Setores vêm filtrados pelo backend para atendentes; não recortar por `user.setor_ids` no cliente. */
  const setoresFiltro = useMemo(() => {
    const ativos = setoresOpt.filter((s) => s.ativo)
    return [...ativos].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [setoresOpt])

  const empresasOrdenadas = useMemo(
    () => [...empresasOpt].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [empresasOpt],
  )

  const opcoesEmpresaFiltro = useMemo(
    () => empresasOrdenadas.map((e) => ({ value: e.id, label: e.nome })),
    [empresasOrdenadas],
  )
  const opcoesSetorFiltro = useMemo(
    () => setoresFiltro.map((s) => ({ value: s.id, label: s.nome })),
    [setoresFiltro],
  )
  const opcoesStatusFiltro = useMemo(
    () => statusList.map((s) => ({ value: s.id, label: s.nome })),
    [statusList],
  )

  const opcoesAtendenteFiltro = useMemo(() => {
    const ativos = atendentesOpt.filter((a) => a.ativo)
    return [...ativos].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')).map((a) => ({ value: a.id, label: a.nome }))
  }, [atendentesOpt])

  const mostrarColunasFila = situacao === 'abertos' && filtroFila === 'sem_responsavel'

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE_PADRAO))
  const inicio = total === 0 ? 0 : (page - 1) * PAGE_SIZE_PADRAO + 1
  const fim = Math.min(page * PAGE_SIZE_PADRAO, total)

  const temFiltrosAtivos =
    busca.trim() !== '' ||
    filtroEmpresa !== '' ||
    filtroSetor !== '' ||
    (situacao === 'abertos' && filtroStatus !== '') ||
    filtroFila !== '' ||
    (isAdmin && filtroAtendente !== '')

  const qtdFiltrosRefinamento =
    (filtroEmpresa !== '' ? 1 : 0) +
    (filtroSetor !== '' ? 1 : 0) +
    (situacao === 'abertos' && filtroStatus !== '' ? 1 : 0) +
    (isAdmin && filtroAtendente !== '' ? 1 : 0)

  useEffect(() => {
    if (situacao !== 'fechados') return
    if (filtroFila !== '') setFiltroFila('')
  }, [situacao, filtroFila])

  useEffect(() => {
    if (situacao !== 'fechados') return
    if (filtroStatus !== '') setFiltroStatus('')
  }, [situacao, filtroStatus])

  useEffect(() => {
    const sr = searchParams.get('sem_responsavel')
    if (sr === '1' || sr === 'true') {
      setFiltroFila('sem_responsavel')
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.delete('sem_responsavel')
          return next
        },
        { replace: true },
      )
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    coletarTodasPaginas<StatusTicket.Status>((o, l) =>
      statusTicket.list({ incluir_inativos: false, offset: o, limit: l }),
    ).then(setStatusList)
    coletarTodasPaginas<Empresas.EmpresaListaItem>((o, l) => empresas.list({ offset: o, limit: l })).then(
      setEmpresasOpt,
    )
    coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: true, offset: o, limit: l }),
    ).then(setSetoresOpt)
  }, [])

  useEffect(() => {
    if (!isAdmin) {
      setAtendentesOpt([])
      setFiltroAtendente('')
      resetarPagina()
      return
    }
    coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
      atendentes.list({ incluir_inativos: false, offset: o, limit: l }),
    ).then(setAtendentesOpt)
  }, [isAdmin, resetarPagina])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    if (filtroSetor !== '' && !setoresFiltro.some((s) => s.id === filtroSetor)) {
      setFiltroSetor('')
    }
  }, [setoresFiltro, filtroSetor])

  useEffect(() => {
    if (qtdFiltrosRefinamento > 0) setMaisFiltrosAberto(true)
  }, [qtdFiltrosRefinamento])

  useEffect(() => {
    setLoading(true)
    setForbidden(false)
    tickets
      .list({
        situacao,
        busca: debouncedBusca || undefined,
        status_id: situacao === 'abertos' && filtroStatus !== '' ? Number(filtroStatus) : undefined,
        empresa_id: filtroEmpresa !== '' ? Number(filtroEmpresa) : undefined,
        setor_id: filtroSetor !== '' ? Number(filtroSetor) : undefined,
        sem_responsavel: filtroFila === 'sem_responsavel' ? true : undefined,
        com_responsavel: filtroFila === 'com_responsavel' ? true : undefined,
        meus: filtroFila === 'meus' ? true : undefined,
        atendente_id:
          isAdmin &&
          filtroFila !== 'sem_responsavel' &&
          filtroFila !== 'meus' &&
          filtroAtendente !== ''
            ? Number(filtroAtendente)
            : undefined,
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
          toast.showWarning(err.message || 'Você não tem permissão para ver estes tickets.')
          setList([])
          setTotal(0)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos os tickets solicitados.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [
    page,
    situacao,
    debouncedBusca,
    filtroStatus,
    filtroEmpresa,
    filtroSetor,
    filtroFila,
    filtroAtendente,
    isAdmin,
    ordenarPor,
    ordem,
    sortParams,
    toast,
  ])

  if (forbidden) {
    return (
      <PageContainer>
        <SemPermissao
          title="Você não tem permissão para listar tickets."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil e seus vínculos de setor."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      </PageContainer>
    )
  }

  function limparFiltros() {
    setBusca('')
    setDebouncedBusca('')
    setFiltroEmpresa('')
    setFiltroSetor('')
    setFiltroStatus('')
    setFiltroFila('')
    setFiltroAtendente('')
    setPage(1)
  }

  return (
    <PageContainer spacing="relaxed">
      <PageHeader
        title="Tickets"
        subtitle="Acompanhe e filtre as demandas do suporte."
        actions={
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
            <div
              className="inline-flex w-full flex-wrap rounded-2xl bg-slate-100/90 p-1 ring-1 ring-slate-200/60 dark:bg-slate-800/60 dark:ring-slate-700/80 sm:w-auto"
              role="group"
              aria-label="Filtrar tickets por situação"
            >
              {(
                [
                  { id: 'abertos' as const, label: 'Abertos' },
                  { id: 'fechados' as const, label: 'Finalizados' },
                ] as const
              ).map(({ id, label }) => {
                const ativo = situacao === id
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      setPage(1)
                      setSearchParams(
                        (prev) => {
                          const next = new URLSearchParams(prev)
                          if (id === 'abertos') next.delete('situacao')
                          else next.set('situacao', 'fechados')
                          return next
                        },
                        { replace: true },
                      )
                    }}
                    className={`min-h-[2.25rem] flex-1 rounded-xl px-3 py-2 text-center text-xs font-medium transition-all duration-200 sm:flex-none sm:px-4 sm:text-sm ${
                      ativo
                        ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/80 dark:bg-slate-700 dark:text-slate-50 dark:ring-slate-600/50'
                        : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            <Link to="/tickets/novo">
              <Button className="w-full sm:w-auto">Novo ticket</Button>
            </Link>
          </div>
        }
      />

      <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900/40">
        <div className="border-b border-slate-100/90 px-4 py-5 sm:px-6 dark:border-slate-800">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-3">
            <div className="relative min-w-0 flex-1">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">{searchIcon}</span>
              <input
                type="search"
                value={busca}
                onChange={(e) => {
                  setBusca(e.target.value)
                  resetarPagina()
                }}
                placeholder="Buscar por protocolo (ex.: #T202605-0001), assunto ou empresa…"
                disabled={loading}
                className="w-full rounded-xl border-0 bg-slate-50 py-2.5 pl-10 pr-4 text-sm text-slate-900 shadow-inner ring-1 ring-slate-200/80 transition-shadow placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-400/25 dark:bg-slate-900/60 dark:text-slate-100 dark:ring-slate-700 dark:placeholder:text-slate-500 dark:focus:bg-slate-900"
                aria-label="Buscar tickets"
              />
            </div>
            <button
              type="button"
              id={`${painelFiltrosId}-toggle`}
              aria-expanded={maisFiltrosAberto}
              aria-controls={painelFiltrosId}
              onClick={() => setMaisFiltrosAberto((o) => !o)}
              className="inline-flex w-full shrink-0 items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200 dark:hover:bg-slate-800 sm:w-auto sm:justify-start"
            >
              <span className="flex items-center gap-2">
                <span
                  className={`inline-flex size-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition-transform dark:bg-slate-800 dark:text-slate-400 ${
                    maisFiltrosAberto ? 'rotate-180' : ''
                  }`}
                  aria-hidden
                >
                  <svg className="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
                Mais filtros
              </span>
              {qtdFiltrosRefinamento > 0 && (
                <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold tabular-nums text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                  {qtdFiltrosRefinamento}
                </span>
              )}
            </button>
            {temFiltrosAtivos && (
              <button
                type="button"
                onClick={limparFiltros}
                className="w-full shrink-0 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 sm:w-auto"
              >
                Limpar tudo
              </button>
            )}
          </div>

          {situacao === 'abertos' && (
            <div className="mt-5">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400 dark:text-slate-500">
              Fila
            </p>
            <div
              className="inline-flex w-full max-w-lg flex-wrap rounded-2xl bg-slate-100/90 p-1 ring-1 ring-slate-200/60 dark:bg-slate-800/60 dark:ring-slate-700/80 sm:w-auto"
              role="group"
              aria-label="Filtrar por fila de atendimento"
            >
              {(
                [
                  { id: '' as const, label: 'Todos' },
                  { id: 'sem_responsavel' as const, label: 'Na fila' },
                  { id: 'com_responsavel' as const, label: 'Em atendimento' },
                  { id: 'meus' as const, label: 'Meus' },
                ] as const
              ).map(({ id, label }) => {
                const ativo = filtroFila === id
                return (
                  <button
                    key={id || 'todos'}
                    type="button"
                    onClick={() => {
                      setFiltroFila(id)
                      if (id !== '') setFiltroAtendente('')
                      resetarPagina()
                    }}
                    className={`min-h-[2.25rem] flex-1 rounded-xl px-3 py-2 text-center text-xs font-medium transition-all duration-200 sm:flex-none sm:px-4 sm:text-sm ${
                      ativo
                        ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/80 dark:bg-slate-700 dark:text-slate-50 dark:ring-slate-600/50'
                        : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            <p className="mt-2 max-w-xl text-xs text-slate-500 dark:text-slate-400">
              <span className="font-medium text-slate-600 dark:text-slate-300">Na fila</span> — sem responsável.{' '}
              <span className="font-medium text-slate-600 dark:text-slate-300">Em atendimento</span> — já com responsável atribuído.
              {isAdmin && ' Use «Mais filtros» para filtrar por atendente da equipe.'}
            </p>
            </div>
          )}

          {maisFiltrosAberto && (
            <div
              id={painelFiltrosId}
              role="region"
              aria-labelledby={`${painelFiltrosId}-toggle`}
              className="mt-6 grid gap-4 border-t border-slate-200/70 pt-5 dark:border-slate-800 sm:grid-cols-2 lg:grid-cols-3"
            >
              <div className="min-w-0 sm:col-span-2 lg:col-span-1">
                <Select
                  label="Empresa"
                  labelStyle="overline"
                  className="min-w-0"
                  value={filtroEmpresa}
                  onChange={(v) => {
                    setFiltroEmpresa(v === '' ? '' : Number(v))
                    resetarPagina()
                  }}
                  options={opcoesEmpresaFiltro}
                  includeEmpty
                  emptyLabel="Todas"
                  placeholder="Todas"
                />
                {!isAdmin && empresasOpt.length === 0 && (
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                    Empresas no filtro aparecem só para redes que já tiveram ticket nos setores que você atende. Até lá,
                    use a busca por protocolo (inclui # e hífen), assunto ou empresa.
                  </p>
                )}
              </div>
              <Select
                label="Setor"
                labelStyle="overline"
                className="min-w-0"
                value={filtroSetor}
                onChange={(v) => {
                  setFiltroSetor(v === '' ? '' : Number(v))
                  resetarPagina()
                }}
                options={opcoesSetorFiltro}
                includeEmpty
                emptyLabel="Todos"
                placeholder="Todos"
              />
              {situacao === 'abertos' && (
                <Select
                  label="Status"
                  labelStyle="overline"
                  className="min-w-0"
                  value={filtroStatus}
                  onChange={(v) => {
                    setFiltroStatus(v === '' ? '' : Number(v))
                    resetarPagina()
                  }}
                  options={opcoesStatusFiltro}
                  includeEmpty
                  emptyLabel="Todos"
                  placeholder="Todos"
                />
              )}
              {isAdmin && (
                <Select
                  label="Responsável (equipe)"
                  labelStyle="overline"
                  className="min-w-0 sm:col-span-2 lg:col-span-1"
                  value={filtroAtendente}
                  onChange={(v) => {
                    setFiltroAtendente(v === '' ? '' : Number(v))
                    if (v !== '') setFiltroFila('')
                    resetarPagina()
                  }}
                  options={opcoesAtendenteFiltro}
                  includeEmpty
                  emptyLabel="Qualquer"
                  placeholder="Qualquer"
                  disabled={
                    situacao === 'abertos' ? filtroFila === 'sem_responsavel' || filtroFila === 'meus' : false
                  }
                />
              )}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 dark:border-slate-800 sm:px-6">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {loading ? (
              'Carregando…'
            ) : total === 0 ? (
              'Nenhum resultado'
            ) : (
              <>
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  {inicio}–{fim}
                </span>
                <span className="text-slate-400 dark:text-slate-500"> de </span>
                {total}
              </>
            )}
          </p>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={loading || page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100 disabled:pointer-events-none disabled:opacity-40 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              Anterior
            </button>
            <span className="min-w-[4rem] text-center text-xs tabular-nums text-slate-500 dark:text-slate-400">
              {page} / {totalPages}
            </span>
            <button
              type="button"
              disabled={loading || page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100 disabled:pointer-events-none disabled:opacity-40 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              Próxima
            </button>
          </div>
        </div>

        {loading ? (
          <div className="px-4 py-16 text-center text-sm text-slate-500 dark:text-slate-400 sm:px-6">Carregando lista…</div>
        ) : list.length === 0 ? (
          <div className="px-4 py-16 text-center text-sm text-slate-500 dark:text-slate-400 sm:px-6">
            Nenhum ticket encontrado.
            {temFiltrosAtivos && (
              <>
                {' '}
                <button
                  type="button"
                  onClick={limparFiltros}
                  className="font-medium text-slate-800 underline dark:text-slate-200"
                >
                  Limpar filtros
                </button>
              </>
            )}
          </div>
        ) : (
          <>
            {/* Mobile: cards (melhor leitura/toque) */}
            <div className="divide-y divide-slate-100 dark:divide-slate-800 sm:hidden">
              {list.map((t) => {
                const fechadoFmt = t.fechado_em ? new Date(t.fechado_em).toLocaleString('pt-BR') : null
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => navigate(`/tickets/${t.id}`)}
                    className="w-full px-4 py-4 text-left transition-colors hover:bg-slate-50/80 focus:outline-none focus-visible:bg-slate-100/80 dark:hover:bg-slate-800/40 dark:focus-visible:bg-slate-800/60"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p
                          className="min-w-0 truncate font-mono text-xs text-slate-500 dark:text-slate-400"
                          title={exibirProtocolo(t.protocolo)}
                        >
                          {exibirProtocolo(t.protocolo)}
                        </p>
                        <p className="mt-1 truncate font-semibold text-slate-900 dark:text-slate-100">
                          {t.empresa_nome ??
                            (t.empresa_nome ?? (t.empresa_id != null ? String(t.empresa_id) : '—'))}
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-sm text-slate-600 dark:text-slate-400">
                          {t.assunto}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        {situacao === 'fechados' ? (
                          <span className="inline-flex rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200">
                            Fechado
                          </span>
                        ) : (
                          <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                            {t.status_nome ?? t.status_id}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                      <span className="truncate">
                        <span className="font-medium text-slate-600 dark:text-slate-300">Setor:</span>{' '}
                        {t.setor_nome ?? String(t.setor_id)}
                      </span>
                      <span className="truncate">
                        <span className="font-medium text-slate-600 dark:text-slate-300">Resp.:</span>{' '}
                        {t.atendente_nome ?? 'Na fila'}
                      </span>
                      {mostrarColunasFila && (
                        <span className="truncate">
                          <span className="font-medium text-slate-600 dark:text-slate-300">Na fila há:</span>{' '}
                          {formatarTempoNaFila(t.fila_desde_at)}
                        </span>
                      )}
                      {mostrarColunasFila && t.distribuicao_modo_setor === 'auto_apos_timeout' && t.distribuicao_auto_em_minutos != null && (
                        <span className="inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                          Auto em {t.distribuicao_auto_em_minutos} min
                        </span>
                      )}
                      {situacao === 'abertos' && (
                        <span className="truncate">
                          <span className="font-medium text-slate-600 dark:text-slate-300">Prior.:</span>{' '}
                          {rotuloPrioridade(t.prioridade)}
                        </span>
                      )}
                      {situacao === 'fechados' && t.motivo_nome ? (
                        <span className="truncate">
                          <span className="font-medium text-slate-600 dark:text-slate-300">Motivo:</span>{' '}
                          {t.motivo_nome}
                        </span>
                      ) : null}
                      {situacao === 'fechados' && (
                        <span className="truncate">
                          <span className="font-medium text-slate-600 dark:text-slate-300">Fechado em:</span>{' '}
                          {fechadoFmt ?? '—'}
                        </span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>

            {/* Desktop/tablet: tabela */}
            <div className="hidden overflow-hidden sm:block">
              <table className="w-full table-auto text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel
                    coluna="protocolo"
                    rotulo="Protocolo"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      resetarPagina()
                      aoOrdenarColuna(c)
                    }}
                    className="whitespace-nowrap px-4 py-3 sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="rede"
                    rotulo="Rede"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      resetarPagina()
                      aoOrdenarColuna(c)
                    }}
                    className="hidden px-4 py-3 lg:table-cell sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="empresa"
                    rotulo="Empresa"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      resetarPagina()
                      aoOrdenarColuna(c)
                    }}
                    className="px-4 py-3 sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="setor"
                    rotulo="Setor"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      resetarPagina()
                      aoOrdenarColuna(c)
                    }}
                    className="hidden px-4 py-3 xl:table-cell sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="assunto"
                    rotulo="Assunto"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      resetarPagina()
                      aoOrdenarColuna(c)
                    }}
                    className="hidden px-4 py-3 md:table-cell sm:px-6"
                  />
                  {situacao === 'abertos' && (
                    <th className="hidden px-4 py-3 md:table-cell sm:px-6">Prioridade</th>
                  )}
                  {situacao === 'fechados' && (
                    <th className="hidden px-4 py-3 lg:table-cell sm:px-6">Motivo</th>
                  )}
                  {situacao === 'fechados' ? (
                    <CabecalhoOrdenavel
                      coluna="fechado_em"
                      rotulo="Fechado em"
                      ordenarPor={ordenarPor}
                      ordem={ordem}
                      aoOrdenar={(c) => {
                        resetarPagina()
                        aoOrdenarColuna(c)
                      }}
                      className="whitespace-nowrap px-4 py-3 sm:px-6"
                    />
                  ) : (
                    <CabecalhoOrdenavel
                      coluna="status"
                      rotulo="Status"
                      ordenarPor={ordenarPor}
                      ordem={ordem}
                      aoOrdenar={(c) => {
                        resetarPagina()
                        aoOrdenarColuna(c)
                      }}
                      className="whitespace-nowrap px-4 py-3 sm:px-6"
                    />
                  )}
                  <CabecalhoOrdenavel
                    coluna="responsavel"
                    rotulo="Responsável"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={(c) => {
                      resetarPagina()
                      aoOrdenarColuna(c)
                    }}
                    className="hidden px-4 py-3 lg:table-cell sm:px-6"
                  />
                  {mostrarColunasFila && (
                    <th className="hidden whitespace-nowrap px-4 py-3 lg:table-cell sm:px-6">Na fila há</th>
                  )}
                  {mostrarColunasFila && (
                    <th className="hidden whitespace-nowrap px-4 py-3 xl:table-cell sm:px-6">Distribuição</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((t) => (
                  <tr
                    key={t.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/tickets/${t.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        navigate(`/tickets/${t.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50/90 focus:outline-none focus-visible:bg-slate-100/80 dark:hover:bg-slate-800/50 dark:focus-visible:bg-slate-800/60"
                  >
                    <td
                      className="max-w-[10rem] truncate px-4 py-3.5 align-top font-mono text-sm text-slate-900 sm:max-w-[12rem] sm:px-6 dark:text-slate-100"
                      title={exibirProtocolo(t.protocolo)}
                    >
                      {exibirProtocolo(t.protocolo)}
                    </td>
                    <td
                      className="hidden px-4 py-3.5 align-top text-slate-600 lg:table-cell sm:px-6 dark:text-slate-400"
                      title={t.rede_nome}
                    >
                      <span className="block break-words whitespace-normal leading-snug">{t.rede_nome ?? '—'}</span>
                    </td>
                    <td
                      className="min-w-0 px-4 py-3.5 align-top sm:px-6"
                      title={t.empresa_nome ?? undefined}
                    >
                      <div className="min-w-0">
                        <p className="break-words whitespace-normal font-medium leading-snug text-slate-900 dark:text-slate-100">
                          {t.empresa_nome ??
                            (t.empresa_nome ?? (t.empresa_id != null ? String(t.empresa_id) : '—'))}
                        </p>
                        <p className="mt-0.5 break-words whitespace-normal text-xs leading-snug text-slate-500 dark:text-slate-400 md:hidden">
                          {t.assunto}
                        </p>
                      </div>
                    </td>
                    <td className="hidden px-4 py-3.5 align-top text-slate-600 xl:table-cell sm:px-6 dark:text-slate-400">
                      <span className="block break-words whitespace-normal leading-snug">{t.setor_nome ?? String(t.setor_id)}</span>
                    </td>
                    <td className="hidden px-4 py-3.5 align-top font-medium text-slate-900 md:table-cell sm:px-6 dark:text-slate-100" title={t.assunto}>
                      <span className="block break-words whitespace-normal leading-snug">{t.assunto}</span>
                    </td>
                    {situacao === 'abertos' && (
                      <td className="hidden px-4 py-3.5 align-top md:table-cell sm:px-6">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${classeBadgePrioridade(t.prioridade)}`}
                        >
                          {rotuloPrioridade(t.prioridade)}
                        </span>
                      </td>
                    )}
                    {situacao === 'fechados' && (
                      <td
                        className="hidden px-4 py-3.5 align-top text-slate-600 lg:table-cell sm:px-6 dark:text-slate-400"
                        title={t.motivo_outro_texto ?? undefined}
                      >
                        <span className="block break-words whitespace-normal leading-snug">
                          {t.motivo_nome ?? '—'}
                          {t.motivo_outro_texto ? (
                            <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                              {t.motivo_outro_texto}
                            </span>
                          ) : null}
                        </span>
                      </td>
                    )}
                    {situacao === 'fechados' ? (
                      <td className="whitespace-nowrap px-4 py-3.5 align-top text-slate-600 sm:px-6 dark:text-slate-400">
                        {t.fechado_em ? new Date(t.fechado_em).toLocaleString('pt-BR') : '—'}
                      </td>
                    ) : (
                      <td className="whitespace-nowrap px-4 py-3.5 align-top sm:px-6">
                        <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {t.status_nome ?? t.status_id}
                        </span>
                      </td>
                    )}
                    <td className="hidden px-4 py-3.5 align-top text-slate-600 lg:table-cell sm:px-6 dark:text-slate-400">
                      <span className="block break-words whitespace-normal leading-snug">
                        {t.atendente_nome ?? 'Na fila'}
                      </span>
                    </td>
                    {mostrarColunasFila && (
                      <td className="hidden whitespace-nowrap px-4 py-3.5 align-top text-slate-600 lg:table-cell sm:px-6 dark:text-slate-400">
                        {formatarTempoNaFila(t.fila_desde_at)}
                      </td>
                    )}
                    {mostrarColunasFila && (
                      <td className="hidden px-4 py-3.5 align-top xl:table-cell sm:px-6">
                        {t.distribuicao_modo_setor === 'auto_apos_timeout' && t.distribuicao_auto_em_minutos != null ? (
                          <span className="inline-flex rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                            Auto em {t.distribuicao_auto_em_minutos} min
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </>
        )}
      </div>
    </PageContainer>
  )
}
