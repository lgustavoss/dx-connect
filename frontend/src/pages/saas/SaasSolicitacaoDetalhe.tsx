import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasSolicitacoes, type SaasSolicitacoesProduto } from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { DetailRow } from '../../components/ui/DetailRow'
import { Input, TEXTAREA_FIELD_CLASS } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SolicitacaoDescricao } from '../../components/release/SolicitacaoDescricao'
import { SemPermissao } from '../SemPermissao'

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
  const [publico, setPublico] = useState(true)
  const [buscaIgual, setBuscaIgual] = useState('')
  const [candidatos, setCandidatos] = useState<SaasSolicitacoesProduto.ListaItem[]>([])

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

  async function salvarStatus() {
    if (!item) return
    setBusy(true)
    try {
      const atualizado = await saasSolicitacoes.alterarStatus(item.id, {
        status: novoStatus,
        motivo_nao_desenvolvimento:
          novoStatus === 'nao_sera_desenvolvida' ? motivo.trim() || null : undefined,
      })
      aplicarDetalhe(atualizado)
      toast.showSuccess('Status actualizado. O cliente vê o andamento em Minhas solicitações.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar o status'))
    } finally {
      setBusy(false)
    }
  }

  async function enviarComentario() {
    if (!item || !comentario.trim()) return
    setBusy(true)
    try {
      const atualizado = await saasSolicitacoes.comentar(item.id, {
        corpo: comentario.trim(),
        publico_cliente: publico,
      })
      aplicarDetalhe(atualizado)
      setComentario('')
      toast.showSuccess(publico ? 'Resposta pública enviada ao cliente' : 'Nota interna registada (só no SaaS)')
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
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
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

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <button
        type="button"
        onClick={voltarAnterior}
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
      >
        <span aria-hidden>←</span> Voltar
      </button>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {item.protocolo || 'Sem protocolo'} · {rotuloTipo(item.tipo)}
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{item.titulo}</h1>
          <p className="text-sm text-slate-500">
            {item.cliente_nome || item.instance_slug}
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

      <Card title="Pedido">
        <SolicitacaoDescricao descricao={item.descricao} anexos={item.anexos} />
        <dl className="mt-4">
          <DetailRow label="Protocolo" value={item.protocolo || '—'} mono />
          <DetailRow label="Cliente" value={item.cliente_nome || '—'} />
          <DetailRow label="Slug" value={item.instance_slug} mono />
          <DetailRow label="Autor" value={item.autor_nome || '—'} />
          <DetailRow label="Status" value={item.status_rotulo} />
          <DetailRow label="Versão" value={item.versao_contexto || '—'} />
          <DetailRow label="Aberto em" value={formatWhen(item.created_at_origem)} />
          <DetailRow label="Recebido no SaaS" value={formatWhen(item.ingested_at)} />
          <DetailRow
            label="Peso"
            value={
              (item.peso_clientes || 1) > 1
                ? `${item.peso_clientes} clientes · ${item.pedidos_grupo} pedidos`
                : '1 cliente'
            }
          />
        </dl>
      </Card>

      <Card title="Pedidos iguais">
        <p className="text-sm text-slate-500">
          Só neste painel. O cliente não vê quem mais pediu a mesma coisa. Na issue, cola o bloco de protocolos.
        </p>
        {(item.grupo || []).length > 1 ? (
          <ul className="mt-3 space-y-2">
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
          <p className="mt-2 text-sm text-slate-500">Ainda não está ligado a outros pedidos.</p>
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

      {item.github_issue_url ? (
        <Card title="Issue no GitHub">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Ligada pelo Cursor. Cole os protocolos do grupo no corpo da issue. O cliente não vê este link.
          </p>
          <a
            href={item.github_issue_url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-flex text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-400"
          >
            {item.github_issue_url}
          </a>
        </Card>
      ) : null}

      <Card title="Triagem">
        <div className="space-y-3">
          <Select
            value={novoStatus}
            onChange={(v) => setNovoStatus(String(v))}
            options={STATUS_OPTS}
          />
          {novoStatus === 'nao_sera_desenvolvida' ? (
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={3}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Motivo amigável para o cliente (obrigatório)"
            />
          ) : null}
          <Button type="button" variant="primary" loading={busy} onClick={() => void salvarStatus()}>
            Guardar status
          </Button>
        </div>
      </Card>

      <Card title="Resposta / nota">
        <div className="space-y-3">
          <textarea
            className={TEXTAREA_FIELD_CLASS}
            rows={3}
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            placeholder="Mensagem…"
          />
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={publico} onChange={(e) => setPublico(e.target.checked)} />
            Visível para o cliente (desmarque para nota interna — não sai deste painel)
          </label>
          <Button type="button" variant="primary" loading={busy} disabled={!comentario.trim()} onClick={() => void enviarComentario()}>
            Enviar
          </Button>
        </div>
      </Card>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-500">Comentários</h2>
        {(item.comentarios || []).map((c) => (
          <Card key={c.id} className="p-3 text-sm">
            <p className="text-xs text-slate-500">
              {c.publico_cliente ? 'Público' : 'Interno'} · {c.autor_nome || '—'} · {formatWhen(c.created_at)}
            </p>
            <p className="mt-1 whitespace-pre-wrap">{c.corpo}</p>
          </Card>
        ))}
        {(item.comentarios || []).length === 0 ? (
          <p className="text-sm text-slate-500">Ainda não há comentários nesta solicitação.</p>
        ) : null}
      </section>
    </div>
  )
}
