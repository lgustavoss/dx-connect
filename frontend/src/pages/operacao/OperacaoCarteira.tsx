/**
 * Carteira da operação com badge de saúde/engajamento por cliente (#914).
 *
 * Página nova — a rota (`/operacao/carteira`) é integrada pelo Lead no App.tsx.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import {
  operacaoTimeline,
  SAUDE_BADGE_CLASS,
  SAUDE_LABEL,
  SAUDE_STATUS_OPCOES,
  type SaudeEmpresa,
  type SaudeStatus,
} from '../../api/operacaoTimeline'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { formatDateTime } from '../../lib/formatDateTime'
import { SemPermissao } from '../SemPermissao'

const LIMITE = 20

function textoUltimoEvento(item: SaudeEmpresa): string {
  if (!item.ultimo_evento_em) return 'Sem histórico registrado'
  const dias = item.dias_sem_movimento ?? 0
  const quando = dias === 0 ? 'hoje' : dias === 1 ? 'há 1 dia' : `há ${dias} dias`
  return `${formatDateTime(item.ultimo_evento_em)} (${quando})`
}

/** Primeiro motivo do status atual — o restante fica nos sinais da timeline. */
function motivoResumido(item: SaudeEmpresa): string {
  return item.motivos[0] ?? 'Sem sinais de atenção.'
}

export function OperacaoCarteira() {
  const toast = useToast()
  const [itens, setItens] = useState<SaudeEmpresa[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [busca, setBusca] = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [status, setStatus] = useState<SaudeStatus | ''>('')
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => {
      setBuscaDebounced(busca.trim())
      setOffset(0)
    }, 400)
    return () => clearTimeout(timer)
  }, [busca])

  const carregar = useCallback(() => {
    setLoading(true)
    setErro(null)
    setForbidden(false)
    operacaoTimeline
      .carteira({
        busca: buscaDebounced || undefined,
        status: status || undefined,
        offset,
        limit: LIMITE,
      })
      .then(({ items, total: totalApi }) => {
        setItens(items)
        setTotal(totalApi)
      })
      .catch((err) => {
        setItens([])
        setTotal(0)
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        const mensagem = mensagemFalhaParaToast(err, 'Não foi possível carregar a carteira.')
        setErro(mensagem)
        toast.showError(mensagem)
      })
      .finally(() => setLoading(false))
  }, [buscaDebounced, status, offset, toast])

  useEffect(() => {
    carregar()
  }, [carregar])

  const intervalo = useMemo(() => {
    if (total === 0) return '0 clientes'
    const inicio = offset + 1
    const fim = Math.min(offset + itens.length, total)
    return `${inicio}–${fim} de ${total}`
  }, [offset, itens.length, total])

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver a carteira."
        detail="Peça ao gestor a permissão de CRM (crm.ver) para acompanhar a saúde dos clientes."
        voltarPara="/"
        voltarLabel="Voltar para o início"
      />
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Carteira da operação"
        subtitle="Saúde e engajamento por cliente, com os sinais objetivos que explicam o status."
      />

      <Card
        title="Clientes atendidos"
        description="Status calculado a partir de CRM, implantação e suporte. Clique em um cliente para abrir a timeline 360."
      >
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1">
            <Input
              label="Buscar cliente"
              placeholder="Nome, razão social ou CNPJ"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          </div>
          <div className="w-48">
            <Select
              label="Saúde"
              value={status}
              onChange={(valor) => {
                setStatus(valor === '' ? '' : (valor as SaudeStatus))
                setOffset(0)
              }}
              options={SAUDE_STATUS_OPCOES.map((opcao) => ({ value: opcao.value, label: opcao.label }))}
              includeEmpty
              emptyLabel="Todas"
            />
          </div>
        </div>

        {erro ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
            <p>{erro}</p>
            <Button variant="secondary" className="mt-3" onClick={carregar}>
              Tentar novamente
            </Button>
          </div>
        ) : loading ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Carregando carteira…</p>
        ) : itens.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Nenhum cliente encontrado com os filtros atuais.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <th className="py-3 pr-4 font-semibold">Cliente</th>
                  <th className="py-3 pr-4 font-semibold">Rede</th>
                  <th className="py-3 pr-4 font-semibold">Última movimentação</th>
                  <th className="py-3 pr-4 font-semibold">Saúde</th>
                  <th className="py-3 font-semibold"> </th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item) => (
                  <tr
                    key={item.empresa_id}
                    className="border-b border-slate-100 last:border-0 dark:border-slate-800/70"
                  >
                    <td className="py-3 pr-4">
                      <p className="font-medium text-slate-800 dark:text-slate-100">
                        {item.empresa_nome}
                      </p>
                      {!item.ativo ? (
                        <p className="text-xs text-slate-500 dark:text-slate-400">Inativo</p>
                      ) : null}
                    </td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">
                      {item.rede_nome ?? '—'}
                    </td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">
                      {textoUltimoEvento(item)}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${SAUDE_BADGE_CLASS[item.status]}`}
                        title={motivoResumido(item)}
                      >
                        {SAUDE_LABEL[item.status]}
                      </span>
                      <p className="mt-1 max-w-[240px] text-xs text-slate-500 dark:text-slate-400">
                        {motivoResumido(item)}
                      </p>
                    </td>
                    <td className="py-3 text-right">
                      <Link
                        to={`/operacao/timeline?empresa_id=${item.empresa_id}`}
                        className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-300"
                      >
                        Ver timeline
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">{intervalo}</p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={loading || offset === 0}
              onClick={() => setOffset((atual) => Math.max(0, atual - LIMITE))}
            >
              Anterior
            </Button>
            <Button
              variant="secondary"
              disabled={loading || offset + LIMITE >= total}
              onClick={() => setOffset((atual) => atual + LIMITE)}
            >
              Próxima
            </Button>
          </div>
        </div>
      </Card>
    </PageContainer>
  )
}
