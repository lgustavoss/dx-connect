import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { preTicketIa, type PreTicketIa as PT } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'

const ESTADO_ROTULO: Record<string, string> = {
  rascunho: 'Rascunho',
  analisado: 'Analisado',
  aprovado: 'Aprovado (aguardando GitHub)',
  publicado: 'Publicado no GitHub',
  descartado: 'Descartado',
}

function fmt(dt: string | null | undefined): string {
  if (!dt) return '—'
  try {
    return new Date(dt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return dt
  }
}

/** Pré-ticket com IA (#810) — admin / dev analista. */
export function PreTicketIaPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [lista, setLista] = useState<PT.ListaItem[]>([])
  const [detalhe, setDetalhe] = useState<PT.Detalhe | null>(null)
  const [iaHabilitada, setIaHabilitada] = useState<boolean | null>(null)
  const [githubHabilitado, setGithubHabilitado] = useState<boolean | null>(null)
  const [historico, setHistorico] = useState<PT.HistoricoItem[]>([])
  const [metricas, setMetricas] = useState<PT.Metricas | null>(null)
  const [busy, setBusy] = useState(false)

  const [contexto, setContexto] = useState('')
  const [problema, setProblema] = useState('')
  const [impacto, setImpacto] = useState('')
  const [evidencias, setEvidencias] = useState('')
  const [urgencia, setUrgencia] = useState('')
  const [ticketId, setTicketId] = useState('')

  const [tituloEdit, setTituloEdit] = useState('')
  const [corpoEdit, setCorpoEdit] = useState('')

  const carregarLista = useCallback(() => {
    return preTicketIa.listar().then(setLista).catch((e) => toast.showError(mensagemFalhaParaToast(e)))
  }, [toast])

  const carregarDetalhe = useCallback(
    (sessaoId: number) => {
      return Promise.all([preTicketIa.get(sessaoId), preTicketIa.historico(sessaoId)])
        .then(([d, h]) => {
          setDetalhe(d)
          setHistorico(h)
          setTituloEdit(d.rascunho_titulo ?? '')
          setCorpoEdit(d.rascunho_corpo ?? '')
        })
        .catch((e) => toast.showError(mensagemFalhaParaToast(e)))
    },
    [toast],
  )

  useEffect(() => {
    preTicketIa
      .status()
      .then((s) => {
        setIaHabilitada(s.ia_habilitada)
        setGithubHabilitado(s.github_habilitado)
      })
      .catch(() => {
        setIaHabilitada(false)
        setGithubHabilitado(false)
      })
    preTicketIa.metricas().then(setMetricas).catch(() => setMetricas(null))
    carregarLista()
  }, [carregarLista])

  useEffect(() => {
    if (id) {
      const n = Number(id)
      if (Number.isFinite(n)) carregarDetalhe(n)
    } else {
      setDetalhe(null)
    }
  }, [id, carregarDetalhe])

  async function criarSessao() {
    setBusy(true)
    try {
      const row = await preTicketIa.criar({
        contexto: contexto.trim(),
        problema: problema.trim(),
        impacto: impacto.trim() || null,
        evidencias: evidencias.trim() || null,
        urgencia: urgencia.trim() || null,
        ticket_id: ticketId.trim() ? Number(ticketId) : null,
      })
      toast.showSuccess('Sessão criada. Analise com IA quando estiver pronto.')
      await carregarLista()
      navigate(`/pre-ticket-ia/${row.id}`)
    } catch (e) {
      toast.showError(mensagemFalhaParaToast(e))
    } finally {
      setBusy(false)
    }
  }

  async function analisar() {
    if (!detalhe) return
    setBusy(true)
    try {
      const d = await preTicketIa.analisar(detalhe.id)
      setDetalhe(d)
      setTituloEdit(d.rascunho_titulo ?? '')
      setCorpoEdit(d.rascunho_corpo ?? '')
      toast.showSuccess('Análise concluída.')
      await carregarLista()
      preTicketIa.metricas().then(setMetricas).catch(() => undefined)
    } catch (e) {
      toast.showError(mensagemFalhaParaToast(e))
    } finally {
      setBusy(false)
    }
  }

  async function salvarRascunho() {
    if (!detalhe) return
    setBusy(true)
    try {
      const d = await preTicketIa.editarRascunho(detalhe.id, {
        rascunho_titulo: tituloEdit,
        rascunho_corpo: corpoEdit,
      })
      setDetalhe(d)
      toast.showSuccess('Rascunho salvo.')
    } catch (e) {
      toast.showError(mensagemFalhaParaToast(e))
    } finally {
      setBusy(false)
    }
  }

  async function aprovar() {
    if (!detalhe) return
    setBusy(true)
    try {
      const d = await preTicketIa.aprovar(detalhe.id)
      setDetalhe(d)
      toast.showSuccess('Rascunho aprovado. Pode publicar a issue no GitHub.')
      await carregarLista()
    } catch (e) {
      toast.showError(mensagemFalhaParaToast(e))
    } finally {
      setBusy(false)
    }
  }

  async function publicarGithub() {
    if (!detalhe) return
    if (!window.confirm('Criar issue no GitHub com o rascunho aprovado?')) return
    setBusy(true)
    try {
      const d = await preTicketIa.publicarGithub(detalhe.id)
      setDetalhe(d)
      const h = await preTicketIa.historico(detalhe.id)
      setHistorico(h)
      toast.showSuccess(`Issue #${d.github_issue_number} criada no GitHub.`)
      await carregarLista()
    } catch (e) {
      toast.showError(mensagemFalhaParaToast(e))
    } finally {
      setBusy(false)
    }
  }

  async function descartar() {
    if (!detalhe) return
    if (!window.confirm('Descartar esta sessão de pré-ticket?')) return
    setBusy(true)
    try {
      await preTicketIa.descartar(detalhe.id)
      toast.showSuccess('Sessão descartada.')
      await carregarLista()
      navigate('/pre-ticket-ia')
    } catch (e) {
      toast.showError(mensagemFalhaParaToast(e))
    } finally {
      setBusy(false)
    }
  }

  if (id && detalhe) {
    const a = detalhe.analise
    return (
      <PageContainer>
        <PageHeader
          title="Pré-ticket IA"
          subtitle={`Sessão #${detalhe.id} · ${ESTADO_ROTULO[detalhe.estado] ?? detalhe.estado}`}
          actions={
            <Button variant="secondary" onClick={() => navigate('/pre-ticket-ia')}>
              Voltar à lista
            </Button>
          }
        />

        {iaHabilitada === false && (
          <Card className="mb-4 border-amber-200 bg-amber-50 text-amber-900">
            Análise IA desligada nesta instância (OPENAI_API_KEY / PRE_TICKET_AI_ENABLED).
          </Card>
        )}

        {a && (
          <div className="grid gap-4 md:grid-cols-2 mb-4">
            <Card title="Classificação">
              <p className="font-medium capitalize">{a.classificacao}</p>
              <p className="text-sm text-muted mt-1">Viabilidade: {a.viabilidade.replace(/_/g, ' ')}</p>
              {a.prompt_version && (
                <p className="text-xs text-muted mt-2">Prompt {a.prompt_version}</p>
              )}
            </Card>
            <Card title="Lacunas / perguntas">
              {a.lacunas_perguntas.length === 0 ? (
                <p className="text-sm text-muted">Nenhuma lacuna identificada.</p>
              ) : (
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {a.lacunas_perguntas.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title="Riscos">
              {a.riscos.length === 0 ? (
                <p className="text-sm text-muted">Nenhum risco listado.</p>
              ) : (
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {a.riscos.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title="Critérios de aceite sugeridos">
              <ul className="list-disc pl-5 text-sm space-y-1">
                {a.criterios_aceite.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </Card>
          </div>
        )}

        <Card title="Rascunho da issue" className="mb-4">
          <div className="space-y-3">
            <Input label="Título" value={tituloEdit} onChange={(e) => setTituloEdit(e.target.value)} />
            <label className="block text-sm font-medium">Corpo (markdown)</label>
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={12}
              value={corpoEdit}
              onChange={(e) => setCorpoEdit(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2 mt-4">
            <Button variant="secondary" disabled={busy} onClick={() => salvarRascunho()}>
              Salvar edição
            </Button>
            <Button disabled={busy || iaHabilitada === false} onClick={() => analisar()}>
              {detalhe.estado === 'rascunho' ? 'Analisar com IA' : 'Analisar novamente'}
            </Button>
            <Button
              variant="primary"
              disabled={busy || detalhe.estado === 'aprovado' || detalhe.estado === 'publicado'}
              onClick={() => aprovar()}
            >
              Aprovar rascunho
            </Button>
            {(detalhe.estado === 'aprovado' || detalhe.estado === 'publicado') && (
              <Button
                disabled={busy || githubHabilitado === false || detalhe.estado === 'publicado'}
                onClick={() => publicarGithub()}
              >
                {detalhe.github_issue_number ? 'Issue já criada' : 'Criar issue no GitHub'}
              </Button>
            )}
            <Button variant="danger" disabled={busy} onClick={() => descartar()}>
              Descartar
            </Button>
          </div>
          {detalhe.estado === 'aprovado' && (
            <p className="text-sm text-muted mt-3">
              Aprovado por {detalhe.aprovado_por_nome ?? '—'} em {fmt(detalhe.aprovado_em)}.
              {githubHabilitado === false && ' GitHub não configurado nesta instância.'}
            </p>
          )}
          {detalhe.estado === 'publicado' && detalhe.github_issue_url && (
            <p className="text-sm mt-3">
              Publicado por {detalhe.publicado_por_nome ?? '—'} em {fmt(detalhe.publicado_em)}.{' '}
              <a
                href={detalhe.github_issue_url}
                target="_blank"
                rel="noreferrer"
                className="text-cyan-700 underline dark:text-cyan-400"
              >
                Issue #{detalhe.github_issue_number} no GitHub
              </a>
            </p>
          )}
        </Card>

        <Card title="Histórico interno" className="mb-4">
          {historico.length === 0 ? (
            <p className="text-sm text-muted">Nenhum evento registado.</p>
          ) : (
            <ul className="divide-y text-sm">
              {historico.map((ev) => (
                <li key={ev.id} className="py-2">
                  <div className="font-medium">{ev.acao.replace(/_/g, ' ')}</div>
                  <div className="text-muted text-xs mt-0.5">
                    {ev.atendente_nome ?? '—'} · {fmt(ev.created_at)}
                  </div>
                  {ev.detalhe && <div className="mt-1">{ev.detalhe}</div>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Entrada original">
          <dl className="text-sm space-y-2">
            <div>
              <dt className="font-medium">Contexto</dt>
              <dd className="whitespace-pre-wrap">{detalhe.contexto}</dd>
            </div>
            <div>
              <dt className="font-medium">Problema</dt>
              <dd className="whitespace-pre-wrap">{detalhe.problema}</dd>
            </div>
            {detalhe.impacto && (
              <div>
                <dt className="font-medium">Impacto</dt>
                <dd className="whitespace-pre-wrap">{detalhe.impacto}</dd>
              </div>
            )}
          </dl>
        </Card>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Pré-ticket IA"
        subtitle="Análise estruturada antes de abrir issue no GitHub (#808)"
      />

      {metricas && (
        <Card title="Observabilidade (30 dias)" className="mb-6">
          {metricas.alertas.length > 0 && (
            <ul className="mb-4 space-y-2">
              {metricas.alertas.map((a) => (
                <li
                  key={a.tipo}
                  className="text-sm rounded-md border border-amber-200 bg-amber-50 text-amber-900 px-3 py-2 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
                >
                  {a.mensagem}
                </li>
              ))}
            </ul>
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            <div>
              <div className="text-muted">Análises IA</div>
              <div className="text-lg font-semibold">{metricas.uso.total_analises}</div>
              <div className="text-xs text-muted">
                {metricas.uso.analises_sucesso} ok · {metricas.uso.analises_falha} falha
              </div>
            </div>
            <div>
              <div className="text-muted">Taxa de aprovação</div>
              <div className="text-lg font-semibold">
                {metricas.uso.taxa_aprovacao != null
                  ? `${(metricas.uso.taxa_aprovacao * 100).toFixed(1)}%`
                  : '—'}
              </div>
              <div className="text-xs text-muted">
                Retrabalho:{' '}
                {metricas.uso.taxa_retrabalho != null
                  ? `${(metricas.uso.taxa_retrabalho * 100).toFixed(1)}%`
                  : '—'}
              </div>
            </div>
            <div>
              <div className="text-muted">Latência (média / p95)</div>
              <div className="text-lg font-semibold">
                {metricas.tecnicas.latencia_media_ms ?? '—'} / {metricas.tecnicas.latencia_p95_ms ?? '—'} ms
              </div>
              <div className="text-xs text-muted">
                Erro:{' '}
                {metricas.tecnicas.taxa_erro != null
                  ? `${(metricas.tecnicas.taxa_erro * 100).toFixed(1)}%`
                  : '—'}
              </div>
            </div>
            <div>
              <div className="text-muted">Custo estimado (USD)</div>
              <div className="text-lg font-semibold">{metricas.custo.total_usd.toFixed(4)}</div>
              <div className="text-xs text-muted">Hoje: {metricas.custo.hoje_usd.toFixed(4)}</div>
            </div>
          </div>
        </Card>
      )}

      {iaHabilitada === false && (
        <Card className="mb-4 border-amber-200 bg-amber-50 text-amber-900">
          Análise IA desligada nesta instância. Configure OPENAI_API_KEY e PRE_TICKET_AI_ENABLED no backend.
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Nova análise">
          <div className="space-y-3">
            <label className="block text-sm font-medium">Contexto *</label>
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={4}
              value={contexto}
              onChange={(e) => setContexto(e.target.value)}
              placeholder="Quem reportou, módulo, versão, ambiente…"
            />
            <label className="block text-sm font-medium">Problema *</label>
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={4}
              value={problema}
              onChange={(e) => setProblema(e.target.value)}
              placeholder="O que está errado ou faltando?"
            />
            <Input label="Impacto" value={impacto} onChange={(e) => setImpacto(e.target.value)} />
            <label className="block text-sm font-medium">Evidências</label>
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={3}
              value={evidencias}
              onChange={(e) => setEvidencias(e.target.value)}
            />
            <Input label="Urgência" value={urgencia} onChange={(e) => setUrgencia(e.target.value)} />
            <Input
              label="Ticket de origem (opcional)"
              value={ticketId}
              onChange={(e) => setTicketId(e.target.value)}
              inputMode="numeric"
            />
          </div>
          <Button className="mt-4" disabled={busy} onClick={() => criarSessao()}>
            Criar sessão
          </Button>
        </Card>

        <Card title="Sessões recentes">
          {lista.length === 0 ? (
            <p className="text-sm text-muted">Nenhuma sessão ainda.</p>
          ) : (
            <ul className="divide-y">
              {lista.map((item) => (
                <li key={item.id}>
                  <Link
                    to={`/pre-ticket-ia/${item.id}`}
                    className="block py-3 hover:bg-muted/30 px-2 -mx-2 rounded"
                  >
                    <div className="font-medium truncate">
                      {item.rascunho_titulo || `Sessão #${item.id}`}
                    </div>
                    <div className="text-xs text-muted mt-1">
                      {ESTADO_ROTULO[item.estado] ?? item.estado}
                      {item.classificacao ? ` · ${item.classificacao}` : ''} · {fmt(item.created_at)}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </PageContainer>
  )
}
