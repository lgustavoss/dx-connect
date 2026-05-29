import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, statusTicket } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { DetailRow } from '../components/ui/DetailRow'
import { BadgeAtivo } from '../components/ui/BadgeAtivo'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento } from '../api/errorMessage'

export function StatusTicketDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/status-ticket')
  const statusId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [item, setItem] = useState<Awaited<ReturnType<typeof statusTicket.get>> | null>(null)

  useEffect(() => {
    if (!id || Number.isNaN(statusId)) {
      setFalha({ titulo: 'Status não encontrado.', detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setFalha(null)
    statusTicket
      .get(statusId)
      .then((s) => {
        if (!cancelled) setItem(s)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Status não encontrado.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, statusId])

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-48 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para acessar este status."
        voltarPara="/status-ticket"
        voltarLabel="Voltar para Status de ticket"
      />
    )
  }

  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }

  if (!item) return null

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
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{item.nome}</h1>
          <BadgeAtivo ativo={item.ativo} />
        </div>
        <Button onClick={() => navigate(`/status-ticket/${item.id}/editar`)}>Editar</Button>
      </header>

      <Card title="Dados do status">
        <dl>
          <DetailRow label="ID" value={String(item.id)} mono />
          <DetailRow label="Nome" value={item.nome} />
          <DetailRow label="Slug" value={item.slug} mono />
          <DetailRow label="Ordem" value={String(item.ordem)} mono />
          <DetailRow label="Situação" value={item.ativo ? 'Ativo' : 'Inativo'} />
        </dl>
      </Card>
    </div>
  )
}
