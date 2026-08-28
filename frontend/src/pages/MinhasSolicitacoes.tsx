import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { solicitacoesMelhoria, type SolicitacoesMelhoria } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { VoltarButton } from '../components/ui/VoltarButton'
import { INPUT_FIELD_CLASS, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { PageLoading } from '../components/ui/PageLoading'
import { useToast } from '../components/ui/Toast'
import { SolicitacaoDescricao } from '../components/release/SolicitacaoDescricao'
import { SolicitacoesMelhoriaBadges } from '../components/solicitacoes/SolicitacoesMelhoriaBadges'
import { SolicitacoesMelhoriaListaTable } from '../components/solicitacoes/SolicitacoesMelhoriaListaTable'
import { SolicitacoesMelhoriaTimeline } from '../components/solicitacoes/SolicitacoesMelhoriaTimeline'
import { useAuth } from '../contexts/AuthContext'
import {
  classesCardMensagemStatus,
  SAAS_SOLICITACAO_FASES,
  SAAS_SOLICITACAO_STATUS,
  statusNaFase,
  type SaasSolicitacaoFase,
} from '../lib/saasSolicitacoes'

const STATUS_FINAIS = new Set(['concluida', 'nao_sera_desenvolvida'])

function FiltroChip({
  active,
  onClick,
  children,
  count,
  tone,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
  count?: number
  tone?: 'sky' | 'rose' | 'default'
}) {
  const toneActive =
    tone === 'sky'
      ? 'border-sky-500 bg-sky-50 text-sky-900 dark:border-sky-400 dark:bg-sky-950/50 dark:text-sky-100'
      : tone === 'rose'
        ? 'border-rose-500 bg-rose-50 text-rose-900 dark:border-rose-400 dark:bg-rose-950/50 dark:text-rose-100'
        : 'border-cyan-500 bg-cyan-50 text-cyan-950 dark:border-cyan-400 dark:bg-cyan-950/40 dark:text-cyan-50'

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
        active
          ? toneActive
          : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300 dark:hover:border-slate-600 dark:hover:bg-slate-800/60'
      }`}
    >
      {children}
      {count != null ? (
        <span className={`tabular-nums text-xs ${active ? 'opacity-80' : 'text-slate-400 dark:text-slate-500'}`}>
          {count}
        </span>
      ) : null}
    </button>
  )
}

function contarPorFase(items: SolicitacoesMelhoria.ListaItem[], fase: SaasSolicitacaoFase): number {
  return items.filter((item) => statusNaFase(item.status, fase)).length
}

/** Lista + detalhe das solicitações do usuário (#803). */
export function MinhasSolicitacoesPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const { user } = useAuth()
  const [lista, setLista] = useState<SolicitacoesMelhoria.ListaItem[]>([])
  const [detalhe, setDetalhe] = useState<SolicitacoesMelhoria.Detalhe | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetalhe, setLoadingDetalhe] = useState(false)
  const [resposta, setResposta] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')

  const tipoFiltro = searchParams.get('tipo') || ''
  const faseFiltro = (searchParams.get('fase') || '') as SaasSolicitacaoFase | ''
  const statusFiltro = searchParams.get('status') || ''

  function patchFiltros(next: Record<string, string | null>) {
    setSearchParams(
      (prev) => {
        const p = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(next)) {
          if (v == null || v === '') p.delete(k)
          else p.set(k, v)
        }
        return p
      },
      { replace: true },
    )
  }

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim().toLowerCase()), 300)
    return () => clearTimeout(t)
  }, [busca])

  const carregarLista = useCallback(() => {
    return solicitacoesMelhoria
      .minhas()
      .then(setLista)
      .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Falha ao carregar solicitações')))
  }, [toast])

  useEffect(() => {
    let cancel = false
    setLoading(true)
    void carregarLista().finally(() => {
      if (!cancel) setLoading(false)
    })
    return () => {
      cancel = true
    }
  }, [carregarLista])

  useEffect(() => {
    if (!id) {
      setDetalhe(null)
      setLoadingDetalhe(false)
      return
    }
    let cancel = false
    setLoadingDetalhe(true)
    void solicitacoesMelhoria
      .get(Number(id))
      .then((d) => {
        if (!cancel) setDetalhe(d)
      })
      .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Falha ao abrir solicitação')))
      .finally(() => {
        if (!cancel) setLoadingDetalhe(false)
      })
    return () => {
      cancel = true
    }
  }, [id, toast])

  const resumo = useMemo(
    () => ({
      total: lista.length,
      sugestoes: lista.filter((i) => i.tipo === 'sugestao').length,
      problemas: lista.filter((i) => i.tipo === 'problema').length,
      aguardando: contarPorFase(lista, 'aguardando'),
      desenvolvimento: contarPorFase(lista, 'desenvolvimento'),
      finalizadas: contarPorFase(lista, 'finalizadas'),
    }),
    [lista],
  )

  const listaFiltrada = useMemo(() => {
    return lista.filter((item) => {
      if (tipoFiltro && item.tipo !== tipoFiltro) return false
      if (statusFiltro && item.status !== statusFiltro) return false
      if (faseFiltro && !statusNaFase(item.status, faseFiltro)) return false
      if (!debouncedBusca) return true
      const hay = `${item.titulo} ${item.protocolo || ''}`.toLowerCase()
      return hay.includes(debouncedBusca)
    })
  }, [lista, tipoFiltro, faseFiltro, statusFiltro, debouncedBusca])

  async function enviarResposta() {
    if (!detalhe || !resposta.trim()) return
    setEnviando(true)
    try {
      const atualizado = await solicitacoesMelhoria.comentar(detalhe.id, {
        corpo: resposta.trim(),
        publico_cliente: true,
      })
      setDetalhe(atualizado)
      setResposta('')
      toast.showSuccess('Resposta enviada')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar'))
    } finally {
      setEnviando(false)
    }
  }

  const podeResponder =
    detalhe &&
    !STATUS_FINAIS.has(detalhe.status) &&
    detalhe.autor_atendente_id === user?.id

  if (id) {
    if (loadingDetalhe && !detalhe) {
      return (
        <PageContainer>
          <PageLoading label="Abrindo solicitação…" />
        </PageContainer>
      )
    }

    if (!detalhe) {
      return (
        <PageContainer>
          <VoltarButton onClick={() => navigate('/minhas-solicitacoes')} label="Voltar à lista" />
          <p className="text-sm text-slate-500">Não foi possível carregar este pedido.</p>
        </PageContainer>
      )
    }

    return (
      <PageContainer>
        <PageHeader
          title={`${detalhe.protocolo || 'Pedido'} · ${detalhe.titulo}`}
          subtitle={
            <SolicitacoesMelhoriaBadges
              tipo={detalhe.tipo}
              status={detalhe.status}
              statusRotulo={detalhe.status_rotulo}
            />
          }
        />
        <VoltarButton onClick={() => navigate('/minhas-solicitacoes')} label="Voltar à lista" />

        <Card className="space-y-3 p-5">
          <SolicitacaoDescricao descricao={detalhe.descricao} anexos={detalhe.anexos} />
          <p className={classesCardMensagemStatus(detalhe.status)}>{detalhe.mensagem_status}</p>
          {detalhe.versao_alvo_rotulo ? (
            <p className="rounded-lg bg-emerald-50 p-3 text-sm font-medium text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100">
              {detalhe.versao_alvo_rotulo}
            </p>
          ) : null}
          {detalhe.status === 'nao_sera_desenvolvida' && detalhe.motivo_nao_desenvolvimento ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-100">
              <span className="font-medium">Motivo: </span>
              {detalhe.motivo_nao_desenvolvimento}
            </p>
          ) : null}
        </Card>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Acompanhamento</h2>
          <SolicitacoesMelhoriaTimeline historico={detalhe.historico} comentarios={detalhe.comentarios} />
        </section>

        {podeResponder ? (
          <Card className="space-y-3 p-5">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Responder</label>
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={3}
              value={resposta}
              onChange={(e) => setResposta(e.target.value)}
              placeholder="Escreva uma mensagem para a equipe…"
            />
            <Button type="button" variant="primary" loading={enviando} onClick={() => void enviarResposta()}>
              Enviar resposta
            </Button>
          </Card>
        ) : STATUS_FINAIS.has(detalhe.status) ? (
          <p className="text-sm text-slate-500">Este pedido está encerrado e não aceita mais respostas.</p>
        ) : null}
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Minhas solicitações"
        subtitle="Acompanhe sugestões e problemas enviados a partir das notas de versão."
        actions={
          <Button type="button" variant="primary" onClick={() => navigate('/sobre/nova-solicitacao')}>
            Novo pedido
          </Button>
        }
      />
      <div className="flex flex-wrap gap-3 text-sm">
        <Link to="/sobre" className="text-cyan-700 hover:underline dark:text-cyan-400">
          ← Sobre / Release Notes
        </Link>
      </div>
      {loading ? (
        <PageLoading label="Carregando solicitações…" />
      ) : lista.length === 0 ? (
        <Card className="p-8 text-center text-sm text-slate-500">
          Você ainda não enviou nenhum pedido.{' '}
          <Link to="/sobre/nova-solicitacao" className="text-cyan-700 underline dark:text-cyan-400">
            Enviar sugestão
          </Link>
          {' '}ou ver{' '}
          <Link to="/sobre" className="text-cyan-700 underline dark:text-cyan-400">
            Sobre
          </Link>
          .
        </Card>
      ) : (
        <div className="space-y-4">
          <Card>
            <div className="space-y-4">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Tipo
                </p>
                <div className="flex flex-wrap gap-2">
                  <FiltroChip active={!tipoFiltro} count={resumo.total} onClick={() => patchFiltros({ tipo: null })}>
                    Todos
                  </FiltroChip>
                  <FiltroChip
                    active={tipoFiltro === 'sugestao'}
                    count={resumo.sugestoes}
                    tone="sky"
                    onClick={() => patchFiltros({ tipo: tipoFiltro === 'sugestao' ? null : 'sugestao' })}
                  >
                    Sugestões
                  </FiltroChip>
                  <FiltroChip
                    active={tipoFiltro === 'problema'}
                    count={resumo.problemas}
                    tone="rose"
                    onClick={() => patchFiltros({ tipo: tipoFiltro === 'problema' ? null : 'problema' })}
                  >
                    Problemas
                  </FiltroChip>
                </div>
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Fase
                </p>
                <div className="flex flex-wrap gap-2">
                  <FiltroChip active={!faseFiltro} onClick={() => patchFiltros({ fase: null })}>
                    Todas
                  </FiltroChip>
                  {SAAS_SOLICITACAO_FASES.map((f) => (
                    <FiltroChip
                      key={f.value}
                      active={faseFiltro === f.value}
                      count={
                        f.value === 'aguardando'
                          ? resumo.aguardando
                          : f.value === 'desenvolvimento'
                            ? resumo.desenvolvimento
                            : resumo.finalizadas
                      }
                      onClick={() => patchFiltros({ fase: faseFiltro === f.value ? null : f.value })}
                    >
                      {f.label}
                    </FiltroChip>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Status
                </p>
                <div className="flex flex-wrap gap-2">
                  <FiltroChip active={!statusFiltro} onClick={() => patchFiltros({ status: null })}>
                    Todos
                  </FiltroChip>
                  {SAAS_SOLICITACAO_STATUS.map((s) => (
                    <FiltroChip
                      key={s.value}
                      active={statusFiltro === s.value}
                      count={lista.filter((i) => i.status === s.value).length}
                      onClick={() => patchFiltros({ status: statusFiltro === s.value ? null : s.value })}
                    >
                      {s.label}
                    </FiltroChip>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="busca-solicitacoes" className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Buscar
                </label>
                <input
                  id="busca-solicitacoes"
                  type="search"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  placeholder="Título ou protocolo…"
                  className={INPUT_FIELD_CLASS}
                />
              </div>
            </div>
          </Card>

          {listaFiltrada.length === 0 ? (
            <Card className="p-6 text-center text-sm text-slate-500">
              Nenhum pedido corresponde aos filtros atuais.{' '}
              <button
                type="button"
                className="text-cyan-700 underline dark:text-cyan-400"
                onClick={() => {
                  setBusca('')
                  patchFiltros({ tipo: null, fase: null, status: null })
                }}
              >
                Limpar filtros
              </button>
            </Card>
          ) : (
            <Card bodyClassName="overflow-x-auto p-0">
              <p className="border-b border-slate-100 px-6 py-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                {listaFiltrada.length === lista.length
                  ? `${lista.length} pedido${lista.length === 1 ? '' : 's'}`
                  : `${listaFiltrada.length} de ${lista.length} pedidos`}
              </p>
              <SolicitacoesMelhoriaListaTable
                items={listaFiltrada}
                itemPath={(solicitacaoId) => `/minhas-solicitacoes/${solicitacaoId}`}
              />
            </Card>
          )}
        </div>
      )}
    </PageContainer>
  )
}
