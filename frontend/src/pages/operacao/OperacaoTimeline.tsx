/**
 * Timeline 360 do cliente da carteira (#912 / #913 / #914).
 *
 * Página nova — a rota (`/operacao/timeline`) é integrada pelo Lead no App.tsx.
 * O cliente é escolhido por `?empresa_id=`, permitindo abrir a timeline direto
 * da carteira de clientes.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError, empresas, faturamento, type Faturamento } from '../../api/client'
import { temPermissao } from '../../lib/permissoes'
import { useAuth } from '../../contexts/AuthContext'
import { ResumoAReceberCards } from '../../components/faturamento/ResumoAReceberCards'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import {
  CATEGORIA_BADGE_CLASS,
  CATEGORIA_LABEL,
  CATEGORIAS_TIMELINE,
  operacaoTimeline,
  SAUDE_BADGE_CLASS,
  SAUDE_LABEL,
  type CategoriaEvento,
  type EventoTimeline,
  type NivelSinal,
  type SaudeEmpresa,
} from '../../api/operacaoTimeline'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { formatDateTime } from '../../lib/formatDateTime'
import { useAbrirTicket } from '../../lib/ticketAtivo'
import { SemPermissao } from '../SemPermissao'

const LIMITE = 30

const NIVEL_BADGE_CLASS: Record<NivelSinal, string> = {
  saudavel: SAUDE_BADGE_CLASS.saudavel,
  atencao: SAUDE_BADGE_CLASS.atencao,
  risco: SAUDE_BADGE_CLASS.risco,
  info: 'bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700',
}

const NIVEL_LABEL: Record<NivelSinal, string> = {
  saudavel: 'Saudável',
  atencao: 'Atenção',
  risco: 'Risco',
  info: 'Informativo',
}

function statusResumo(saude: SaudeEmpresa): string {
  if (saude.sinais.length === 0) return 'Sem sinais calculados.'
  const ultimo = saude.sinais.find((sinal) => sinal.codigo === 'dias_sem_movimento')
  return ultimo?.valor ?? 'Sinais disponíveis no detalhe abaixo.'
}

function formatarMoeda(valor: string | number): string {
  const numero = typeof valor === 'number' ? valor : Number(valor)
  if (Number.isNaN(numero)) return String(valor)
  return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatarData(valor: string | null | undefined): string {
  if (!valor) return '—'
  const [ano, mes, dia] = valor.slice(0, 10).split('-')
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : valor
}

export function OperacaoTimeline() {
  const toast = useToast()
  const abrirTicket = useAbrirTicket()
  const { user, isFinanceiroOuAdmin } = useAuth()
  // Mesmo critério da aba Faturamento: permissão do grupo OU vínculo ao setor Financeiro.
  const podeFinanceiro = isFinanceiroOuAdmin || temPermissao(user, 'faturamento.ver')
  const [searchParams, setSearchParams] = useSearchParams()

  const empresaParam = Number(searchParams.get('empresa_id') ?? '')
  const empresaId = Number.isFinite(empresaParam) && empresaParam > 0 ? empresaParam : null

  const [opcoesEmpresa, setOpcoesEmpresa] = useState<Array<{ value: number; label: string }>>([])
  const [categoria, setCategoria] = useState<CategoriaEvento | ''>('')
  const [de, setDe] = useState('')
  const [ate, setAte] = useState('')
  const [offset, setOffset] = useState(0)
  const [resumo, setResumo] = useState<Faturamento.ResumoAReceber | null>(null)
  const [resumoLoading, setResumoLoading] = useState(false)
  const [erroFinanceiro, setErroFinanceiro] = useState<string | null>(null)

  const [eventos, setEventos] = useState<EventoTimeline[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [forbidden, setForbidden] = useState(false)

  const [saude, setSaude] = useState<SaudeEmpresa | null>(null)
  const [saudeErro, setSaudeErro] = useState<string | null>(null)

  useEffect(() => {
    empresas
      .list({ limit: 100, ordenar_por: 'nome' })
      .then(({ items }) => {
        setOpcoesEmpresa(items.map((item) => ({ value: item.id, label: item.nome })))
      })
      .catch(() => setOpcoesEmpresa([]))
  }, [])

  const carregarSaude = useCallback(() => {
    if (empresaId == null) {
      setSaude(null)
      setSaudeErro(null)
      return
    }
    operacaoTimeline
      .saude(empresaId)
      .then((resposta) => {
        setSaude(resposta)
        setSaudeErro(null)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        setSaude(null)
        setSaudeErro(mensagemFalhaParaToast(err, 'Não foi possível carregar a saúde do cliente.'))
      })
  }, [empresaId])

  const carregarTimeline = useCallback(() => {
    if (empresaId == null) {
      setEventos([])
      setTotal(0)
      setErro(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setErro(null)
    operacaoTimeline
      .timeline({
        empresaId,
        categorias: categoria ? [categoria] : undefined,
        de: de || undefined,
        ate: ate || undefined,
        offset,
        limit: LIMITE,
      })
      .then(({ items, total: totalApi }) => {
        setEventos(items)
        setTotal(totalApi)
      })
      .catch((err) => {
        setEventos([])
        setTotal(0)
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        const mensagem = mensagemFalhaParaToast(err, 'Não foi possível carregar a timeline.')
        setErro(mensagem)
        toast.showError(mensagem)
      })
      .finally(() => setLoading(false))
  }, [empresaId, categoria, de, ate, offset, toast])

  useEffect(() => {
    carregarSaude()
  }, [carregarSaude])

  useEffect(() => {
    carregarTimeline()
  }, [carregarTimeline])

  // Situação financeira da ficha (#1385): só para quem tem faturamento.ver.
  useEffect(() => {
    if (empresaId == null || !podeFinanceiro) {
      setResumo(null)
      setErroFinanceiro(null)
      return
    }
    let cancelado = false
    setResumoLoading(true)
    setErroFinanceiro(null)
    faturamento
      .resumoAReceber({ empresa_id: empresaId })
      .then((resumoAtual) => {
        if (cancelado) return
        setResumo(resumoAtual)
      })
      .catch((err) => {
        if (cancelado) return
        setResumo(null)
        setErroFinanceiro(mensagemFalhaParaToast(err, 'Não foi possível carregar a situação financeira.'))
      })
      .finally(() => {
        if (!cancelado) setResumoLoading(false)
      })
    return () => {
      cancelado = true
    }
  }, [empresaId, podeFinanceiro])

  const selecionarEmpresa = (valor: string | number | '') => {
    const proximo = new URLSearchParams(searchParams)
    if (valor === '') {
      proximo.delete('empresa_id')
    } else {
      proximo.set('empresa_id', String(valor))
    }
    setSearchParams(proximo, { replace: true })
    setOffset(0)
    setCategoria('')
    setDe('')
    setAte('')
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para ver a timeline operacional."
        detail="Peça ao gestor a permissão de CRM (crm.ver) para acompanhar os clientes da carteira."
        voltarPara="/"
        voltarLabel="Voltar para o início"
      />
    )
  }

  const podeLimparFiltros = Boolean(categoria || de || ate)

  // O resumo já traz próximo vencimento, pago no ano e quantidade de títulos
  // abertos (#1385) — a ficha não baixa a lista inteira de títulos.
  const anoAtual = new Date().getFullYear()
  const proximoVencimento = resumo?.proximo_vencimento ?? null
  const pagoNoAno = Number(resumo?.pago_ano ?? 0)
  const titulosAbertos = resumo?.quantidade_titulos ?? 0

  return (
    <PageContainer>
      <PageHeader
        title="Timeline do cliente"
        subtitle="Jornada operacional do cliente da carteira: CRM, implantação e suporte em ordem cronológica."
        actions={
          <Link
            to="/operacao/carteira"
            className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-300"
          >
            Ver carteira
          </Link>
        }
      />

      <Card
        title="Filtros"
        description="Escolha o cliente da carteira e recorte por categoria ou período."
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2">
            <Select
              label="Cliente"
              value={empresaId ?? ''}
              onChange={selecionarEmpresa}
              options={opcoesEmpresa}
              includeEmpty
              emptyLabel="Selecione um cliente"
              placeholder="Buscar cliente"
            />
          </div>
          <Select
            label="Categoria"
            value={categoria}
            onChange={(valor) => {
              setCategoria(valor === '' ? '' : (valor as CategoriaEvento))
              setOffset(0)
            }}
            options={CATEGORIAS_TIMELINE.map((opcao) => ({ value: opcao.value, label: opcao.label }))}
            includeEmpty
            emptyLabel="Todas"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              type="date"
              label="De"
              value={de}
              onChange={(e) => {
                setDe(e.target.value)
                setOffset(0)
              }}
            />
            <Input
              type="date"
              label="Até"
              value={ate}
              onChange={(e) => {
                setAte(e.target.value)
                setOffset(0)
              }}
            />
          </div>
        </div>
        {podeLimparFiltros ? (
          <Button
            variant="ghost"
            className="mt-3"
            onClick={() => {
              setCategoria('')
              setDe('')
              setAte('')
              setOffset(0)
            }}
          >
            Limpar filtros
          </Button>
        ) : null}
      </Card>

      {empresaId == null ? (
        <Card>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Selecione um cliente da carteira para ver a timeline 360.
          </p>
        </Card>
      ) : (
        <>
          <Card
            title={saude?.empresa_nome ?? 'Saúde do cliente'}
            description="Status e sinais objetivos usados pela operação no pós-venda."
            titleActions={
              saude ? (
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${SAUDE_BADGE_CLASS[saude.status]}`}
                >
                  {SAUDE_LABEL[saude.status]}
                </span>
              ) : null
            }
          >
            {saudeErro ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
                {saudeErro}
              </div>
            ) : !saude ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Carregando saúde…</p>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">{statusResumo(saude)}</p>
                {saude.motivos.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-200">
                    {saude.motivos.map((motivo) => (
                      <li key={motivo}>{motivo}</li>
                    ))}
                  </ul>
                ) : null}
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[560px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                        <th className="py-2 pr-4 font-semibold">Sinal</th>
                        <th className="py-2 pr-4 font-semibold">Valor</th>
                        <th className="py-2 pr-4 font-semibold">Leitura</th>
                        <th className="py-2 font-semibold">Critério</th>
                      </tr>
                    </thead>
                    <tbody>
                      {saude.sinais.map((sinal) => (
                        <tr
                          key={sinal.codigo}
                          className="border-b border-slate-100 align-top last:border-0 dark:border-slate-800/70"
                        >
                          <td className="py-2 pr-4 font-medium text-slate-700 dark:text-slate-200">
                            {sinal.rotulo}
                          </td>
                          <td className="py-2 pr-4 text-slate-600 dark:text-slate-300">{sinal.valor}</td>
                          <td className="py-2 pr-4">
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${NIVEL_BADGE_CLASS[sinal.nivel]}`}
                            >
                              {NIVEL_LABEL[sinal.nivel]}
                            </span>
                          </td>
                          <td className="py-2 text-xs text-slate-500 dark:text-slate-400">
                            {sinal.explicacao ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </Card>

          {podeFinanceiro ? (
            <Card
              title="Situação financeira"
              description="Cobranças do cliente na ficha 360 (visível para quem tem faturamento.ver)."
              titleActions={
                <Link
                  to="/faturamento"
                  className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-300"
                >
                  Abrir faturamento
                </Link>
              }
            >
              {erroFinanceiro ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
                  {erroFinanceiro}
                </div>
              ) : resumoLoading && !resumo ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Carregando situação financeira…</p>
              ) : (
                <div className="space-y-3">
                  <ResumoAReceberCards resumo={resumo} loading={false} />
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
                    <span>
                      <strong className="text-slate-800 dark:text-slate-100">Próximo vencimento:</strong>{' '}
                      {formatarData(proximoVencimento)}
                    </span>
                    <span>
                      <strong className="text-slate-800 dark:text-slate-100">Pago em {anoAtual}:</strong>{' '}
                      {formatarMoeda(pagoNoAno)}
                    </span>
                    <span>
                      <strong className="text-slate-800 dark:text-slate-100">Títulos em aberto:</strong>{' '}
                      {titulosAbertos}
                    </span>
                  </div>
                </div>
              )}
            </Card>
          ) : null}

          <Card
            title="Eventos"
            description="Marcos derivados de CRM, proposta/contrato, implantação, suporte e cobrança."
            titleActions={
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {total === 0 ? 'Nenhum evento' : `${offset + 1}–${Math.min(offset + eventos.length, total)} de ${total}`}
              </span>
            }
          >
            {erro ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
                <p>{erro}</p>
                <Button variant="secondary" className="mt-3" onClick={carregarTimeline}>
                  Tentar novamente
                </Button>
              </div>
            ) : loading ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Carregando timeline…</p>
            ) : eventos.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Nenhum evento para os filtros atuais. Este cliente pode ainda não ter histórico
                derivável de CRM, implantação, suporte ou cobrança.
              </p>
            ) : (
              <ol className="space-y-3">
                {eventos.map((evento) => (
                  <li
                    key={evento.id}
                    className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-900/40"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${CATEGORIA_BADGE_CLASS[evento.categoria]}`}
                      >
                        {CATEGORIA_LABEL[evento.categoria]}
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {formatDateTime(evento.em)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                      {evento.titulo}
                    </p>
                    {evento.detalhe ? (
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                        {evento.detalhe}
                      </p>
                    ) : null}
                    <div className="mt-3 flex flex-wrap gap-4 text-sm">
                      {evento.ref_tipo === 'crm_negociacao' && evento.ref_id != null ? (
                        <Link
                          to={`/crm/negociacoes/${evento.ref_id}`}
                          className="font-medium text-cyan-700 hover:underline dark:text-cyan-300"
                        >
                          Abrir negociação
                        </Link>
                      ) : null}
                      {evento.ref_tipo === 'ticket' && evento.ref_id != null ? (
                        <button
                          type="button"
                          onClick={() => abrirTicket(evento.ref_id as number)}
                          className="font-medium text-cyan-700 hover:underline dark:text-cyan-300"
                        >
                          Abrir ticket
                        </button>
                      ) : null}
                      {evento.ref_tipo === 'comercial_contrato' ? (
                        <Link
                          to="/crm/contratos"
                          className="font-medium text-cyan-700 hover:underline dark:text-cyan-300"
                        >
                          Ver contratos
                        </Link>
                      ) : null}
                      {evento.ref_tipo === 'comercial_proposta' && evento.ref_id != null ? (
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          Proposta #{evento.ref_id}
                        </span>
                      ) : null}
                      {evento.ref_tipo === 'fatura' || evento.ref_tipo === 'titulo' ? (
                        <Link
                          to="/faturamento"
                          className="font-medium text-cyan-700 hover:underline dark:text-cyan-300"
                        >
                          Ver faturamento
                        </Link>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ol>
            )}

            <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
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
          </Card>
        </>
      )}
    </PageContainer>
  )
}
