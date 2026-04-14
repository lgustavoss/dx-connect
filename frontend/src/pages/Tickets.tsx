import { useState, useEffect, useMemo, useId } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  tickets,
  statusTicket,
  empresas,
  setores,
  atendentes,
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
import { Switch } from '../components/ui/Switch'

type ColunaOrdenacao =
  | 'protocolo'
  | 'rede'
  | 'empresa'
  | 'setor'
  | 'assunto'
  | 'status'
  | 'responsavel'

const searchIcon = (
  <svg className="size-4 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
)

export function Tickets() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const { isAdmin, user } = useAuth()
  const { soundEnabled, setSoundEnabled, count: filaCount } = useAlertaFilaSemResponsavel(Boolean(user))

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
  /** '' | 'sem_responsavel' | 'meus' — fila do setor vs. atribuídos a mim */
  const [filtroFila, setFiltroFila] = useState<'' | 'sem_responsavel' | 'meus'>(() => {
    const sr = searchParams.get('sem_responsavel')
    return sr === '1' || sr === 'true' ? 'sem_responsavel' : ''
  })
  const [filtroAtendente, setFiltroAtendente] = useState<number | ''>('')
  const [maisFiltrosAberto, setMaisFiltrosAberto] = useState(false)
  const painelFiltrosId = useId()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaOrdenacao>()

  const setoresFiltro = useMemo(() => {
    const ativos = setoresOpt.filter((s) => s.ativo)
    const sorted = [...ativos].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
    if (isAdmin) return sorted
    const ids = new Set(user?.setor_ids ?? [])
    return sorted.filter((s) => ids.has(s.id))
  }, [isAdmin, user?.setor_ids, setoresOpt])

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

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE_PADRAO))
  const inicio = total === 0 ? 0 : (page - 1) * PAGE_SIZE_PADRAO + 1
  const fim = Math.min(page * PAGE_SIZE_PADRAO, total)

  const temFiltrosAtivos =
    busca.trim() !== '' ||
    filtroEmpresa !== '' ||
    filtroSetor !== '' ||
    filtroStatus !== '' ||
    filtroFila !== '' ||
    (isAdmin && filtroAtendente !== '')

  const qtdFiltrosRefinamento =
    (filtroEmpresa !== '' ? 1 : 0) +
    (filtroSetor !== '' ? 1 : 0) +
    (filtroStatus !== '' ? 1 : 0) +
    (isAdmin && filtroAtendente !== '' ? 1 : 0)

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
      return
    }
    coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
      atendentes.list({ incluir_inativos: false, offset: o, limit: l }),
    ).then(setAtendentesOpt)
  }, [isAdmin])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, filtroStatus, filtroEmpresa, filtroSetor, filtroFila, filtroAtendente, ordenarPor, ordem])

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
    tickets
      .list({
        busca: debouncedBusca || undefined,
        status_id: filtroStatus !== '' ? Number(filtroStatus) : undefined,
        empresa_id: filtroEmpresa !== '' ? Number(filtroEmpresa) : undefined,
        setor_id: filtroSetor !== '' ? Number(filtroSetor) : undefined,
        sem_responsavel: filtroFila === 'sem_responsavel' ? true : undefined,
        meus: filtroFila === 'meus' ? true : undefined,
        atendente_id:
          isAdmin && filtroFila === '' && filtroAtendente !== '' ? Number(filtroAtendente) : undefined,
        ...sortParams,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .catch(() => {
        toast.showWarning('Não foi possível carregar os tickets.')
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [
    page,
    debouncedBusca,
    filtroStatus,
    filtroEmpresa,
    filtroSetor,
    filtroFila,
    filtroAtendente,
    isAdmin,
    ordenarPor,
    ordem,
  ])

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
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Tickets</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Acompanhe e filtre as demandas do suporte.</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Switch
            bare
            checked={soundEnabled}
            onCheckedChange={setSoundEnabled}
            label="Som de fila"
            description={filaCount > 0 ? `${filaCount} na fila sem responsável` : 'Desligue se não quiser alerta'}
          />
          <Link to="/tickets/novo">
            <Button>Novo ticket</Button>
          </Link>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900/40">
        <div className="border-b border-slate-100/90 px-4 py-5 sm:px-6 dark:border-slate-800">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-3">
            <div className="relative min-w-0 flex-1">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">{searchIcon}</span>
              <input
                type="search"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar por protocolo, assunto ou empresa…"
                disabled={loading}
                className="w-full rounded-xl border-0 bg-slate-50 py-2.5 pl-10 pr-4 text-sm text-slate-900 shadow-inner ring-1 ring-slate-200/80 transition-shadow placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-400/25 dark:bg-slate-900/60 dark:text-slate-100 dark:ring-slate-700 dark:placeholder:text-slate-500 dark:focus:bg-slate-900"
                aria-label="Buscar tickets"
              />
            </div>
            {temFiltrosAtivos && (
              <button
                type="button"
                onClick={limparFiltros}
                className="shrink-0 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              >
                Limpar tudo
              </button>
            )}
          </div>

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
              <span className="font-medium text-slate-600 dark:text-slate-300">Na fila</span> mostra chamados sem responsável no setor.
              {isAdmin && ' Use «Mais filtros» para ver tickets de um atendente.'}
            </p>
          </div>

          <div className="mt-6 border-t border-slate-200/70 pt-5 dark:border-slate-800">
            <button
              type="button"
              id={`${painelFiltrosId}-toggle`}
              aria-expanded={maisFiltrosAberto}
              aria-controls={painelFiltrosId}
              onClick={() => setMaisFiltrosAberto((o) => !o)}
              className="group flex w-full items-center justify-between gap-2 rounded-xl py-1 text-left sm:w-auto sm:justify-start sm:gap-3"
            >
              <span className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                <span
                  className={`inline-flex size-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition-transform dark:bg-slate-800 dark:text-slate-400 ${
                    maisFiltrosAberto ? 'rotate-180' : ''
                  }`}
                  aria-hidden
                >
                  <svg className="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
                Mais filtros
                {qtdFiltrosRefinamento > 0 && (
                  <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold tabular-nums text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                    {qtdFiltrosRefinamento}
                  </span>
                )}
              </span>
              <span className="text-xs text-slate-400 dark:text-slate-500 sm:hidden">
                {maisFiltrosAberto ? 'Recolher' : 'Empresa, setor, status'}
              </span>
            </button>

            {maisFiltrosAberto && (
              <div
                id={painelFiltrosId}
                role="region"
                aria-labelledby={`${painelFiltrosId}-toggle`}
                className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
              >
                <Select
                  label="Empresa"
                  labelStyle="overline"
                  className="min-w-0"
                  value={filtroEmpresa}
                  onChange={(v) => setFiltroEmpresa(v === '' ? '' : Number(v))}
                  options={opcoesEmpresaFiltro}
                  includeEmpty
                  emptyLabel="Todas"
                  placeholder="Todas"
                />
                <Select
                  label="Setor"
                  labelStyle="overline"
                  className="min-w-0"
                  value={filtroSetor}
                  onChange={(v) => setFiltroSetor(v === '' ? '' : Number(v))}
                  options={opcoesSetorFiltro}
                  includeEmpty
                  emptyLabel="Todos"
                  placeholder="Todos"
                />
                <Select
                  label="Status"
                  labelStyle="overline"
                  className="min-w-0"
                  value={filtroStatus}
                  onChange={(v) => setFiltroStatus(v === '' ? '' : Number(v))}
                  options={opcoesStatusFiltro}
                  includeEmpty
                  emptyLabel="Todos"
                  placeholder="Todos"
                />
                {isAdmin && (
                  <Select
                    label="Responsável (equipe)"
                    labelStyle="overline"
                    className="min-w-0 sm:col-span-2 lg:col-span-1"
                    value={filtroAtendente}
                    onChange={(v) => {
                      setFiltroAtendente(v === '' ? '' : Number(v))
                      if (v !== '') setFiltroFila('')
                    }}
                    options={opcoesAtendenteFiltro}
                    includeEmpty
                    emptyLabel="Qualquer"
                    placeholder="Qualquer"
                    disabled={filtroFila !== ''}
                  />
                )}
              </div>
            )}
          </div>
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
          <div className="overflow-hidden">
            <table className="w-full table-auto text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel
                    coluna="protocolo"
                    rotulo="Protocolo"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="whitespace-nowrap px-4 py-3 sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="rede"
                    rotulo="Rede"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="hidden px-4 py-3 lg:table-cell sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="empresa"
                    rotulo="Empresa"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="px-4 py-3 sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="setor"
                    rotulo="Setor"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="hidden px-4 py-3 xl:table-cell sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="assunto"
                    rotulo="Assunto"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="hidden px-4 py-3 md:table-cell sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="status"
                    rotulo="Status"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="whitespace-nowrap px-4 py-3 sm:px-6"
                  />
                  <CabecalhoOrdenavel
                    coluna="responsavel"
                    rotulo="Responsável"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="hidden px-4 py-3 lg:table-cell sm:px-6"
                  />
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
                    <td className="whitespace-nowrap px-4 py-3.5 align-top font-mono text-sm text-slate-900 sm:px-6 dark:text-slate-100">
                      {t.protocolo}
                    </td>
                    <td
                      className="hidden px-4 py-3.5 align-top text-slate-600 lg:table-cell sm:px-6 dark:text-slate-400"
                      title={t.rede_nome}
                    >
                      <span className="block break-words whitespace-normal leading-snug">{t.rede_nome ?? '—'}</span>
                    </td>
                    <td
                      className="min-w-0 px-4 py-3.5 align-top sm:px-6"
                      title={t.empresa_nome}
                    >
                      <div className="min-w-0">
                        <p className="break-words whitespace-normal font-medium leading-snug text-slate-900 dark:text-slate-100">
                          {t.empresa_nome ?? String(t.empresa_id)}
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
                    <td className="whitespace-nowrap px-4 py-3.5 align-top sm:px-6">
                      <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                        {t.status_nome ?? t.status_id}
                      </span>
                    </td>
                    <td className="hidden px-4 py-3.5 align-top text-slate-600 lg:table-cell sm:px-6 dark:text-slate-400">
                      <span className="block break-words whitespace-normal leading-snug">
                        {t.atendente_nome ?? 'Na fila'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
