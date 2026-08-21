import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ApiError,
  empresas as apiEmpresas,
  redes,
  tiposNegocio,
  tickets,
  funcionariosRede,
  type Empresas,
  type Tickets,
  type FuncionariosRede,
} from '../api/client'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { maskCnpjCpf } from '../utils/maskCnpjCpf'
import { maskCep, formatTelefoneBrExibicao } from '../utils/masks'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { TicketsTabelaContexto } from '../components/TicketsTabelaContexto'
import { FuncionariosEmpresaLista } from '../components/FuncionariosEmpresaLista'
import { EmpresaPdvsPanel } from '../components/EmpresaPdvsPanel'
import { EmpresaChatsPanel } from '../components/EmpresaChatsPanel'
import { PainelAnalisesCliente } from '../components/dashboard/PainelAnalisesCliente'
import { SemPermissao } from './SemPermissao'
type Aba = 'geral' | 'tickets' | 'chats' | 'funcionarios' | 'pdvs' | 'analises'

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  const v = value?.trim()
  return (
    <div className="grid grid-cols-1 gap-0.5 border-b border-slate-100 py-3 last:border-0 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-6 sm:py-3.5 dark:border-slate-800">
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">{label}</dt>
      <dd className="text-sm leading-relaxed text-slate-800 dark:text-slate-100">{v ? v : '—'}</dd>
    </div>
  )
}

