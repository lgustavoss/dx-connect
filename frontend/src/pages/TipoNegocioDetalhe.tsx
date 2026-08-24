import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, tiposNegocio } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { DetailRow } from '../components/ui/DetailRow'
import { BadgeAtivo } from '../components/ui/BadgeAtivo'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento } from '../api/errorMessage'
import { VoltarButton } from '../components/ui/VoltarButton'

export function TipoNegocioDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/tipos-negocio')
  const tipoId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [item, setItem] = useState<Awaited<ReturnType<typeof tiposNegocio.get>> | null>(null)

  useEffect(() => {
    if (!id || Number.isNaN(tipoId)) {
      setFalha({ titulo: 'Tipo de negócio não encontrado.', detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setFalha(null)
    tiposNegocio
      .get(tipoId)
      .then((t) => {
        if (!cancelled) setItem(t)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Tipo de negócio não encontrado.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, tipoId])

  if (loading) {
    return (
      <div className="mx-auto w-full min-w-0 max-w-6xl space-y-6 pb-10">
        <div className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para acessar este tipo de negócio."
        voltarPara="/tipos-negocio"
        voltarLabel="Voltar para Tipos de negócio"
      />
    )
  }

  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }

  if (!item) return null

  return (
    <div className="mx-auto w-full min-w-0 max-w-6xl space-y-6 pb-10">
      <VoltarButton onClick={voltarAnterior} />

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{item.nome}</h1>
          <BadgeAtivo ativo={item.ativo} />
        </div>
        <Button onClick={() => navigate(`/tipos-negocio/${item.id}/editar`)}>Editar</Button>
      </header>

      <Card title="Dados do tipo de negócio">
        <dl>
          <DetailRow label="ID" value={String(item.id)} mono />
          <DetailRow label="Nome" value={item.nome} />
          <DetailRow label="Situação" value={item.ativo ? 'Ativo' : 'Inativo'} />
        </dl>
      </Card>
    </div>
  )
}
