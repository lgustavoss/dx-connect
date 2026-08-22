import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, respostasProntas } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { DetailRow } from '../components/ui/DetailRow'
import { BadgeAtivo } from '../components/ui/BadgeAtivo'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento } from '../api/errorMessage'
import { VoltarButton } from '../components/ui/VoltarButton'

export function RespostaProntaDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/respostas-prontas')
  const respostaId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [item, setItem] = useState<Awaited<ReturnType<typeof respostasProntas.get>> | null>(null)

  useEffect(() => {
    if (!id || Number.isNaN(respostaId)) {
      setFalha({ titulo: 'Resposta pronta não encontrada.', detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setFalha(null)
    respostasProntas
      .get(respostaId)
      .then((r) => {
        if (!cancelled) setItem(r)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Resposta pronta não encontrada.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, respostaId])

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-56 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para acessar esta resposta pronta."
        voltarPara="/respostas-prontas"
        voltarLabel="Voltar para Respostas prontas"
      />
    )
  }

  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }

  if (!item) return null

  const escopo = item.setor_nome ?? (item.setor_id != null ? `Setor #${item.setor_id}` : 'Global (todos os setores)')

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <VoltarButton onClick={voltarAnterior} />

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{item.titulo}</h1>
          <BadgeAtivo ativo={item.ativo} />
        </div>
        <Button onClick={() => navigate(`/respostas-prontas/${item.id}/editar`)}>Editar</Button>
      </header>

      <Card title="Conteúdo">
        <dl>
          <DetailRow label="ID" value={String(item.id)} mono />
          <DetailRow label="Título" value={item.titulo} />
          <DetailRow label="Corpo" value={item.corpo} multiline />
        </dl>
      </Card>

      <Card title="Escopo e ordem">
        <dl>
          <DetailRow label="Escopo" value={escopo} />
          <DetailRow label="Ordem" value={String(item.ordem)} mono />
          <DetailRow label="Situação" value={item.ativo ? 'Ativa' : 'Inativa'} />
        </dl>
      </Card>
    </div>
  )
}