export function EmpresaDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const voltarParaRede = (location.state as { voltarPara?: string } | null)?.voltarPara
  const voltarHistorico = useVoltarAnterior(voltarParaRede ?? '/empresas')
  const voltar = useCallback(() => {
    if (voltarParaRede) {
      navigate(voltarParaRede)
      return
    }
    voltarHistorico()
  }, [navigate, voltarParaRede, voltarHistorico])
  const toast = useToast()
  const empresaId = id ? parseInt(id, 10) : NaN

  const [empresa, setEmpresa] = useState<Empresas.Empresa | null>(null)
  const [redeNome, setRedeNome] = useState<string>('')
  const [tipoNegocioNome, setTipoNegocioNome] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [loadFailure, setLoadFailure] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [aba, setAba] = useState<Aba>('geral')

  useEffect(() => {
    const q = searchParams.get('aba')
    if (q === 'pdvs' || q === 'tickets' || q === 'chats' || q === 'funcionarios' || q === 'analises' || q === 'geral') {
      setAba(q)
    }
  }, [searchParams])

  const [pageT, setPageT] = useState(1)
  const [buscaT, setBuscaT] = useState('')
  const [debouncedBuscaT, setDebouncedBuscaT] = useState('')
  const [ticketsItems, setTicketsItems] = useState<Tickets.Ticket[]>([])
  const [ticketsTotal, setTicketsTotal] = useState(0)
  const [loadingT, setLoadingT] = useState(false)

  const [pageF, setPageF] = useState(1)
  const [buscaF, setBuscaF] = useState('')
  const [debouncedBuscaF, setDebouncedBuscaF] = useState('')
  const [funcItems, setFuncItems] = useState<FuncionariosRede.Funcionario[]>([])
  const [funcTotal, setFuncTotal] = useState(0)
  const [loadingF, setLoadingF] = useState(false)

  useEffect(() => {
    if (!id || isNaN(empresaId)) {
      setLoading(false)
      setLoadFailure({
        titulo: 'Empresa não encontrada.',
        detalhe: 'O identificador na URL é inválido.',
      })
      return
    }
    let cancelled = false
    setLoading(true)
    setLoadFailure(null)
    setForbidden(false)
    apiEmpresas
      .get(empresaId)
      .then(async (e) => {
        if (cancelled) return
        setEmpresa(e)
        try {
          const r = await redes.get(e.rede_id)
          if (!cancelled) setRedeNome(r.nome)
        } catch {
          if (!cancelled) setRedeNome('—')
        }
        if (e.tipo_negocio_id != null) {
          try {
            const t = await tiposNegocio.get(e.tipo_negocio_id)
            if (!cancelled) setTipoNegocioNome(t.nome)
          } catch {
            if (!cancelled) setTipoNegocioNome('—')
          }
        } else if (!cancelled) setTipoNegocioNome('')
      })
      .catch((err) => {
        if (!cancelled) {
          if (err instanceof ApiError && err.status === 403) {
            setForbidden(true)
            setEmpresa(null)
            return
          }
          setLoadFailure(interpretarFalhaCarregamento(err, 'Empresa não encontrada.'))
          setEmpresa(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, empresaId])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaT(buscaT.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaT])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaF(buscaF.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaF])

  useEffect(() => {
    if (aba !== 'tickets' || !empresaId || Number.isNaN(empresaId)) return
    let cancelled = false
    setLoadingT(true)
    tickets
      .list({
        empresa_id: empresaId,
        situacao: 'todos',
        offset: (pageT - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
        busca: debouncedBuscaT || undefined,
      })
      .then(({ items, total }) => {
        if (!cancelled) {
          setTicketsItems(items)
          setTicketsTotal(total)
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingT(false)
      })
    return () => {
      cancelled = true
    }
  }, [aba, empresaId, pageT, debouncedBuscaT])

  useEffect(() => {
    if (aba !== 'funcionarios' || !empresaId || Number.isNaN(empresaId)) return
    let cancelled = false
    setLoadingF(true)
    funcionariosRede
      .list({
        empresa_id: empresaId,
        incluir_inativos: true,
        busca: debouncedBuscaF || undefined,
        offset: (pageF - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total }) => {
        if (!cancelled) {
          setFuncItems(items)
          setFuncTotal(total)
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingF(false)
      })
    return () => {
      cancelled = true
    }
  }, [aba, empresaId, pageF, debouncedBuscaF])

  function abrirEdicao() {
    if (!empresa) return
    navigate(`/empresas/${empresa.id}/editar`)
  }

  async function handleExcluir() {
    if (!empresa || !confirm('Excluir esta empresa? Esta ação não pode ser desfeita.')) return
    try {
      await apiEmpresas.delete(empresa.id)
      toast.showSuccess('Empresa excluída.')
      navigate(voltarParaRede ?? '/empresas', { replace: true })
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir a empresa.'))
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-4 w-24 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-9 w-2/3 max-w-md animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para acessar esta empresa."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/empresas"
          voltarLabel="Voltar para Empresas"
        />
      </div>
    )
  }

  if (loadFailure) {
    return (
      <CarregamentoFalhou titulo={loadFailure.titulo} detalhe={loadFailure.detalhe} onVoltar={voltar} />
    )
  }

  if (!empresa) {
    return null
  }

  const doc = empresa.cnpj_cpf ? maskCnpjCpf(empresa.cnpj_cpf) : null
  const enderecoLinha = [empresa.endereco, empresa.numero, empresa.complemento].filter(Boolean).join(', ') || null
  const cidadeUf = [empresa.cidade, empresa.estado].filter(Boolean).join(' / ') || null
  const cepFmt = empresa.cep ? maskCep(empresa.cep) : null
  const respLegalCpfFmt = empresa.resp_legal_cpf ? maskCnpjCpf(empresa.resp_legal_cpf) : null
  const respLegalCepFmt = empresa.resp_legal_cep ? maskCep(empresa.resp_legal_cep) : null
  const telefoneFmt = formatTelefoneBrExibicao(empresa.telefone) || null
  const respLegalTelefoneFmt = formatTelefoneBrExibicao(empresa.resp_legal_telefone) || null
  const respLegalEnderecoLinha =
    [empresa.resp_legal_endereco, empresa.resp_legal_numero, empresa.resp_legal_complemento].filter(Boolean).join(', ') ||
    null
  const respLegalCidadeUf =
    [empresa.resp_legal_cidade, empresa.resp_legal_estado].filter(Boolean).join(' / ') || null

  const tabBtn = (key: Aba, label: string) => (
    <button
      type="button"
      onClick={() => setAba(key)}
      aria-current={aba === key ? 'page' : undefined}
      className={
        aba === key
          ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
          : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
      }
    >
      {label}
    </button>
  )

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-10">
      <div>
        <button
          type="button"
          onClick={voltar}
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar
        </button>
      </div>

      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 md:text-3xl">
              {empresa.nome}
            </h1>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  empresa.ativo
                    ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-600/15 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-600/30'
                    : 'bg-slate-100 text-slate-600 ring-1 ring-slate-300/60 dark:bg-slate-800 dark:text-slate-400 dark:ring-slate-600/40'
                }`}
              >
                {empresa.ativo ? 'Ativa' : 'Inativa'}
              </span>
              {doc ? (
                <span className="font-mono text-sm tabular-nums text-slate-600 dark:text-slate-300">{doc}</span>
              ) : null}
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button variant="secondary" onClick={voltar}>
              Voltar
            </Button>
            <Button onClick={abrirEdicao}>Editar</Button>
            <Button variant="danger" onClick={handleExcluir}>
              Excluir
            </Button>
          </div>
        </div>

        <div className="border-b border-slate-200 dark:border-slate-600">
          <nav className="flex flex-wrap gap-1 sm:gap-2" aria-label="Seções da empresa">
            {tabBtn('geral', 'Geral')}
            {tabBtn('analises', 'Análises')}
            {tabBtn('tickets', 'Tickets')}
            {tabBtn('chats', 'Chats')}
            {tabBtn('funcionarios', 'Funcionários')}
            {tabBtn('pdvs', 'PDVs')}
          </nav>
        </div>
      </header>

      {aba === 'geral' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Vínculos
            </h2>
            <dl>
              <div className="grid grid-cols-1 gap-0.5 border-b border-slate-100 py-3 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-6 sm:py-3.5 dark:border-slate-800">
                <dt className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                  Rede
                </dt>
                <dd className="text-sm">
                  {redeNome && redeNome !== '—' ? (
                    <Link
                      to={`/redes/${empresa.rede_id}`}
                      className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-2 transition-colors hover:text-slate-950 hover:decoration-slate-500 dark:text-slate-100 dark:decoration-slate-600 dark:hover:text-white"
                    >
                      {redeNome}
                    </Link>
                  ) : (
                    <span className="text-slate-800 dark:text-slate-200">—</span>
                  )}
                </dd>
              </div>
              <DetailRow label="Tipo de negócio" value={tipoNegocioNome || undefined} />
              <DetailRow
                label="Emite NFS-e"
                value={empresa.emite_nfse === false ? 'Não' : 'Sim'}
              />
            </dl>
          </section>

          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Contato
            </h2>
            <dl>
              <DetailRow label="E-mail" value={empresa.email} />
              <DetailRow label="Telefone" value={telefoneFmt} />
            </dl>
          </section>

          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Dados cadastrais
            </h2>
            <dl>
              <DetailRow label="Razão social" value={empresa.razao_social} />
              <DetailRow label="Nome fantasia" value={empresa.nome_fantasia} />
              <DetailRow label="Inscrição estadual" value={empresa.inscricao_estadual} />
            </dl>
          </section>

          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Endereço
            </h2>
            <dl>
              <DetailRow label="Logradouro" value={enderecoLinha} />
              <DetailRow label="Bairro" value={empresa.bairro} />
              <DetailRow label="Cidade / UF" value={cidadeUf} />
              <DetailRow label="CEP" value={cepFmt} />
            </dl>
          </section>

          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7 lg:col-span-2">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Responsável legal
            </h2>
            <p className="mb-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Dados para identificação em contratos de prestação de serviço e documentos correlatos.
            </p>
            <dl className="grid grid-cols-1 gap-x-8 lg:grid-cols-2">
              <DetailRow label="Nome completo" value={empresa.resp_legal_nome} />
              <DetailRow label="CPF" value={respLegalCpfFmt} />
              <DetailRow label="RG" value={empresa.resp_legal_rg} />
              <DetailRow label="Órgão emissor" value={empresa.resp_legal_orgao_emissor} />
              <DetailRow label="Nacionalidade" value={empresa.resp_legal_nacionalidade} />
              <DetailRow label="Estado civil" value={empresa.resp_legal_estado_civil} />
              <DetailRow label="Cargo na empresa" value={empresa.resp_legal_cargo} />
              <DetailRow label="E-mail" value={empresa.resp_legal_email} />
              <DetailRow label="Telefone" value={respLegalTelefoneFmt} />
              <DetailRow label="Endereço (logradouro, nº, compl.)" value={respLegalEnderecoLinha} />
              <DetailRow label="Bairro" value={empresa.resp_legal_bairro} />
              <DetailRow label="Cidade / UF" value={respLegalCidadeUf} />
              <DetailRow label="CEP" value={respLegalCepFmt} />
            </dl>
          </section>
        </div>
      )}

      {aba === 'analises' && (
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
          <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
            Estatísticas de tickets e demandas WhatsApp só desta empresa — use o período para treinar, priorizar
            atualizações e evoluir o catálogo de motivos.
          </p>
          <PainelAnalisesCliente
            empresaId={empresa.id}
            onVerTickets={() => setAba('tickets')}
            onVerChats={() => setAba('chats')}
          />
        </section>
      )}

      {aba === 'tickets' && (
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
          <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
            Tickets abertos e encerrados vinculados a esta empresa.
          </p>
          <BarraBuscaPaginacao
            busca={buscaT}
            onBuscaChange={(v) => {
              setBuscaT(v)
              setPageT(1)
            }}
            placeholder="Protocolo ou assunto..."
            page={pageT}
            total={ticketsTotal}
            onPageChange={setPageT}
            disabled={loadingT}
            extra={
              <Link to="/tickets/novo">
                <Button type="button">Novo ticket</Button>
              </Link>
            }
          />
          <TicketsTabelaContexto
            items={ticketsItems}
            loading={loadingT}
            showEmpresaColumn={false}
            emptyMessage="Nenhum ticket para esta empresa."
          />
        </section>
      )}

      {aba === 'chats' && (
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
          <EmpresaChatsPanel empresaId={empresa.id} />
        </section>
      )}

      {aba === 'funcionarios' && (
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
          <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
            Funcionários da rede associados a esta empresa (sócio, supervisor ou colaborador).
          </p>
          <BarraBuscaPaginacao
            busca={buscaF}
            onBuscaChange={(v) => {
              setBuscaF(v)
              setPageF(1)
            }}
            placeholder="Nome ou e-mail..."
            page={pageF}
            total={funcTotal}
            onPageChange={setPageF}
            disabled={loadingF}
            extra={
              <Link
                to={`/funcionarios-rede/novo?empresa_id=${empresa.id}&rede_id=${empresa.rede_id}`}
              >
                <Button type="button">Adicionar funcionário</Button>
              </Link>
            }
          />
          <FuncionariosEmpresaLista
            items={funcItems}
            loading={loadingF}
            emptyMessage="Nenhum funcionário vinculado a esta empresa."
            emptyAction={
              <Link
                to={`/funcionarios-rede/novo?empresa_id=${empresa.id}&rede_id=${empresa.rede_id}`}
                className="mt-3 inline-block"
              >
                <Button type="button">Cadastrar ou vincular funcionário</Button>
              </Link>
            }
          />
        </section>
      )}

      {aba === 'pdvs' && (
        <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/70 dark:shadow-none sm:p-7">
          <EmpresaPdvsPanel empresaId={empresa.id} />
        </section>
      )}
    </div>
  )
}
