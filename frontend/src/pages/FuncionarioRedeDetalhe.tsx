import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError, funcionariosRede, tickets, type FuncionariosRede, type Tickets } from '../api/client'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { useAuth } from '../contexts/AuthContext'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { VoltarButton } from '../components/ui/VoltarButton'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { EmpresaChatsPanel } from '../components/EmpresaChatsPanel'
import { TicketsTabelaContexto } from '../components/TicketsTabelaContexto'
import { formatTelefoneBrExibicao } from '../utils/masks'
import { useTicketsAbertosContato } from '../hooks/useTicketsAbertosContato'

type Aba = 'geral' | 'chats' | 'tickets'
type SituacaoTickets = 'abertos' | 'fechados' | 'todos'

const tipoLabel: Record<string, string> = {
  socio: 'Sócio',
  supervisor: 'Supervisor',
  colaborador: 'Colaborador',
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  const v = value?.trim()
  return (
    <div className="grid grid-cols-1 gap-0.5 border-b border-slate-100 py-3 last:border-0 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-6 sm:py-3.5 dark:border-slate-800">
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">{label}</dt>
      <dd className="text-sm leading-relaxed text-slate-800 dark:text-slate-100">{v ? v : '—'}</dd>
    </div>
  )
}

const linkEmpresaClass =
  'font-medium text-slate-800 underline decoration-slate-300 underline-offset-2 hover:decoration-slate-500 dark:text-slate-100 dark:decoration-slate-700 dark:hover:decoration-slate-500'

function renderEmpresaVinculo(em: FuncionariosRede.EmpresaVinculo, admin: boolean) {
  if (admin) {
    return (
      <Link to={`/empresas/${em.id}`} className={linkEmpresaClass}>
        {em.nome}
      </Link>
    )
  }
  return <span className="font-medium text-slate-800 dark:text-slate-100">{em.nome}</span>
}

function buildVinculoExtra(func: FuncionariosRede.Funcionario, admin: boolean): ReactNode {
  if (func.tipo === 'socio') {
    return (
      <p className="text-sm text-slate-700 dark:text-slate-200">
        Pessoa vinculada como <strong>sócio</strong> da rede (visão e cadastros no contexto da rede).
      </p>
    )
  }
  const empresas = func.empresas_vinculo ?? []
  if (func.tipo === 'colaborador' && empresas.length > 0) {
    return (
      <p className="text-sm text-slate-700 dark:text-slate-200">
        Colaborador da empresa {renderEmpresaVinculo(empresas[0], admin)}.
      </p>
    )
  }
  if (func.tipo === 'supervisor' && empresas.length > 0) {
    return (
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-slate-700 dark:text-slate-200">
        {empresas.map((em) => (
          <li key={em.id}>{renderEmpresaVinculo(em, admin)}</li>
        ))}
      </ul>
    )
  }
  return null
}

