import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, atendentes, setores, type Atendentes, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { DetailRow } from '../components/ui/DetailRow'
import { BadgeAtivo } from '../components/ui/BadgeAtivo'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento } from '../api/errorMessage'

const roleLabel: Record<string, string> = { admin: 'Administrador', atendente: 'Atendente' }

function fmtMediaAvaliacao(media: number | null): string {
  if (media == null) return '—'
  return media.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function AtendenteDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/atendentes')
  const atendenteId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [atendente, setAtendente] = useState<Atendentes.Atendente | null>(null)
  const [avaliacoes, setAvaliacoes] = useState<Atendentes.AvaliacoesResumo | null>(null)
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])

  useEffect(() => {
    if (!id || Number.isNaN(atendenteId)) {
      setFalha({ titulo: 'Atendente não encontrado.', detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setFalha(null)
    Promise.all([
      atendentes.get(atendenteId),
      atendentes.avaliacoes(atendenteId),
      coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: true, offset: o, limit: l })),
    ])
      .then(([a, av, setoresAll]) => {
        if (cancelled) return
        setAtendente(a)
        setAvaliacoes(av)
        setSetoresList(setoresAll)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Atendente não encontrado.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, atendenteId])

  const setoresVinculados = useMemo(() => {
    if (!atendente) return '—'
    const ids = new Set(atendente.setor_ids ?? [])
    const nomes = setoresList.filter((s) => ids.has(s.id)).map((s) => s.nome)
    return nomes.length > 0 ? nomes.join(', ') : 'Nenhum setor vinculado'
  }, [atendente, setoresList])

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para acessar este atendente."
        voltarPara="/atendentes"
        voltarLabel="Voltar para Atendentes"
      />
    )
  }

  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }

  if (!atendente) return null

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <button
        type="button"
        onClick={voltarAnterior}
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
      >
        <span aria-hidden>←</span> Voltar
      </button>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{atendente.nome}</h1>
          <div className="flex flex-wrap items-center gap-2">
            <BadgeAtivo ativo={atendente.ativo} labelAtivo="Ativo" labelInativo="Inativo" />
            <span className="text-sm text-slate-600 dark:text-slate-400">{roleLabel[atendente.role] ?? atendente.role}</span>
          </div>
        </div>
        <Button onClick={() => navigate(`/atendentes/${atendente.id}/editar`)}>Editar</Button>
      </header>

      <Card title="Dados do atendente">
        <dl>
          <DetailRow label="ID" value={String(atendente.id)} mono />
          <DetailRow label="Nome" value={atendente.nome} />
          <DetailRow label="E-mail" value={atendente.email} />
          <DetailRow label="Perfil" value={roleLabel[atendente.role] ?? atendente.role} />
          <DetailRow label="Setores" value={setoresVinculados} />
          <DetailRow label="Situação" value={atendente.ativo ? 'Ativo' : 'Inativo'} />
          {atendente.must_change_password ? (
            <DetailRow label="Senha" value="Deve alterar a senha no próximo acesso" />
          ) : null}
        </dl>
      </Card>

      {avaliacoes ? (
        <Card title="Avaliações (CSAT)">
          <dl className="grid gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Geral</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-50">
                {fmtMediaAvaliacao(avaliacoes.geral.media)}
              </dd>
              <dd className="text-xs text-slate-500 dark:text-slate-400">{avaliacoes.geral.total} avaliação(ões)</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">WhatsApp</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-50">
                {fmtMediaAvaliacao(avaliacoes.whatsapp.media)}
              </dd>
              <dd className="text-xs text-slate-500 dark:text-slate-400">{avaliacoes.whatsapp.total} avaliação(ões)</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Tickets</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-50">
                {fmtMediaAvaliacao(avaliacoes.tickets.media)}
              </dd>
              <dd className="text-xs text-slate-500 dark:text-slate-400">{avaliacoes.tickets.total} avaliação(ões)</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Média geral ponderada por quantidade de respostas (WhatsApp + tickets por e-mail).
          </p>
        </Card>
      ) : null}
    </div>
  )
}
