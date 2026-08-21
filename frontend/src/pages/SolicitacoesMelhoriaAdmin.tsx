import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { solicitacoesMelhoria, type SolicitacoesMelhoria } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'

const STATUS_OPTS = [
  { value: '', label: 'Todos os status' },
  { value: 'aberta', label: 'Recebida' },
  { value: 'em_analise', label: 'Em análise' },
  { value: 'planejada', label: 'Planejada' },
  { value: 'em_desenvolvimento', label: 'Em desenvolvimento' },
  { value: 'concluida', label: 'Concluída' },
  { value: 'nao_sera_desenvolvida', label: 'Não será desenvolvida' },
]

function fmt(dt: string): string {
  try {
    return new Date(dt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return dt
  }
}

/** Painel admin de triagem (#804) + GitHub (#805/#806). */
export function SolicitacoesMelhoriaAdminPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [lista, setLista] = useState<SolicitacoesMelhoria.ListaItem[]>([])
  const [detalhe, setDetalhe] = useState<SolicitacoesMelhoria.Detalhe | null>(null)
  const [filtroStatus, setFiltroStatus] = useState('')
  const [filtroTipo, setFiltroTipo] = useState('')
  const [filtroOrg, setFiltroOrg] = useState('')
  const [desde, setDesde] = useState('')
  const [ate, setAte] = useState('')
  const [novoStatus, setNovoStatus] = useState<SolicitacoesMelhoria.Status>('em_analise')
  const [motivo, setMotivo] = useState('')
  const [comentario, setComentario] = useState('')
  const [publico, setPublico] = useState(true)
  const [busy, setBusy] = useState(false)

  const carregarLista = useCallback(() => {
    return solicitacoesMelhoria
      .adminLista({
        status: filtroStatus || undefined,
        tipo: filtroTipo || undefined,
        organizacao_id: filtroOrg ? Number(filtroOrg) : undefined,
        desde: desde || undefined,
        ate: ate || undefined,
      })
      .then(setLista)
      .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Falha ao listar')))
  }, [filtroStatus, filtroTipo, filtroOrg, desde, ate, toast])

  useEffect(() => {
    void carregarLista()
  }, [carregarLista])

  useEffect(() => {
    if (!id) {
      setDetalhe(null)
      return
    }
    void solicitacoesMelhoria
      .get(Number(id))
      .then((d) => {
        setDetalhe(d)
        setNovoStatus(d.status as SolicitacoesMelhoria.Status)
        setMotivo(d.motivo_nao_desenvolvimento || '')
      })
      .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Falha ao abrir')))
  }, [id, toast])

  async function salvarStatus() {
    if (!detalhe) return
    setBusy(true)
    try {
      const atualizado = await solicitacoesMelhoria.alterarStatus(detalhe.id, {
        status: novoStatus,
        motivo_nao_desenvolvimento:
          novoStatus === 'nao_sera_desenvolvida' ? motivo.trim() || null : undefined,
      })
      setDetalhe(atualizado)
      toast.showSuccess('Status atualizado')
      void carregarLista()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar o status'))
    } finally {
      setBusy(false)
    }
  }

  async function enviarComentario() {
    if (!detalhe || !comentario.trim()) return
    setBusy(true)
    try {
      const atualizado = await solicitacoesMelhoria.comentar(detalhe.id, {
        corpo: comentario.trim(),
        publico_cliente: publico,
      })
      setDetalhe(atualizado)
      setComentario('')
      toast.showSuccess(publico ? 'Resposta pública enviada' : 'Nota interna registada')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao comentar'))
    } finally {
      setBusy(false)
    }
  }

  async function criarGithub() {
    if (!detalhe) return
    setBusy(true)
    try {
      const atualizado = await solicitacoesMelhoria.criarGithub(detalhe.id)
      setDetalhe(atualizado)
      toast.showSuccess('Issue criada no GitHub')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao criar issue (pode tentar de novo)'))
      const refreshed = await solicitacoesMelhoria.get(detalhe.id).catch(() => null)
      if (refreshed) setDetalhe(refreshed)
    } finally {
      setBusy(false)
    }
  }

  async function syncGithub() {
    if (!detalhe) return
    setBusy(true)
    try {
      const atualizado = await solicitacoesMelhoria.syncGithub(detalhe.id)
      setDetalhe(atualizado)
      toast.showSuccess('Sincronização GitHub concluída (nota interna)')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao sincronizar'))
    } finally {
      setBusy(false)
    }
  }

  if (id && detalhe) {
    return (
      <PageContainer>
        <PageHeader title={`#${detalhe.id} · ${detalhe.titulo}`} subtitle="Triagem interna" />
        <button
          type="button"
          className="text-sm text-cyan-700 hover:underline dark:text-cyan-400"
          onClick={() => navigate('/solicitacoes-melhoria')}
        >
          ← Voltar à lista
        </button>

        <Card className="space-y-2 p-5 text-sm">
          <p>
            <span className="text-slate-500">Autor:</span> {detalhe.autor_nome || '—'} · org {detalhe.organizacao_id}
          </p>
          <p>
            <span className="text-slate-500">Tipo:</span> {detalhe.tipo} ·{' '}
            <span className="text-slate-500">Status:</span> {detalhe.status_rotulo}
          </p>
          <p className="whitespace-pre-wrap text-slate-800 dark:text-slate-100">{detalhe.descricao}</p>
          {detalhe.github_issue_url ? (
            <p>
              GitHub:{' '}
              <a href={detalhe.github_issue_url} className="text-cyan-700 underline" target="_blank" rel="noreferrer">
                #{detalhe.github_issue_number}
              </a>
            </p>
          ) : null}
          {detalhe.github_last_error ? (
            <p className="text-rose-600 dark:text-rose-400">Último erro GitHub: {detalhe.github_last_error}</p>
          ) : null}
        </Card>

        <Card className="space-y-3 p-5">
          <h2 className="font-semibold">Alterar status</h2>
          <Select
            value={novoStatus}
            onChange={(v) => setNovoStatus(String(v) as SolicitacoesMelhoria.Status)}
            options={STATUS_OPTS.filter((o) => o.value !== '') as { value: string; label: string }[]}
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
        </Card>

        <Card className="space-y-3 p-5">
          <h2 className="font-semibold">Resposta / nota</h2>
          <textarea
            className={TEXTAREA_FIELD_CLASS}
            rows={3}
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            placeholder="Mensagem…"
          />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publico} onChange={(e) => setPublico(e.target.checked)} />
            Visível para o cliente
          </label>
          <Button type="button" variant="primary" loading={busy} onClick={() => void enviarComentario()}>
            Enviar
          </Button>
        </Card>

        <Card className="flex flex-wrap gap-2 p-5">
          <Button type="button" variant="ghost" loading={busy} onClick={() => void criarGithub()} disabled={!!detalhe.github_issue_number}>
            Criar issue no GitHub
          </Button>
          <Button type="button" variant="ghost" loading={busy} onClick={() => void syncGithub()} disabled={!detalhe.github_issue_number}>
            Sincronizar GitHub
          </Button>
        </Card>

        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-slate-500">Timeline</h2>
          {detalhe.historico.map((h) => (
            <Card key={`h-${h.id}`} className="p-3 text-sm">
              <p className="font-medium">
                {h.status_novo_rotulo}
                {h.atendente_nome ? ` · ${h.atendente_nome}` : ''}
              </p>
              {h.mensagem_publica ? <p className="mt-1 whitespace-pre-wrap">{h.mensagem_publica}</p> : null}
              <p className="text-xs text-slate-400">{fmt(h.created_at)}</p>
            </Card>
          ))}
          {detalhe.comentarios.map((c) => (
            <Card key={`c-${c.id}`} className="p-3 text-sm">
              <p className="text-xs text-slate-500">
                {c.publico_cliente ? 'Público' : 'Interno'} · {c.autor_nome || '—'} · {fmt(c.created_at)}
                {c.origem === 'github' ? ' · GitHub' : ''}
              </p>
              <p className="mt-1 whitespace-pre-wrap">{c.corpo}</p>
            </Card>
          ))}
        </section>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader title="Sugestões de clientes" subtitle="Triagem de pedidos vindos das notas de versão." />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Select
          value={filtroStatus}
          onChange={(v) => setFiltroStatus(String(v))}
          options={[
            { value: 'aberta', label: 'Recebida' },
            { value: 'em_analise', label: 'Em análise' },
            { value: 'planejada', label: 'Planejada' },
            { value: 'em_desenvolvimento', label: 'Em desenvolvimento' },
            { value: 'concluida', label: 'Concluída' },
            { value: 'nao_sera_desenvolvida', label: 'Não será desenvolvida' },
          ]}
          includeEmpty
          emptyLabel="Todos os status"
        />
        <Select
          value={filtroTipo}
          onChange={(v) => setFiltroTipo(String(v))}
          options={[
            { value: 'sugestao', label: 'Sugestão' },
            { value: 'problema', label: 'Problema' },
          ]}
          includeEmpty
          emptyLabel="Todos os tipos"
        />
        <Input value={filtroOrg} onChange={(e) => setFiltroOrg(e.target.value)} placeholder="Org / tenant id" />
        <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} aria-label="Desde" />
        <Input type="date" value={ate} onChange={(e) => setAte(e.target.value)} aria-label="Até" />
      </div>
      <div className="space-y-2">
        {lista.map((item) => (
          <Link key={item.id} to={`/solicitacoes-melhoria/${item.id}`} className="block">
            <Card className="p-4 hover:ring-1 hover:ring-cyan-400/40">
              <div className="flex flex-wrap justify-between gap-2">
                <h3 className="font-semibold">
                  #{item.id} {item.titulo}
                </h3>
                <span className="text-xs">{item.status_rotulo}</span>
              </div>
              <p className="text-xs text-slate-500">
                {item.autor_nome} · org {item.organizacao_id} · {fmt(item.created_at)}
                {item.github_issue_number ? ` · GH #${item.github_issue_number}` : ''}
              </p>
            </Card>
          </Link>
        ))}
        {lista.length === 0 ? <p className="text-sm text-slate-500">Nenhuma solicitação com estes filtros.</p> : null}
      </div>
    </PageContainer>
  )
}