export function FuncionarioRedeDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const voltarPara = (location.state as { voltarPara?: string } | null)?.voltarPara
  const { isAdmin } = useAuth()
  const voltarHistorico = useVoltarAnterior(isAdmin ? '/funcionarios-rede' : '/chat/atendendo')
  const voltar = useCallback(() => {
    if (voltarPara) {
      navigate(voltarPara)
      return
    }
    voltarHistorico()
  }, [navigate, voltarPara, voltarHistorico])
  const toast = useToast()
  const funcionarioId = id ? parseInt(id, 10) : NaN
  const returnPath = `/funcionarios-rede/${funcionarioId}${searchParams.get('aba') ? `?aba=${searchParams.get('aba')}` : ''}`

  const [f, setF] = useState<FuncionariosRede.Funcionario | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadFailure, setLoadFailure] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [aba, setAba] = useState<Aba>('geral')

  const [pageT, setPageT] = useState(1)
  const [buscaT, setBuscaT] = useState('')
  const [debouncedBuscaT, setDebouncedBuscaT] = useState('')
  const [situacaoT, setSituacaoT] = useState<SituacaoTickets>('abertos')
  const [ticketsItems, setTicketsItems] = useState<Tickets.Ticket[]>([])
  const [ticketsTotal, setTicketsTotal] = useState(0)
  const [loadingT, setLoadingT] = useState(false)
  const [reloadChatsSeq, setReloadChatsSeq] = useState(0)
  const [reloadTicketsSeq, setReloadTicketsSeq] = useState(0)
  const skipLocationReloadRef = useRef(true)
  const abaRef = useRef(aba)
  abaRef.current = aba

  const { total: ticketsAbertos, reload: reloadTicketsAbertos } = useTicketsAbertosContato(
    Number.isNaN(funcionarioId) ? null : funcionarioId,
  )

  useEffect(() => {
    const q = searchParams.get('aba')
    if (q === 'chats' || q === 'tickets' || q === 'geral') {
      setAba(q)
    }
  }, [searchParams])

  const mudarAba = (key: Aba) => {
    if (key !== aba) {
      if (key === 'chats') setReloadChatsSeq((n) => n + 1)
      if (key === 'tickets') setReloadTicketsSeq((n) => n + 1)
    }
    if (key === 'geral') reloadTicketsAbertos()
    setAba(key)
    const next = new URLSearchParams(searchParams)
    if (key === 'geral') next.delete('aba')
    else next.set('aba', key)
    setSearchParams(next, { replace: true })
  }

  const irParaTicketsAbertos = () => {
    setSituacaoT('abertos')
    setPageT(1)
    mudarAba('tickets')
  }

  useEffect(() => {
    if (skipLocationReloadRef.current) {
      skipLocationReloadRef.current = false
      return
    }
    const current = abaRef.current
    if (current === 'chats') setReloadChatsSeq((n) => n + 1)
    else if (current === 'tickets') setReloadTicketsSeq((n) => n + 1)
    else if (current === 'geral') reloadTicketsAbertos()
  }, [location.key, reloadTicketsAbertos])

  useEffect(() => {
    if (!id || isNaN(funcionarioId)) {
      setLoading(false)
      setLoadFailure({
        titulo: 'Funcionário não encontrado.',
        detalhe: 'O identificador na URL é inválido.',
      })
      return
    }
    let cancelled = false
    setLoading(true)
    setLoadFailure(null)
    setForbidden(false)

    funcionariosRede
      .get(funcionarioId)
      .then((func) => {
        if (!cancelled) setF(func)
      })
      .catch((err) => {
        if (!cancelled) {
          if (err instanceof ApiError && err.status === 403) {
            setForbidden(true)
            setF(null)
            return
          }
          setLoadFailure(interpretarFalhaCarregamento(err, 'Funcionário não encontrado.'))
          setF(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [id, funcionarioId])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaT(buscaT.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaT])

  useEffect(() => {
    if (aba !== 'tickets' || !funcionarioId || Number.isNaN(funcionarioId)) return
    let cancelled = false
    setLoadingT(true)
    tickets
      .list({
        funcionario_rede_id: funcionarioId,
        situacao: situacaoT,
        offset: (pageT - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
        busca: debouncedBuscaT || undefined,
      })
      .then(({ items, total }) => {
        if (!cancelled) {
          setTicketsItems(items)
          setTicketsTotal(total)
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingT(false)
      })
    return () => {
      cancelled = true
    }
  }, [aba, funcionarioId, pageT, debouncedBuscaT, situacaoT, reloadTicketsSeq])

  function abrirEdicao() {
    if (!f) return
    navigate(`/funcionarios-rede/${f.id}/editar`)
  }

  async function handleExcluir() {
    if (!f || !confirm('Excluir este funcionário? Esta ação não pode ser desfeita.')) return
    try {
      await funcionariosRede.delete(f.id)
      toast.showSuccess('Funcionário excluído.')
      voltar()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir o funcionário.'))
    }
  }

  if (loading) {
    return (
      <div className="mx-auto w-full min-w-0 max-w-6xl space-y-6 pb-10">
        <div className="h-4 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-9 w-2/3 max-w-md animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="h-48 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto w-full min-w-0 max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para acessar este contato."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara={isAdmin ? '/funcionarios-rede' : '/chat/atendendo'}
          voltarLabel={isAdmin ? 'Voltar para Funcionários' : 'Voltar para chats'}
        />
      </div>
    )
  }

  if (loadFailure) {
    return <CarregamentoFalhou titulo={loadFailure.titulo} detalhe={loadFailure.detalhe} onVoltar={voltar} />
  }

  if (!f) {
    return null
  }

  const createdRaw = f.created_at
  const createdFmt =
    createdRaw != null && createdRaw !== ''
      ? new Date(createdRaw).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
      : null
  const telefoneFmt = formatTelefoneBrExibicao(f.telefone) || null
  const vinculoExtra = buildVinculoExtra(f, isAdmin)
  const redeNome = f.rede_nome?.trim() || null

  const tabBtn = (key: Aba, label: string) => (
    <button
      type="button"
      onClick={() => mudarAba(key)}
      aria-current={aba === key ? 'page' : undefined}
      className={
        aba === key
          ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
          : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
      }
    >
      {label}
    </button>
  )

  return (
    <div className="mx-auto w-full min-w-0 max-w-6xl space-y-8 pb-10">
      <div>
        <VoltarButton onClick={voltar} />
      </div>

      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 md:text-3xl">{f.nome}</h1>
            <p className="break-all text-sm text-slate-600 dark:text-slate-400">{f.email || '—'}</p>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  f.ativo
                    ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-600/15 dark:bg-emerald-950/50 dark:text-emerald-300'
                    : 'bg-slate-100 text-slate-600 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700/60'
                }`}
              >
                {f.ativo ? 'Ativo' : 'Inativo'}
              </span>
              <span className="text-sm text-slate-500 dark:text-slate-400">{tipoLabel[f.tipo] ?? f.tipo}</span>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button variant="secondary" onClick={voltar}>
              Voltar
            </Button>
            {isAdmin ? (
              <>
                <Button onClick={abrirEdicao}>Editar</Button>
                <Button variant="danger" onClick={handleExcluir}>
                  Excluir
                </Button>
              </>
            ) : null}
          </div>
        </div>
      </header>

      <nav className="-mb-2 flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800" aria-label="Abas do contato">
        {tabBtn('geral', 'Geral')}
        {tabBtn('chats', 'Chats')}
        {tabBtn('tickets', 'Tickets')}
      </nav>

      {aba === 'geral' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-800/90 dark:bg-slate-900/60">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Vínculos</h2>
            <dl>
              <DetailRow label="Telefone" value={telefoneFmt} />
              <div className="grid grid-cols-1 gap-0.5 border-b border-slate-100 py-3 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-6 sm:py-3.5 dark:border-slate-800">
                <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Rede</dt>
                <dd className="text-sm">
                  {f.rede_id != null && redeNome ? (
                    isAdmin ? (
                      <Link
                        to={`/redes/${f.rede_id}`}
                        className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-2 transition-colors hover:text-slate-950 hover:decoration-slate-500 dark:text-slate-100 dark:decoration-slate-700 dark:hover:decoration-slate-500"
                      >
                        {redeNome}
                      </Link>
                    ) : (
                      <span className="text-slate-800 dark:text-slate-100">{redeNome}</span>
                    )
                  ) : (
                    <span className="text-slate-800 dark:text-slate-100">—</span>
                  )}
                </dd>
              </div>
            </dl>
            {vinculoExtra ? <div className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-800">{vinculoExtra}</div> : null}
          </section>

          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-800/90 dark:bg-slate-900/60">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Registro</h2>
            <dl>
              <DetailRow label="Cadastrado em" value={createdFmt} />
            </dl>
          </section>

          {ticketsAbertos != null && ticketsAbertos > 0 ? (
            <section className="rounded-2xl border border-amber-200/80 bg-amber-50/80 p-5 shadow-sm sm:p-7 lg:col-span-2 dark:border-amber-900/40 dark:bg-amber-950/20">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber-800 dark:text-amber-300">
                Atendimento
              </h2>
              <p className="text-sm text-amber-950 dark:text-amber-100">
                {ticketsAbertos} ticket{ticketsAbertos === 1 ? '' : 's'} aberto{ticketsAbertos === 1 ? '' : 's'} deste
                contato.
              </p>
              <button
                type="button"
                onClick={irParaTicketsAbertos}
                className="mt-3 text-sm font-medium text-amber-900 underline decoration-amber-400 underline-offset-2 hover:decoration-amber-600 dark:text-amber-200 dark:decoration-amber-700 dark:hover:decoration-amber-400"
              >
                Ver tickets abertos
              </button>
            </section>
          ) : null}
        </div>
      )}

      {aba === 'chats' && (
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
          <EmpresaChatsPanel funcionarioRedeId={f.id} returnPath={returnPath} reloadKey={reloadChatsSeq} />
        </section>
      )}

      {aba === 'tickets' && (
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
          <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
            Tickets abertos pelo contato no portal ou vinculados às conversas WhatsApp dele.
          </p>
          <div className="mb-4 flex flex-wrap gap-2">
            {(['abertos', 'fechados', 'todos'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setSituacaoT(s)
                  setPageT(1)
                }}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  situacaoT === s
                    ? 'bg-sky-100 text-sky-900 dark:bg-sky-950/50 dark:text-sky-200'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                }`}
              >
                {s === 'abertos' ? 'Abertos' : s === 'fechados' ? 'Fechados' : 'Todos'}
              </button>
            ))}
          </div>
          <BarraBuscaPaginacao
            busca={buscaT}
            onBuscaChange={(v) => {
              setBuscaT(v)
              setPageT(1)
            }}
            placeholder="Protocolo ou assunto..."
            page={pageT}
            total={ticketsTotal}
            onPageChange={setPageT}
            disabled={loadingT}
          />
          <div className="mt-4">
            <TicketsTabelaContexto
              items={ticketsItems}
              loading={loadingT}
              showEmpresaColumn
              emptyMessage="Nenhum ticket encontrado para este contato."
            />
          </div>
        </section>
      )}
    </div>
  )
}
