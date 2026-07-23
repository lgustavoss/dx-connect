import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasClientes } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { DetailRow } from '../../components/ui/DetailRow'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SemPermissao } from '../SemPermissao'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import {
  badgeClassStatusClienteSaaS,
  hrefInstanciaCliente,
  labelStatusClienteSaaS,
} from '../../lib/saasControlPlane'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = iso.slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return iso
  return `${day}/${m}/${y}`
}

export function SaasLicencaDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/saas/licencas')
  const clienteId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [item, setItem] = useState<Awaited<ReturnType<typeof saasClientes.get>> | null>(null)

  function carregar() {
    if (!id || Number.isNaN(clienteId)) {
      setFalha({ titulo: 'Licença não encontrada.', detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    setFalha(null)
    saasClientes
      .get(clienteId)
      .then((c) => setItem(c))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          const detail =
            typeof err.body === 'object' && err.body && 'detail' in err.body
              ? String((err.body as { detail?: unknown }).detail ?? '')
              : ''
          if (detail.toLowerCase().includes('não disponível')) {
            setIndisponivel(true)
          } else {
            setFalha(interpretarFalhaCarregamento(err, 'Licença não encontrada.'))
          }
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Licença não encontrada.'))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recarrega só quando muda o id
  }, [id, clienteId])

  async function runAction(
    action: () => Promise<Awaited<ReturnType<typeof saasClientes.get>>>,
    okMsg: string,
  ) {
    setActing(true)
    try {
      const updated = await action()
      setItem(updated)
      toast.showSuccess(okMsg)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível concluir a ação.'))
    } finally {
      setActing(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel de licenças não disponível nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para acessar esta licença."
        voltarPara="/saas/licencas"
        voltarLabel="Voltar para Licenças"
      />
    )
  }

  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }

  if (!item) return null

  const href = hrefInstanciaCliente(item.instancia_url)

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
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            {item.nome}
          </h1>
          <span
            className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClassStatusClienteSaaS(item.status)}`}
          >
            {labelStatusClienteSaaS(item.status)}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" disabled={acting} onClick={() => navigate(`/saas/licencas/${item.id}/editar`)}>
            Editar
          </Button>
          {item.status !== 'suspenso' ? (
            <Button
              variant="secondary"
              disabled={acting}
              onClick={() => runAction(() => saasClientes.suspender(item.id), 'Cliente suspenso.')}
            >
              Suspender
            </Button>
          ) : (
            <Button
              variant="secondary"
              disabled={acting}
              onClick={() => runAction(() => saasClientes.reativar(item.id), 'Cliente reativado.')}
            >
              Reativar
            </Button>
          )}
          {!item.provisionamento_solicitado ? (
            <Button
              variant="secondary"
              disabled={acting}
              onClick={() =>
                runAction(
                  () => saasClientes.solicitarProvisionamento(item.id),
                  'Provisionamento solicitado (fila manual).',
                )
              }
            >
              Solicitar provisionamento
            </Button>
          ) : null}
        </div>
      </header>

      <Card title="Dados da licença">
        <dl>
          <DetailRow label="ID" value={String(item.id)} mono />
          <DetailRow label="Slug" value={item.slug} mono />
          <DetailRow label="Plano" value={item.plano || '—'} />
          <DetailRow label="Início" value={formatDate(item.data_inicio)} />
          <DetailRow label="Renovação" value={formatDate(item.data_renovacao)} />
          <DetailRow label="Instância" value={item.instancia_url || '—'} />
          <DetailRow
            label="Provisionamento"
            value={item.provisionamento_solicitado ? 'Solicitado' : 'Não solicitado'}
          />
          <DetailRow label="Notas" value={item.notas || '—'} />
        </dl>
      </Card>
      {href ? (
        <Card title="Acesso à instância">
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-sky-600 hover:underline dark:text-sky-400"
          >
            Abrir {item.instancia_url}
          </a>
        </Card>
      ) : null}
    </div>
  )
}
