import { useEffect, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, funcionariosRede, redes, empresas, type FuncionariosRede } from '../api/client'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'

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

export function FuncionarioRedeDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/funcionarios-rede')
  const toast = useToast()
  const funcionarioId = id ? parseInt(id, 10) : NaN

  const [f, setF] = useState<FuncionariosRede.Funcionario | null>(null)
  const [redeNome, setRedeNome] = useState('')
  const [vinculoExtra, setVinculoExtra] = useState<ReactNode>(null)
  const [loading, setLoading] = useState(true)
  const [loadFailure, setLoadFailure] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [forbidden, setForbidden] = useState(false)

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
    setVinculoExtra(null)

    funcionariosRede
      .get(funcionarioId)
      .then(async (func) => {
        if (cancelled) return
        setF(func)

        const rid = func.rede_id
        if (rid != null) {
          try {
            const r = await redes.get(rid)
            if (!cancelled) setRedeNome(r.nome)
          } catch {
            if (!cancelled) setRedeNome('—')
          }
        } else if (!cancelled) setRedeNome('')

        if (cancelled) return

        if (func.tipo === 'socio') {
          setVinculoExtra(
            <p className="text-sm text-slate-700 dark:text-slate-200">
              Pessoa vinculada como <strong>sócio</strong> da rede (visão e cadastros no contexto da rede).
            </p>,
          )
        } else if (func.tipo === 'colaborador' && func.empresa_id) {
          try {
            const em = await empresas.get(func.empresa_id)
            if (!cancelled) {
              setVinculoExtra(
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Colaborador da empresa{' '}
                  <Link
                    to={`/empresas/${em.id}`}
                    className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-2 hover:decoration-slate-500 dark:text-slate-100 dark:decoration-slate-700 dark:hover:decoration-slate-500"
                  >
                    {em.nome}
                  </Link>
                  .
                </p>,
              )
            }
          } catch {
            if (!cancelled) {
              setVinculoExtra(
                <p className="text-sm text-slate-600 dark:text-slate-400">Empresa vinculada (ID {func.empresa_id}) não encontrada.</p>,
              )
            }
          }
        } else if (func.tipo === 'supervisor' && func.empresa_ids?.length) {
          try {
            const lista = await Promise.all(
              func.empresa_ids.map((eid) =>
                empresas.get(eid).catch(() => null),
              ),
            )
            if (cancelled) return
            const ok = lista.filter(Boolean) as Awaited<ReturnType<typeof empresas.get>>[]
            if (ok.length === 0) {
              setVinculoExtra(<p className="text-sm text-slate-600 dark:text-slate-400">Não foi possível carregar os nomes das empresas.</p>)
            } else {
              setVinculoExtra(
                <ul className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-slate-700 dark:text-slate-200">
                  {ok.map((em) => (
                    <li key={em.id}>
                      <Link
                        to={`/empresas/${em.id}`}
                        className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-2 hover:decoration-slate-500 dark:text-slate-100 dark:decoration-slate-700 dark:hover:decoration-slate-500"
                      >
                        {em.nome}
                      </Link>
                    </li>
                  ))}
                </ul>,
              )
            }
          } catch {
            if (!cancelled) setVinculoExtra(null)
          }
        } else {
          setVinculoExtra(null)
        }
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

  function abrirEdicao() {
    if (!f) return
    navigate(`/funcionarios-rede/${f.id}/editar`)
  }

  async function handleExcluir() {
    if (!f || !confirm('Excluir este funcionário? Esta ação não pode ser desfeita.')) return
    try {
      await funcionariosRede.delete(f.id)
      toast.showSuccess('Funcionário excluído.')
      voltarAnterior()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir o funcionário.'))
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-4 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-9 w-2/3 max-w-md animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="h-48 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para acessar este funcionário."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/funcionarios-rede"
          voltarLabel="Voltar para Funcionários"
        />
      </div>
    )
  }

  if (loadFailure) {
    return (
      <CarregamentoFalhou titulo={loadFailure.titulo} detalhe={loadFailure.detalhe} onVoltar={voltarAnterior} />
    )
  }

  if (!f) {
    return null
  }

  const createdRaw = f.created_at
  const createdFmt =
    createdRaw != null && createdRaw !== ''
      ? new Date(createdRaw).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
      : null

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-10">
      <div>
        <button
          type="button"
          onClick={voltarAnterior}
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar
        </button>
      </div>

      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 md:text-3xl">{f.nome}</h1>
            <p className="break-all text-sm text-slate-600 dark:text-slate-400">{f.email}</p>
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
            <Button variant="secondary" onClick={voltarAnterior}>
              Voltar
            </Button>
            <Button onClick={abrirEdicao}>Editar</Button>
            <Button variant="danger" onClick={handleExcluir}>
              Excluir
            </Button>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7 dark:border-slate-800/90 dark:bg-slate-900/60">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Vínculos</h2>
          <dl>
            <div className="grid grid-cols-1 gap-0.5 border-b border-slate-100 py-3 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-6 sm:py-3.5">
              <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Rede</dt>
              <dd className="text-sm">
                {f.rede_id != null && redeNome && redeNome !== '—' ? (
                  <Link
                    to={`/redes/${f.rede_id}`}
                    className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-2 transition-colors hover:text-slate-950 hover:decoration-slate-500 dark:text-slate-100 dark:decoration-slate-700 dark:hover:decoration-slate-500"
                  >
                    {redeNome}
                  </Link>
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
      </div>
    </div>
  )
}
