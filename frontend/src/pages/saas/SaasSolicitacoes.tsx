import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, saasSolicitacoes, type SaasSolicitacoesProduto } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../../components/ui/BarraBuscaPaginacao'
import { Card } from '../../components/ui/Card'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { SemPermissao } from '../SemPermissao'

const TIPO_OPTS = [
  { value: 'sugestao', label: 'Sugestão' },
  { value: 'problema', label: 'Problema' },
]

const STATUS_OPTS = [
  { value: 'aberta', label: 'Recebida' },
  { value: 'em_analise', label: 'Em análise' },
  { value: 'planejada', label: 'Planejada' },
  { value: 'em_desenvolvimento', label: 'Em desenvolvimento' },
  { value: 'concluida', label: 'Concluída' },
  { value: 'nao_sera_desenvolvida', label: 'Não será desenvolvida' },
]

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function rotuloTipo(tipo: string): string {
  return tipo === 'problema' ? 'Problema' : 'Sugestão'
}

export function SaasSolicitacoes() {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<SaasSolicitacoesProduto.ListaItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [tipoFiltro, setTipoFiltro] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, tipoFiltro, statusFiltro])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasSolicitacoes
      .list({
        busca: debouncedBusca || undefined,
        tipo: tipoFiltro || undefined,
        status: statusFiltro || undefined,
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
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos as solicitações.'))
        setList([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, page, tipoFiltro, statusFiltro, toast])

  useEffect(() => {
    load()
  }, [load])

  if (indisponivel) {
    return (
      <SemPermissao
        title="Fila de sugestões não disponível nesta instância."
        detail="Este módulo só existe na instância comercial DeskRudder."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  return (
    <ConfigListPageShell
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para ver a fila de sugestões."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      }
      title="Sugestões das instâncias"
      subtitle="Pedidos abertos pelos clientes nas Release Notes. Altere o status e responda no detalhe — o cliente vê o andamento em Minhas solicitações."
    >
      <Card>
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por protocolo, título, cliente, slug ou autor…"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={
            <div className="flex min-w-0 flex-wrap gap-2">
              <div className="min-w-[9rem] shrink-0">
                <Select
                  aria-label="Filtrar por tipo"
                  value={tipoFiltro}
                  onChange={(v) => setTipoFiltro(String(v))}
                  options={TIPO_OPTS}
                  includeEmpty
                  emptyLabel="Todos os tipos"
                  disabled={loading}
                />
              </div>
              <div className="min-w-[10rem] shrink-0">
                <Select
                  aria-label="Filtrar por status"
                  value={statusFiltro}
                  onChange={(v) => setStatusFiltro(String(v))}
                  options={STATUS_OPTS}
                  includeEmpty
                  emptyLabel="Todos os status"
                  disabled={loading}
                />
              </div>
            </div>
          }
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhuma solicitação ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Protocolo</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Cliente</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Tipo</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Título</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Autor</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Peso</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Status</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Quando</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((item) => (
                  <tr
                    key={item.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/saas/solicitacoes/${item.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/saas/solicitacoes/${item.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    <td className="px-4 py-3 font-mono text-sm text-cyan-800 dark:text-cyan-300 sm:px-6">
                      {item.protocolo || '—'}
                    </td>
                    <td className="px-4 py-3 sm:px-6">
                      <p className="font-medium text-slate-900 dark:text-slate-50">
                        {item.cliente_nome || item.instance_slug}
                      </p>
                      <p className="font-mono text-xs text-slate-500">{item.instance_slug}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300 sm:px-6">{rotuloTipo(item.tipo)}</td>
                    <td className="px-4 py-3 sm:px-6">
                      <p className="font-medium text-slate-800 dark:text-slate-100">{item.titulo}</p>
                      {item.versao_contexto ? (
                        <p className="text-xs text-slate-500">v{item.versao_contexto}</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300 sm:px-6">{item.autor_nome || '—'}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300 sm:px-6">
                      {(item.peso_clientes || 1) > 1 ? (
                        <span className="font-medium text-cyan-800 dark:text-cyan-300">
                          {item.peso_clientes} clientes
                        </span>
                      ) : (
                        '1'
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300 sm:px-6">{item.status_rotulo}</td>
                    <td className="px-4 py-3 text-slate-500 sm:px-6">
                      {formatWhen(item.created_at_origem || item.ingested_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </ConfigListPageShell>
  )
}
