import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { solicitacoesMelhoria, type SolicitacoesMelhoria } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { SolicitacaoDescricao } from '../components/release/SolicitacaoDescricao'

function fmt(dt: string): string {
  try {
    return new Date(dt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return dt
  }
}

/** Painel admin: acompanhamento local. A triagem de produto é no SaaS (#856). */
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
      .then(setDetalhe)
      .catch((err) => toast.showError(mensagemFalhaParaToast(err, 'Falha ao abrir')))
  }, [id, toast])

  if (id && detalhe) {
    return (
      <PageContainer>
        <PageHeader
          title={`${detalhe.protocolo || `#${detalhe.id}`} · ${detalhe.titulo}`}
          subtitle="Acompanhamento na instância. A triagem (status e respostas) é feita no painel SaaS DeskRudder."
        />
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
          <SolicitacaoDescricao descricao={detalhe.descricao} anexos={detalhe.anexos} />
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
                {c.origem === 'saas' ? ' · DeskRudder' : ''}
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
      <PageHeader
        title="Sugestões de clientes"
        subtitle="Acompanhamento local. Status e respostas de produto vêm do painel SaaS DeskRudder."
      />
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
                  {item.protocolo || `#${item.id}`} {item.titulo}
                </h3>
                <span className="text-xs">{item.status_rotulo}</span>
              </div>
              <p className="text-xs text-slate-500">
                {item.autor_nome} · org {item.organizacao_id} · {fmt(item.created_at)}
              </p>
            </Card>
          </Link>
        ))}
        {lista.length === 0 ? <p className="text-sm text-slate-500">Nenhuma solicitação com estes filtros.</p> : null}
      </div>
    </PageContainer>
  )
}
