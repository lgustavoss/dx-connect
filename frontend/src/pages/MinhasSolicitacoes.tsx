import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { solicitacoesMelhoria, type SolicitacoesMelhoria } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'
import { SolicitacaoDescricao } from '../components/release/SolicitacaoDescricao'
import { useAuth } from '../contexts/AuthContext'

const STATUS_FINAIS = new Set(['concluida', 'nao_sera_desenvolvida'])

function fmt(dt: string): string {
  try {
    return new Date(dt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return dt
  }
}

/** Lista + detalhe das solicitações do utilizador (#803). */
export function MinhasSolicitacoesPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const [lista, setLista] = useState<SolicitacoesMelhoria.ListaItem[]>([])
  const [detalhe, setDetalhe] = useState<SolicitacoesMelhoria.Detalhe | null>(null)
  const [loading, setLoading] = useState(true)
  const [resposta, setResposta] = useState('')
  const [enviando, setEnviando] = useState(false)

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
      return
    }
    let cancel = false
    void solicitacoesMelhoria
      .get(Number(id))
      .then((d) => {
        if (!cancel) setDetalhe(d)
      })
      .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Falha ao abrir solicitação')))
    return () => {
      cancel = true
    }
  }, [id, toast])

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

  if (id && detalhe) {
    return (
      <PageContainer>
        <PageHeader
          title={detalhe.titulo}
          subtitle={`${detalhe.tipo === 'problema' ? 'Problema' : 'Sugestão'} · ${detalhe.status_rotulo}`}
        />
        <Link to="/minhas-solicitacoes" className="text-sm text-cyan-700 hover:underline dark:text-cyan-400">
          ← Voltar à lista
        </Link>

        <Card className="space-y-3 p-5">
          <SolicitacaoDescricao descricao={detalhe.descricao} anexos={detalhe.anexos} />
          <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
            {detalhe.mensagem_status}
          </p>
          {detalhe.status === 'nao_sera_desenvolvida' && detalhe.motivo_nao_desenvolvimento ? (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              <span className="font-medium">Motivo: </span>
              {detalhe.motivo_nao_desenvolvimento}
            </p>
          ) : null}
        </Card>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Acompanhamento</h2>
          <div className="space-y-2">
            {detalhe.historico.map((h) => (
              <Card key={`h-${h.id}`} className="p-3 text-sm">
                <p className="font-medium text-slate-800 dark:text-slate-100">{h.status_novo_rotulo}</p>
                {h.mensagem_publica ? (
                  <p className="mt-1 whitespace-pre-wrap text-slate-600 dark:text-slate-300">{h.mensagem_publica}</p>
                ) : null}
                <p className="mt-1 text-xs text-slate-400">{fmt(h.created_at)}</p>
              </Card>
            ))}
            {detalhe.comentarios.map((c) => (
              <Card key={`c-${c.id}`} className="p-3 text-sm">
                <p className="text-xs font-medium text-slate-500">{c.autor_nome || 'Equipa'} · {fmt(c.created_at)}</p>
                <p className="mt-1 whitespace-pre-wrap text-slate-700 dark:text-slate-200">{c.corpo}</p>
              </Card>
            ))}
          </div>
        </section>

        {podeResponder ? (
          <Card className="space-y-3 p-5">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Responder</label>
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={3}
              value={resposta}
              onChange={(e) => setResposta(e.target.value)}
              placeholder="Escreva uma mensagem para a equipa…"
            />
            <Button type="button" variant="primary" loading={enviando} onClick={() => void enviarResposta()}>
              Enviar resposta
            </Button>
          </Card>
        ) : STATUS_FINAIS.has(detalhe.status) ? (
          <p className="text-sm text-slate-500">Este pedido está encerrado e já não aceita respostas.</p>
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
        <p className="text-sm text-slate-500">A carregar…</p>
      ) : lista.length === 0 ? (
        <Card className="p-8 text-center text-sm text-slate-500">
          Ainda não tem pedidos.{' '}
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
        <div className="space-y-2">
          {lista.map((item) => (
            <Link key={item.id} to={`/minhas-solicitacoes/${item.id}`} className="block">
              <Card className="p-4 transition hover:ring-1 hover:ring-cyan-400/50">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-semibold text-slate-900 dark:text-slate-50">{item.titulo}</h3>
                  <span className="text-xs font-medium text-slate-500">{item.status_rotulo}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {item.tipo === 'problema' ? 'Problema' : 'Sugestão'} · {fmt(item.created_at)}
                </p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </PageContainer>
  )
}
