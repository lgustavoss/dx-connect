import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasSolicitacoes, type SaasSolicitacoesProduto } from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { Input, TEXTAREA_FIELD_CLASS } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { VoltarButton } from '../../components/ui/VoltarButton'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SolicitacaoDescricao } from '../../components/release/SolicitacaoDescricao'
import {
  classesBadgeStatusSolicitacao,
  classesBadgeTipoSolicitacao,
  mencionaTrabalhoInterno,
  podeAvancarStatus,
  proximosStatusSolicitacao,
  rotuloStatusSolicitacao,
  rotuloTipoSolicitacao,
  rotuloVersaoAlvo,
  SAAS_SOLICITACAO_STATUS,
} from '../../lib/saasSolicitacoes'
import { SemPermissao } from '../SemPermissao'

const STATUS_REJEITAR = SAAS_SOLICITACAO_STATUS.find((s) => s.value === 'nao_sera_desenvolvida')!

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function StatusBadge({ status, rotulo }: { status: string; rotulo?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeStatusSolicitacao(status)}`}
    >
      {rotulo || rotuloStatusSolicitacao(status)}
    </span>
  )
}

export function SaasSolicitacaoDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/saas/solicitacoes')
  const solicitacaoId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [item, setItem] = useState<SaasSolicitacoesProduto.Detalhe | null>(null)
  const [novoStatus, setNovoStatus] = useState('em_analise')
  const [motivo, setMotivo] = useState('')
  const [comentario, setComentario] = useState('')
  const [tipoMensagem, setTipoMensagem] = useState<'publico' | 'interno'>('publico')
  const [buscaIgual, setBuscaIgual] = useState('')
  const [candidatos, setCandidatos] = useState<SaasSolicitacoesProduto.ListaItem[]>([])
  const [githubUrl, setGithubUrl] = useState('')
  const [mostrarImplementar, setMostrarImplementar] = useState(false)

  const aplicarDetalhe = useCallback((row: SaasSolicitacoesProduto.Detalhe) => {
    setItem(row)
    setNovoStatus(row.status)
    setMotivo(row.motivo_nao_desenvolvimento || '')
  }, [])

  useEffect(() => {
    if (!id || Number.isNaN(solicitacaoId)) {
      setFalha({ titulo: 'Solicitação não encontrada.', detalhe: 'Identificador inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    saasSolicitacoes
      .get(solicitacaoId)
      .then((row) => {
        if (cancelled) return
        aplicarDetalhe(row)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          const detail =
            typeof err.body === 'object' && err.body && 'detail' in err.body
              ? String((err.body as { detail?: unknown }).detail ?? '')
              : ''
          if (detail.toLowerCase().includes('não disponível')) setIndisponivel(true)
          else setFalha(interpretarFalhaCarregamento(err, 'Solicitação não encontrada.'))
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível abrir a solicitação.'))
        setFalha(interpretarFalhaCarregamento(err, 'Não foi possível abrir a solicitação.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, solicitacaoId, toast, aplicarDetalhe])

  useEffect(() => {
    const q = buscaIgual.trim()
    if (q.length < 2 || !item) {
      setCandidatos([])
      return
    }
    const t = setTimeout(() => {
      void saasSolicitacoes
        .list({ busca: q, limit: 8 })
        .then(({ items }) => {
          const ja = new Set((item.grupo || []).map((m) => m.id))
          ja.add(item.id)
          setCandidatos(items.filter((c) => !ja.has(c.id)))
        })
        .catch(() => setCandidatos([]))
    }, 350)
    return () => clearTimeout(t)
  }, [buscaIgual, item])

  async function persistirStatus(status: string, motivoTexto?: string) {
    if (!item) return
    setBusy(true)
    try {
      const atualizado = await saasSolicitacoes.alterarStatus(item.id, {
        status,
        motivo_nao_desenvolvimento:
          status === 'nao_sera_desenvolvida' ? motivoTexto?.trim() || null : undefined,
      })
      aplicarDetalhe(atualizado)
      toast.showSuccess('Status atualizado. O cliente vê o andamento em Minhas solicitações.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar o status'))
    } finally {
      setBusy(false)
    }
  }

  async function escolherStatus(status: string) {
    setNovoStatus(status)
    if (status === 'nao_sera_desenvolvida') return
    if (item && status === item.status) return
    if (status === 'em_desenvolvimento') {
      setMostrarImplementar(true)
      return
    }
    if (item && !podeAvancarStatus(item.status, status)) {
      toast.showError('Essa transição de status não é permitida. Avance passo a passo.')
      setNovoStatus(item.status)
      return
    }
    await persistirStatus(status)
  }

  async function confirmarRejeicao() {
    if (!motivo.trim()) {
      toast.showError('Informe um motivo amigável para o cliente.')
      return
    }
    await persistirStatus('nao_sera_desenvolvida', motivo)
  }

  async function confirmarImplementar(opts: { criarIssue: boolean; url?: string }) {
    if (!item) return
    setBusy(true)
    try {
      const data: SaasSolicitacoesProduto.Implementar = {
        criar_issue: opts.criarIssue,
      }
      const url = (opts.url ?? githubUrl).trim()
      if (url) {
        data.github_issue_url = url
        data.criar_issue = false
      } else if (item.github_issue_url) {
        data.criar_issue = false
      }
      const atualizado = await saasSolicitacoes.implementar(item.id, data)
      aplicarDetalhe(atualizado)
      setMostrarImplementar(false)
      setGithubUrl('')
      toast.showSuccess('Em desenvolvimento. Issue ligada — o cliente não vê o GitHub.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível implementar'))
    } finally {
      setBusy(false)
    }
  }

  async function enviarComentario() {
    if (!item || !comentario.trim()) return
    const publico = tipoMensagem === 'publico'
    if (publico && mencionaTrabalhoInterno(comentario)) {
      toast.showError(
        'Não envie links ou números de issue do GitHub na mensagem ao cliente. Use comentário interno.',
      )
      return
    }
    setBusy(true)
    try {
      const atualizado = await saasSolicitacoes.comentar(item.id, {
        corpo: comentario.trim(),
        publico_cliente: publico,
      })
      aplicarDetalhe(atualizado)
      setComentario('')
      toast.showSuccess(publico ? 'Resposta pública enviada ao cliente' : 'Nota interna registada (só neste painel)')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao comentar'))
    } finally {
      setBusy(false)
    }
  }

  async function vincularPedido(alvo: { id?: number; protocolo?: string | null }) {
    if (!item) return
    setBusy(true)
    try {
      const atualizado = await saasSolicitacoes.vincular(
        item.id,
        alvo.protocolo ? { protocolo: alvo.protocolo } : { solicitacao_id: alvo.id },
      )
      aplicarDetalhe(atualizado)
      setBuscaIgual('')
      setCandidatos([])
      toast.showSuccess('Pedidos ligados. O cliente não vê este grupo.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível vincular'))
    } finally {
      setBusy(false)
    }
  }

  async function desvincularPedido(membroId: number) {
    if (!item) return
    setBusy(true)
    try {
      const atualizado = await saasSolicitacoes.desvincular(item.id, membroId)
      aplicarDetalhe(atualizado)
      toast.showSuccess('Pedido saiu do grupo.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível desvincular'))
    } finally {
      setBusy(false)
    }
  }

  async function copiarDemandaGithub() {
    if (!item?.texto_github_demanda) return
    try {
      await navigator.clipboard.writeText(item.texto_github_demanda)
      toast.showSuccess('Texto copiado para colar na issue.')
    } catch {
      toast.showError('Não foi possível copiar.')
    }
  }

  if (loading) {
    return (
      <div className="mx-auto w-full min-w-0 max-w-6xl space-y-6 pb-10">
        <div className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }
  if (indisponivel) {
    return (
      <SemPermissao
        title="Fila de sugestões não disponível nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }
  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver esta solicitação."
        voltarPara="/saas/solicitacoes"
        voltarLabel="Voltar para a fila"
      />
    )
  }
  if (falha) {
    return <CarregamentoFalhou titulo={falha.titulo} detalhe={falha.detalhe} onVoltar={voltarAnterior} />
  }
  if (!item) return null

  const comentarios = [...(item.comentarios || [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  )
  const rejeitarPendente = novoStatus === 'nao_sera_desenvolvida' && item.status !== 'nao_sera_desenvolvida'
  const internoActivo = tipoMensagem === 'interno'
  const proximos = new Set(proximosStatusSolicitacao(item.status))
  const statusFluxo = SAAS_SOLICITACAO_STATUS.filter((s) => s.value !== 'nao_sera_desenvolvida')
  const podeRejeitar = proximos.has('nao_sera_desenvolvida') || item.status === 'nao_sera_desenvolvida'
  const podeImplementar = item.status === 'planejada'
  const rotuloVersaoCliente = rotuloVersaoAlvo(item.status, item.versao_alvo)

  return (
    <div className="mx-auto w-full min-w-0 max-w-6xl space-y-6 pb-10">
      <VoltarButton onClick={voltarAnterior} />

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-mono text-xs font-semibold tracking-wide text-slate-500 dark:text-slate-400">
              {item.protocolo || 'Sem protocolo'}
            </p>
            <span className="text-slate-300 dark:text-slate-600">·</span>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classesBadgeTipoSolicitacao(item.tipo)}`}
            >
              {rotuloTipoSolicitacao(item.tipo)}
            </span>
            <StatusBadge status={item.status} rotulo={item.status_rotulo} />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{item.titulo}</h1>
          <p className="text-sm text-slate-500">
            {item.cliente_nome || item.instance_slug}
            {item.autor_nome ? ` · ${item.autor_nome}` : ''}
            {item.versao_contexto ? ` · v${item.versao_contexto}` : ''}
            {(item.peso_clientes || 1) > 1 ? ` · ${item.peso_clientes} clientes pediram o mesmo` : ''}
          </p>
        </div>
        {item.cliente_saas_id ? (
          <Button variant="secondary" onClick={() => navigate(`/saas/licencas/${item.cliente_saas_id}`)}>
            Abrir licença
          </Button>
        ) : null}
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_21rem] xl:items-start">
        <aside className="space-y-6 xl:col-start-2 xl:row-start-1">
          <Card title="Status" description="O cliente vê este andamento em Minhas solicitações. Só avanços permitidos.">
            <nav className="space-y-1.5" aria-label="Status da triagem">
              {statusFluxo.map((s) => {
                const activo = novoStatus === s.value || (mostrarImplementar && s.value === 'em_desenvolvimento')
                const atual = item.status === s.value
                const permitido =
                  atual ||
                  proximos.has(s.value) ||
                  (s.value === 'em_desenvolvimento' && podeImplementar)
                return (
                  <button
                    key={s.value}
                    type="button"
                    disabled={busy || (!permitido && !atual)}
                    onClick={() => void escolherStatus(s.value)}
                    className={`flex w-full items-center gap-2.5 rounded-xl border px-3 py-2 text-left text-sm transition disabled:cursor-not-allowed disabled:opacity-45 ${
                      activo
                        ? 'border-cyan-300 bg-cyan-50/90 ring-1 ring-cyan-400/25 dark:border-cyan-700/60 dark:bg-cyan-950/35 dark:ring-cyan-600/30'
                        : 'border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <span
                      className={`size-2 shrink-0 rounded-full ${activo ? 'bg-cyan-500' : 'bg-slate-300 dark:bg-slate-600'}`}
                    />
                    <span className={`min-w-0 flex-1 font-medium ${activo ? 'text-slate-900 dark:text-slate-50' : 'text-slate-700 dark:text-slate-200'}`}>
                      {s.label}
                    </span>
                    {atual ? (
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-cyan-700 dark:text-cyan-300">
                        atual
                      </span>
                    ) : null}
                  </button>
                )
              })}
              <div className="my-2 border-t border-slate-100 dark:border-slate-800" />
              <button
                type="button"
                disabled={busy || !podeRejeitar}
                onClick={() => void escolherStatus(STATUS_REJEITAR.value)}
                className={`flex w-full items-center gap-2.5 rounded-xl border px-3 py-2 text-left text-sm transition disabled:cursor-not-allowed disabled:opacity-45 ${
                  novoStatus === STATUS_REJEITAR.value
                    ? 'border-rose-300 bg-rose-50/90 ring-1 ring-rose-400/25 dark:border-rose-800/60 dark:bg-rose-950/35 dark:ring-rose-700/30'
                    : 'border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:bg-slate-800/50'
                }`}
              >
                <span
                  className={`size-2 shrink-0 rounded-full ${novoStatus === STATUS_REJEITAR.value ? 'bg-rose-500' : 'bg-slate-300 dark:bg-slate-600'}`}
                />
                <span className="min-w-0 flex-1 font-medium text-slate-700 dark:text-slate-200">
                  {STATUS_REJEITAR.label}
                </span>
                {item.status === STATUS_REJEITAR.value ? (
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-rose-700 dark:text-rose-300">
                    atual
                  </span>
                ) : null}
              </button>
            </nav>
            {mostrarImplementar || (podeImplementar && novoStatus === 'em_desenvolvimento') ? (
              <div className="mt-3 space-y-2 rounded-xl border border-cyan-200 bg-cyan-50/50 p-3 dark:border-cyan-800/50 dark:bg-cyan-950/30">
                <p className="text-xs font-medium text-cyan-900 dark:text-cyan-100">
                  Implementar exige issue no GitHub (o cliente não vê o link).
                </p>
                {item.github_issue_url ? (
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    Já ligada:{' '}
                    <a
                      href={item.github_issue_url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-cyan-700 underline dark:text-cyan-400"
                    >
                      #{item.github_issue_number}
                    </a>
                  </p>
                ) : (
                  <Input
                    label="URL da issue (opcional)"
                    placeholder="https://github.com/org/repo/issues/123"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                  />
                )}
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="primary"
                    loading={busy}
                    onClick={() =>
                      void confirmarImplementar({
                        criarIssue: !item.github_issue_url && !githubUrl.trim(),
                        url: githubUrl,
                      })
                    }
                  >
                    {item.github_issue_url || githubUrl.trim()
                      ? 'Ligar e implementar'
                      : 'Criar issue e implementar'}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => {
                      setMostrarImplementar(false)
                      setNovoStatus(item.status)
                    }}
                  >
                    Cancelar
                  </Button>
                </div>
              </div>
            ) : null}
            {novoStatus === 'nao_sera_desenvolvida' ? (
              <div className="mt-3 space-y-2">
                <textarea
                  className={TEXTAREA_FIELD_CLASS}
                  rows={3}
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  placeholder="Motivo amigável para o cliente (obrigatório)"
                />
                <Button type="button" variant="primary" loading={busy} onClick={() => void confirmarRejeicao()}>
                  {rejeitarPendente ? 'Salvar e informar o cliente' : 'Atualizar motivo'}
                </Button>
              </div>
            ) : null}
            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
              Aberto {formatWhen(item.created_at_origem)} · no SaaS {formatWhen(item.ingested_at)}
            </p>
          </Card>

          {rotuloVersaoCliente ? (
            <Card
              title="Versão liberada"
              description="O cliente vê em Minhas solicitações quando o pedido está concluído."
            >
              <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">{rotuloVersaoCliente}</p>
            </Card>
          ) : null}

          {item.github_issue_url && !mostrarImplementar ? (
            <Card title="Issue no GitHub" description="Só neste painel — o cliente não vê o link.">
              <a
                href={item.github_issue_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-400"
              >
                {item.github_issue_number ? `#${item.github_issue_number}` : item.github_issue_url}
              </a>
            </Card>
          ) : null}

          <Card title="Pedidos iguais" description="Só neste painel. O cliente não vê quem mais pediu o mesmo.">
            {(item.grupo || []).length > 1 ? (
              <ul className="space-y-2">
                {(item.grupo || []).map((m) => (
                  <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <button
                      type="button"
                      className="text-left font-medium text-cyan-800 hover:underline dark:text-cyan-300"
                      onClick={() => navigate(`/saas/solicitacoes/${m.id}`)}
                    >
                      <span className="font-mono">{m.protocolo || `#${m.id}`}</span>
                      {' · '}
                      {m.cliente_nome || m.instance_slug}
                    </button>
                    {m.id !== item.id ? (
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => void desvincularPedido(m.id)}
                      >
                        Desvincular
                      </Button>
                    ) : (
                      <span className="text-xs text-slate-400">este pedido</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">Ainda não está ligado a outros pedidos.</p>
            )}
            {item.texto_github_demanda ? (
              <div className="mt-3 space-y-2">
                <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
                  {item.texto_github_demanda}
                </pre>
                <Button type="button" variant="secondary" onClick={() => void copiarDemandaGithub()}>
                  Copiar para a issue
                </Button>
              </div>
            ) : null}
            <div className="mt-4 space-y-2">
              <Input
                label="Vincular outro pedido"
                placeholder="Protocolo, título ou cliente…"
                value={buscaIgual}
                onChange={(e) => setBuscaIgual(e.target.value)}
              />
              {candidatos.length > 0 ? (
                <ul className="space-y-1">
                  {candidatos.map((c) => (
                    <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                      <span>
                        <span className="font-mono text-cyan-800 dark:text-cyan-300">{c.protocolo || `#${c.id}`}</span>
                        {' · '}
                        {c.cliente_nome || c.instance_slug} — {c.titulo}
                      </span>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => void vincularPedido({ id: c.id, protocolo: c.protocolo })}
                      >
                        Vincular
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </Card>
        </aside>

        <div className="space-y-4 xl:col-start-1 xl:row-start-1">
          <Card
            title="Linha do tempo"
            description="O pedido e o que o cliente vê. Notas internas ficam só neste painel (cartão âmbar)."
          >
            <ol className="relative space-y-4 border-l border-slate-200 pl-5 dark:border-slate-700">
              <li className="relative">
                <span className="absolute -left-[1.45rem] mt-1.5 size-2.5 rounded-full bg-slate-400 ring-4 ring-white dark:bg-slate-500 dark:ring-slate-900" />
                <div className="rounded-xl border border-slate-200 border-l-4 border-l-slate-500 bg-slate-50/90 px-4 py-3 text-sm dark:border-slate-600 dark:border-l-slate-400 dark:bg-slate-800/50">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/70 pb-2 text-xs dark:border-slate-600/80">
                    <span className="font-semibold text-slate-800 dark:text-slate-100">Pedido do cliente</span>
                    <span className="text-slate-500 dark:text-slate-400">{formatWhen(item.created_at_origem)}</span>
                  </div>
                  <div className="mt-3">
                    <SolicitacaoDescricao descricao={item.descricao} anexos={item.anexos} />
                  </div>
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    {item.autor_nome || 'Cliente'}
                    {item.instance_slug ? ` · ${item.instance_slug}` : ''}
                  </p>
                </div>
              </li>

              {comentarios.map((c) => {
                const interno = !c.publico_cliente
                return (
                  <li key={c.id} className="relative">
                    <span
                      className={`absolute -left-[1.45rem] mt-1.5 size-2.5 rounded-full ring-4 ring-white dark:ring-slate-900 ${
                        interno ? 'bg-amber-500' : 'bg-cyan-500'
                      }`}
                    />
                    <div
                      className={`rounded-xl border px-4 py-3 text-sm ${
                        interno
                          ? 'border-amber-200/90 bg-amber-50/60 dark:border-amber-800/50 dark:bg-amber-950/25'
                          : 'border-slate-200/90 bg-white shadow-sm dark:border-slate-600 dark:bg-slate-800/45 dark:shadow-none'
                      }`}
                    >
                      <div
                        className={`flex flex-wrap items-center justify-between gap-2 border-b pb-2 text-xs ${
                          interno
                            ? 'border-amber-200/50 dark:border-amber-800/40'
                            : 'border-slate-200/60 dark:border-slate-600/80'
                        }`}
                      >
                        <span className="font-semibold text-slate-800 dark:text-slate-100">
                          {interno ? 'Nota interna' : 'Mensagem ao cliente'}
                        </span>
                        {interno ? (
                          <span className="rounded-md bg-amber-100/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-900 dark:bg-amber-900/50 dark:text-amber-100">
                            Só equipe
                          </span>
                        ) : (
                          <span className="rounded-md bg-cyan-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-100">
                            Visível ao cliente
                          </span>
                        )}
                      </div>
                      <p className="mt-2 whitespace-pre-wrap text-slate-800 dark:text-slate-200">{c.corpo}</p>
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        {c.autor_nome || '—'} · {formatWhen(c.created_at)}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>

            {comentarios.length === 0 ? (
              <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
                Ainda não há respostas. O que enviares como mensagem ao cliente aparece em Minhas solicitações.
              </p>
            ) : null}

            <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-800">
              <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Nova mensagem</p>
              <div className="mb-3 inline-flex rounded-xl bg-slate-100 p-1 ring-1 ring-slate-200/80 dark:bg-slate-800/90 dark:ring-slate-600/80">
                <button
                  type="button"
                  onClick={() => setTipoMensagem('publico')}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    tipoMensagem === 'publico'
                      ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100 dark:shadow-none dark:ring-1 dark:ring-slate-500/30'
                      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  Mensagem ao cliente
                </button>
                <button
                  type="button"
                  onClick={() => setTipoMensagem('interno')}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    internoActivo
                      ? 'bg-white text-amber-950 shadow-sm dark:bg-amber-950/55 dark:text-amber-100 dark:shadow-none dark:ring-1 dark:ring-amber-700/40'
                      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  Comentário interno
                </button>
              </div>
              <textarea
                className={`${TEXTAREA_FIELD_CLASS} ${
                  internoActivo
                    ? 'bg-amber-50 ring-amber-200/90 focus:ring-amber-400/30 dark:bg-amber-950/25 dark:ring-amber-800/60'
                    : ''
                }`}
                rows={4}
                value={comentario}
                onChange={(e) => setComentario(e.target.value)}
                placeholder={
                  internoActivo
                    ? 'Anotação visível apenas para a equipe ops…'
                    : 'Resposta que o cliente vê em Minhas solicitações…'
                }
              />
              {!internoActivo ? (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  O cliente lê isto. Não cite GitHub, número de issue nem acompanhamento interno.
                </p>
              ) : null}
              {tipoMensagem === 'publico' && mencionaTrabalhoInterno(comentario) ? (
                <p className="mt-2 text-sm text-rose-700 dark:text-rose-300">
                  Esta mensagem cita trabalho interno. Mude para comentário interno ou tire a issue/GitHub.
                </p>
              ) : null}
              <div className="mt-3 flex justify-end">
                <Button
                  type="button"
                  variant="primary"
                  loading={busy}
                  disabled={!comentario.trim() || (tipoMensagem === 'publico' && mencionaTrabalhoInterno(comentario))}
                  onClick={() => void enviarComentario()}
                >
                  Enviar
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
