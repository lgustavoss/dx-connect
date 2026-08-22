import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ApiError,
  redes,
  empresas,
  funcionariosRede,
  tiposNegocio,
  tickets,
  type Redes,
  type Empresas,
  type TiposNegocio,
  type Tickets,
  type FuncionariosRede,
} from '../api/client'
import { TicketsTabelaContexto } from '../components/TicketsTabelaContexto'
import { FuncionariosEmpresaLista } from '../components/FuncionariosEmpresaLista'
import { EmpresaPdvsPanel } from '../components/EmpresaPdvsPanel'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { VoltarButton } from '../components/ui/VoltarButton'
import { Input } from '../components/ui/Input'
import { FormSection } from '../components/ui/FormSection'
import {
  EMPRESA_HINT_ATIVA,
  EMPRESA_SECAO_DOCUMENTO_NOMES,
  EMPRESA_SECAO_RESPONSAVEL_LEGAL,
  nomeParaApiEmpresa,
} from '../components/empresa/empresaFormCopy'
import { IconPencil } from '../components/ui/IconPencil'
import { IconTrash } from '../components/ui/IconTrash'
import { useToast } from '../components/ui/Toast'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { maskCnpjCpf, digitsOnly, isCnpj } from '../utils/maskCnpjCpf'
import {
  maskCep,
  maskTelefoneBr,
  maskInscricaoEstadual,
  formatTelefoneBrExibicao,
} from '../utils/masks'
import { ESTADOS_CIVIS_BR, type EstadoCivilBr } from '../constants/estadosCivis'
import { SelectUf } from '../components/ui/SelectUf'
import { SelectCidadeUf } from '../components/ui/SelectCidadeUf'
import { InputCepComBusca } from '../components/ui/InputCepComBusca'
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { Select } from '../components/ui/Select'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { Switch } from '../components/ui/Switch'
import { CheckboxField } from '../components/ui/CheckboxField'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'

import { PainelAnalisesCliente } from '../components/dashboard/PainelAnalisesCliente'

type Aba = 'empresas' | 'funcionarios' | 'tickets' | 'analises'
type AbaModalEmpresa = 'geral' | 'tickets' | 'funcionarios' | 'pdvs'
type TipoFuncionario = 'socio' | 'supervisor' | 'colaborador'
const tipoLabel: Record<string, string> = { socio: 'Sócio', supervisor: 'Supervisor', colaborador: 'Colaborador' }

type FuncionarioListaItem = Redes.FuncionarioComVinculo
type ColunaEmpresaRede = 'nome' | 'cnpj_cpf'
type ColunaFuncRede = 'nome' | 'email' | 'tipo'

export function RedeDetalhe() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/redes')
  const toast = useToast()
  const redeId = id ? parseInt(id, 10) : NaN
  const {
    ordenarPor: ordemColEmpresa,
    ordem: dirEmpresa,
    aoOrdenarColuna: aoOrdEmpresa,
  } = useOrdenacaoLista<ColunaEmpresaRede>()
  const {
    ordenarPor: ordemColFunc,
    ordem: dirFunc,
    aoOrdenarColuna: aoOrdFunc,
    sortParams: sortFuncParams,
  } = useOrdenacaoLista<ColunaFuncRede>()

  const [rede, setRede] = useState<Awaited<ReturnType<typeof redes.get>> | null>(null)
  const [empresasList, setEmpresasList] = useState<Empresas.Empresa[]>([])
  const [funcionariosList, setFuncionariosList] = useState<FuncionarioListaItem[]>([])
  const [funcionariosTotal, setFuncionariosTotal] = useState(0)
  const [pageFuncionarios, setPageFuncionarios] = useState(1)
  const [buscaFuncionarios, setBuscaFuncionarios] = useState('')
  const [debouncedBuscaFuncionarios, setDebouncedBuscaFuncionarios] = useState('')
  const [loadingFuncionarios, setLoadingFuncionarios] = useState(false)
  const [buscaEmpresas, setBuscaEmpresas] = useState('')
  const [debouncedBuscaEmpresas, setDebouncedBuscaEmpresas] = useState('')
  const [pageEmpresas, setPageEmpresas] = useState(1)
  const [loading, setLoading] = useState(true)
  const [loadFailure, setLoadFailure] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [aba, setAba] = useState<Aba>('empresas')
  const [abaModalEmpresa, setAbaModalEmpresa] = useState<AbaModalEmpresa>('geral')
  const [incluirInativos, setIncluirInativos] = useState(false)

  const [pageTicketsRede, setPageTicketsRede] = useState(1)
  const [buscaTicketsRede, setBuscaTicketsRede] = useState('')
  const [debouncedBuscaTicketsRede, setDebouncedBuscaTicketsRede] = useState('')
  const [ticketsRedeItems, setTicketsRedeItems] = useState<Tickets.Ticket[]>([])
  const [ticketsRedeTotal, setTicketsRedeTotal] = useState(0)
  const [loadingTicketsRede, setLoadingTicketsRede] = useState(false)

  const [pageTicketsEmpModal, setPageTicketsEmpModal] = useState(1)
  const [buscaTicketsEmpModal, setBuscaTicketsEmpModal] = useState('')
  const [debouncedBuscaTicketsEmpModal, setDebouncedBuscaTicketsEmpModal] = useState('')
  const [ticketsEmpModalItems, setTicketsEmpModalItems] = useState<Tickets.Ticket[]>([])
  const [ticketsEmpModalTotal, setTicketsEmpModalTotal] = useState(0)
  const [loadingTicketsEmpModal, setLoadingTicketsEmpModal] = useState(false)

  const [pageFuncEmpModal, setPageFuncEmpModal] = useState(1)
  const [buscaFuncEmpModal, setBuscaFuncEmpModal] = useState('')
  const [debouncedBuscaFuncEmpModal, setDebouncedBuscaFuncEmpModal] = useState('')
  const [funcEmpModalItems, setFuncEmpModalItems] = useState<FuncionariosRede.Funcionario[]>([])
  const [funcEmpModalTotal, setFuncEmpModalTotal] = useState(0)
  const [loadingFuncEmpModal, setLoadingFuncEmpModal] = useState(false)

  const [tiposNegocioList, setTiposNegocioList] = useState<TiposNegocio.Tipo[]>([])
  const [modalEmpresa, setModalEmpresa] = useState(false)
  const [editingEmpresaId, setEditingEmpresaId] = useState<number | null>(null)
  const [modoEmpresa, setModoEmpresa] = useState<'create' | 'view' | 'edit'>('view')
  const [cnpjCpfEmpresa, setCnpjCpfEmpresa] = useState('')
  const [tipoNegocioIdEmpresa, setTipoNegocioIdEmpresa] = useState<number | ''>('')
  const [razaoSocialEmpresa, setRazaoSocialEmpresa] = useState('')
  const [nomeFantasiaEmpresa, setNomeFantasiaEmpresa] = useState('')
  const [inscricaoEstadualEmpresa, setInscricaoEstadualEmpresa] = useState('')
  const [enderecoEmpresa, setEnderecoEmpresa] = useState('')
  const [numeroEmpresa, setNumeroEmpresa] = useState('')
  const [complementoEmpresa, setComplementoEmpresa] = useState('')
  const [bairroEmpresa, setBairroEmpresa] = useState('')
  const [cidadeEmpresa, setCidadeEmpresa] = useState('')
  const [estadoEmpresa, setEstadoEmpresa] = useState('')
  const [cepEmpresa, setCepEmpresa] = useState('')
  const [emailEmpresa, setEmailEmpresa] = useState('')
  const [telefoneEmpresa, setTelefoneEmpresa] = useState('')
  const [respLegalNome, setRespLegalNome] = useState('')
  const [respLegalCpf, setRespLegalCpf] = useState('')
  const [respLegalRg, setRespLegalRg] = useState('')
  const [respLegalOrgaoEmissor, setRespLegalOrgaoEmissor] = useState('')
  const [respLegalNacionalidade, setRespLegalNacionalidade] = useState('')
  const [respLegalEstadoCivil, setRespLegalEstadoCivil] = useState('')
  const [respLegalCargo, setRespLegalCargo] = useState('')
  const [respLegalEmail, setRespLegalEmail] = useState('')
  const [respLegalTelefone, setRespLegalTelefone] = useState('')
  const [respLegalEndereco, setRespLegalEndereco] = useState('')
  const [respLegalNumero, setRespLegalNumero] = useState('')
  const [respLegalComplemento, setRespLegalComplemento] = useState('')
  const [respLegalBairro, setRespLegalBairro] = useState('')
  const [respLegalCidade, setRespLegalCidade] = useState('')
  const [respLegalEstado, setRespLegalEstado] = useState('')
  const [respLegalCep, setRespLegalCep] = useState('')
  const [ativoEmpresa, setAtivoEmpresa] = useState(true)
  const [savingEmpresa, setSavingEmpresa] = useState(false)
  const [loadingCnpjEmpresa, setLoadingCnpjEmpresa] = useState(false)

  const opcoesEstadoCivilEmpresa = useMemo(() => {
    const v = (respLegalEstadoCivil || '').trim()
    const base = ESTADOS_CIVIS_BR.map((c) => ({ value: c, label: c }))
    if (v !== '' && !ESTADOS_CIVIS_BR.includes(v as EstadoCivilBr)) {
      return [...base, { value: v, label: v }]
    }
    return base
  }, [respLegalEstadoCivil])

  const [modalFuncionario, setModalFuncionario] = useState(false)
  const [modoFuncionario, setModoFuncionario] = useState<'create' | 'edit'>('edit')
  const [editingFuncionarioId, setEditingFuncionarioId] = useState<number | null>(null)
  const [nomeFuncionario, setNomeFuncionario] = useState('')
  const [emailFuncionario, setEmailFuncionario] = useState('')
  const [tipoFuncionario, setTipoFuncionario] = useState<TipoFuncionario>('colaborador')
  const [ativoFuncionario, setAtivoFuncionario] = useState(true)
  const [empresaIdFuncionario, setEmpresaIdFuncionario] = useState<number | ''>('')
  const [empresaIdsFuncionario, setEmpresaIdsFuncionario] = useState<number[]>([])
  const [senhaPortalFuncionario, setSenhaPortalFuncionario] = useState('')
  const [mustChangePasswordFuncionario, setMustChangePasswordFuncionario] = useState(true)
  const [portalHabilitadoFuncionario, setPortalHabilitadoFuncionario] = useState(false)
  const [notificarEmailPortalFuncionario, setNotificarEmailPortalFuncionario] = useState(true)
  const [savingFuncionario, setSavingFuncionario] = useState(false)

  const empresasFiltradas = useMemo(() => {
    const base = incluirInativos ? empresasList : empresasList.filter((e) => e.ativo)
    let filtered = base
    if (debouncedBuscaEmpresas) {
      const q = debouncedBuscaEmpresas.toLowerCase()
      const digits = debouncedBuscaEmpresas.replace(/\D/g, '')
      filtered = base.filter(
        (e) =>
          e.nome.toLowerCase().includes(q) ||
          (e.razao_social && e.razao_social.toLowerCase().includes(q)) ||
          (e.nome_fantasia && e.nome_fantasia.toLowerCase().includes(q)) ||
          (digits.length > 0 && e.cnpj_cpf && e.cnpj_cpf.replace(/\D/g, '').includes(digits)),
      )
    }
    if (!ordemColEmpresa) return filtered
    const m = dirEmpresa === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      if (ordemColEmpresa === 'nome') return m * a.nome.localeCompare(b.nome, 'pt-BR')
      const da = (a.cnpj_cpf || '').replace(/\D/g, '')
      const db = (b.cnpj_cpf || '').replace(/\D/g, '')
      return m * da.localeCompare(db, 'pt-BR')
    })
  }, [empresasList, incluirInativos, debouncedBuscaEmpresas, ordemColEmpresa, dirEmpresa])

  const empresasPagina = useMemo(() => {
    const start = (pageEmpresas - 1) * PAGE_SIZE_PADRAO
    return empresasFiltradas.slice(start, start + PAGE_SIZE_PADRAO)
  }, [empresasFiltradas, pageEmpresas])

  const empresasDaRedeParaVinculo = empresasList.filter(
    (em) => em.ativo || em.id === empresaIdFuncionario || empresaIdsFuncionario.includes(em.id),
  )

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaFuncionarios(buscaFuncionarios.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaFuncionarios])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaEmpresas(buscaEmpresas.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaEmpresas])

  useEffect(() => {
    setPageFuncionarios(1)
  }, [debouncedBuscaFuncionarios, incluirInativos, ordemColFunc, dirFunc])

  useEffect(() => {
    setPageEmpresas(1)
  }, [debouncedBuscaEmpresas, incluirInativos, ordemColEmpresa, dirEmpresa])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaTicketsRede(buscaTicketsRede.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaTicketsRede])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaTicketsEmpModal(buscaTicketsEmpModal.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaTicketsEmpModal])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBuscaFuncEmpModal(buscaFuncEmpModal.trim()), 400)
    return () => clearTimeout(t)
  }, [buscaFuncEmpModal])

  useEffect(() => {
    setPageTicketsRede(1)
  }, [debouncedBuscaTicketsRede])

  useEffect(() => {
    setPageTicketsEmpModal(1)
  }, [debouncedBuscaTicketsEmpModal, editingEmpresaId])

  useEffect(() => {
    setPageFuncEmpModal(1)
  }, [debouncedBuscaFuncEmpModal, editingEmpresaId])

  useEffect(() => {
    if (!modalEmpresa) setAbaModalEmpresa('geral')
  }, [modalEmpresa])

  const loadFuncionarios = useCallback((override?: { busca?: string; page?: number }) => {
    if (!redeId || isNaN(redeId)) return
    const buscaEff = override?.busca !== undefined ? override.busca : debouncedBuscaFuncionarios
    const pageEff = override?.page !== undefined ? override.page : pageFuncionarios
    setLoadingFuncionarios(true)
    redes
      .getFuncionarios(redeId, {
        incluir_inativos: incluirInativos,
        busca: buscaEff.trim() || undefined,
        ...sortFuncParams,
        offset: (pageEff - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total }) => {
        setFuncionariosList(items)
        setFuncionariosTotal(total)
      })
      .finally(() => setLoadingFuncionarios(false))
  }, [debouncedBuscaFuncionarios, incluirInativos, pageFuncionarios, redeId, sortFuncParams])

  useEffect(() => {
    if (aba !== 'tickets' || !redeId || Number.isNaN(redeId)) return
    let cancelled = false
    setLoadingTicketsRede(true)
    tickets
      .list({
        rede_id: redeId,
        situacao: 'todos',
        offset: (pageTicketsRede - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
        busca: debouncedBuscaTicketsRede || undefined,
      })
      .then(({ items, total }) => {
        if (!cancelled) {
          setTicketsRedeItems(items)
          setTicketsRedeTotal(total)
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingTicketsRede(false)
      })
    return () => {
      cancelled = true
    }
  }, [aba, redeId, pageTicketsRede, debouncedBuscaTicketsRede])

  useEffect(() => {
    if (!modalEmpresa || modoEmpresa !== 'view' || abaModalEmpresa !== 'tickets' || !editingEmpresaId) return
    let cancelled = false
    setLoadingTicketsEmpModal(true)
    tickets
      .list({
        empresa_id: editingEmpresaId,
        situacao: 'todos',
        offset: (pageTicketsEmpModal - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
        busca: debouncedBuscaTicketsEmpModal || undefined,
      })
      .then(({ items, total }) => {
        if (!cancelled) {
          setTicketsEmpModalItems(items)
          setTicketsEmpModalTotal(total)
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingTicketsEmpModal(false)
      })
    return () => {
      cancelled = true
    }
  }, [
    modalEmpresa,
    modoEmpresa,
    abaModalEmpresa,
    editingEmpresaId,
    pageTicketsEmpModal,
    debouncedBuscaTicketsEmpModal,
  ])

  useEffect(() => {
    if (!modalEmpresa || modoEmpresa !== 'view' || abaModalEmpresa !== 'funcionarios' || !editingEmpresaId)
      return
    let cancelled = false
    setLoadingFuncEmpModal(true)
    funcionariosRede
      .list({
        empresa_id: editingEmpresaId,
        incluir_inativos: true,
        busca: debouncedBuscaFuncEmpModal || undefined,
        offset: (pageFuncEmpModal - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total }) => {
        if (!cancelled) {
          setFuncEmpModalItems(items)
          setFuncEmpModalTotal(total)
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingFuncEmpModal(false)
      })
    return () => {
      cancelled = true
    }
  }, [
    modalEmpresa,
    modoEmpresa,
    abaModalEmpresa,
    editingEmpresaId,
    pageFuncEmpModal,
    debouncedBuscaFuncEmpModal,
  ])

  function loadRedeEEmpresas() {
    if (!redeId || isNaN(redeId)) return
    Promise.all([
      redes.get(redeId),
      coletarTodasPaginas<Empresas.Empresa>((o, l) =>
        empresas.list<Empresas.Empresa>({ rede_id: redeId, incluir_inativos: true, offset: o, limit: l }),
      ),
    ])
      .then(([r, e]) => {
        setRede(r)
        setEmpresasList(e)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setRede(null)
          setEmpresasList([])
          return
        }
        const msg = interpretarFalhaCarregamento(err, 'Rede não encontrada.')
        toast.showWarning([msg.titulo, msg.detalhe].filter(Boolean).join(' '))
      })
  }

  useEffect(() => {
    if (!redeId || isNaN(redeId)) return
    let cancelled = false
    setLoading(true)
    setLoadFailure(null)
    setForbidden(false)
    Promise.all([
      redes.get(redeId),
      coletarTodasPaginas<Empresas.Empresa>((o, l) =>
        empresas.list<Empresas.Empresa>({ rede_id: redeId, incluir_inativos: true, offset: o, limit: l }),
      ),
    ])
      .then(([r, e]) => {
        if (cancelled) return
        setRede(r)
        setEmpresasList(e)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setRede(null)
          setEmpresasList([])
          return
        }
        setLoadFailure(interpretarFalhaCarregamento(err, 'Rede não encontrada.'))
        setRede(null)
        setEmpresasList([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [redeId, toast])

  useEffect(() => {
    loadFuncionarios()
  }, [loadFuncionarios])

  useEffect(() => {
    coletarTodasPaginas<TiposNegocio.Tipo>((o, l) =>
      tiposNegocio.list({ incluir_inativos: true, offset: o, limit: l }),
    ).then(setTiposNegocioList)
  }, [])

  function openNovaEmpresa() {
    setEditingEmpresaId(null)
    setModoEmpresa('create')
    setCnpjCpfEmpresa('')
    setTipoNegocioIdEmpresa('')
    setRazaoSocialEmpresa('')
    setNomeFantasiaEmpresa('')
    setInscricaoEstadualEmpresa('')
    setEnderecoEmpresa('')
    setNumeroEmpresa('')
    setComplementoEmpresa('')
    setBairroEmpresa('')
    setCidadeEmpresa('')
    setEstadoEmpresa('')
    setCepEmpresa('')
    setEmailEmpresa('')
    setTelefoneEmpresa('')
    setRespLegalNome('')
    setRespLegalCpf('')
    setRespLegalRg('')
    setRespLegalOrgaoEmissor('')
    setRespLegalNacionalidade('')
    setRespLegalEstadoCivil('')
    setRespLegalCargo('')
    setRespLegalEmail('')
    setRespLegalTelefone('')
    setRespLegalEndereco('')
    setRespLegalNumero('')
    setRespLegalComplemento('')
    setRespLegalBairro('')
    setRespLegalCidade('')
    setRespLegalEstado('')
    setRespLegalCep('')
    setAtivoEmpresa(true)
    setAbaModalEmpresa('geral')
    setModalEmpresa(true)
  }

  function openEditEmpresa(e: Empresas.Empresa) {
    setEditingEmpresaId(e.id)
    setModoEmpresa('edit')
    setCnpjCpfEmpresa(e.cnpj_cpf ? maskCnpjCpf(e.cnpj_cpf) : '')
    setTipoNegocioIdEmpresa(e.tipo_negocio_id ?? '')
    setRazaoSocialEmpresa(e.razao_social ?? '')
    setNomeFantasiaEmpresa(e.nome_fantasia ?? '')
    setInscricaoEstadualEmpresa(e.inscricao_estadual ?? '')
    setEnderecoEmpresa(e.endereco ?? '')
    setNumeroEmpresa(e.numero ?? '')
    setComplementoEmpresa(e.complemento ?? '')
    setBairroEmpresa(e.bairro ?? '')
    setCidadeEmpresa(e.cidade ?? '')
    setEstadoEmpresa((e.estado ?? '').toUpperCase().slice(0, 2))
    setCepEmpresa(maskCep(e.cep ?? ''))
    setEmailEmpresa(e.email ?? '')
    setTelefoneEmpresa(maskTelefoneBr(e.telefone ?? ''))
    setRespLegalNome(e.resp_legal_nome ?? '')
    setRespLegalCpf(e.resp_legal_cpf ? maskCnpjCpf(e.resp_legal_cpf) : '')
    setRespLegalRg(e.resp_legal_rg ?? '')
    setRespLegalOrgaoEmissor(e.resp_legal_orgao_emissor ?? '')
    setRespLegalNacionalidade(e.resp_legal_nacionalidade ?? '')
    setRespLegalEstadoCivil(e.resp_legal_estado_civil ?? '')
    setRespLegalCargo(e.resp_legal_cargo ?? '')
    setRespLegalEmail(e.resp_legal_email ?? '')
    setRespLegalTelefone(maskTelefoneBr(e.resp_legal_telefone ?? ''))
    setRespLegalEndereco(e.resp_legal_endereco ?? '')
    setRespLegalNumero(e.resp_legal_numero ?? '')
    setRespLegalComplemento(e.resp_legal_complemento ?? '')
    setRespLegalBairro(e.resp_legal_bairro ?? '')
    setRespLegalCidade(e.resp_legal_cidade ?? '')
    setRespLegalEstado((e.resp_legal_estado ?? '').toUpperCase().slice(0, 2))
    setRespLegalCep(maskCep(e.resp_legal_cep ?? ''))
    setAtivoEmpresa(e.ativo)
    setAbaModalEmpresa('geral')
    setModalEmpresa(true)
  }

  function openViewEmpresa(e: Empresas.Empresa) {
    navigate(`/empresas/${e.id}`, { state: { voltarPara: `/redes/${redeId}` } })
  }

  async function handleConsultarCnpjEmpresa() {
    const d = digitsOnly(cnpjCpfEmpresa)
    if (!isCnpj(cnpjCpfEmpresa)) {
      toast.showWarning('Informe um CNPJ com 14 dígitos para consultar.')
      return
    }
    setLoadingCnpjEmpresa(true)
    try {
      const data = await empresas.consultarCnpj(d)
      setRazaoSocialEmpresa(data.razao_social ?? '')
      setNomeFantasiaEmpresa(data.nome_fantasia ?? '')
      setEnderecoEmpresa(data.endereco ?? '')
      setNumeroEmpresa(data.numero ?? '')
      setComplementoEmpresa(data.complemento ?? '')
      setBairroEmpresa(data.bairro ?? '')
      setCidadeEmpresa(data.cidade ?? '')
      setEstadoEmpresa((data.estado ?? '').toUpperCase().slice(0, 2))
      setCepEmpresa(maskCep(data.cep ?? ''))
      setEmailEmpresa(data.email ?? '')
      setTelefoneEmpresa(maskTelefoneBr(data.telefone ?? ''))
      toast.showSuccess('Dados preenchidos.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Erro ao consultar CNPJ.'))
    } finally {
      setLoadingCnpjEmpresa(false)
    }
  }

  async function handleSubmitEmpresa(ev: React.FormEvent) {
    ev.preventDefault()
    const nomeGravado = nomeParaApiEmpresa(nomeFantasiaEmpresa, razaoSocialEmpresa)
    if (!nomeGravado) {
      toast.showWarning('Informe o nome fantasia ou a razão social.')
      return
    }
    setSavingEmpresa(true)
    try {
      const payload = {
        rede_id: redeId,
        tipo_negocio_id: tipoNegocioIdEmpresa === '' ? null : Number(tipoNegocioIdEmpresa),
        nome: nomeGravado,
        cnpj_cpf: cnpjCpfEmpresa.replace(/\D/g, '') || null,
        razao_social: razaoSocialEmpresa.trim() || null,
        nome_fantasia: nomeFantasiaEmpresa.trim() || null,
        inscricao_estadual: inscricaoEstadualEmpresa.trim() || null,
        endereco: enderecoEmpresa.trim() || null,
        numero: numeroEmpresa.trim() || null,
        complemento: complementoEmpresa.trim() || null,
        bairro: bairroEmpresa.trim() || null,
        cidade: cidadeEmpresa.trim() || null,
        estado: estadoEmpresa.trim() || null,
        cep: cepEmpresa.replace(/\D/g, '') || null,
        email: emailEmpresa.trim() || null,
        telefone: digitsOnly(telefoneEmpresa) || null,
        resp_legal_nome: respLegalNome.trim() || null,
        resp_legal_cpf: digitsOnly(respLegalCpf) || null,
        resp_legal_rg: respLegalRg.trim() || null,
        resp_legal_orgao_emissor: respLegalOrgaoEmissor.trim() || null,
        resp_legal_nacionalidade: respLegalNacionalidade.trim() || null,
        resp_legal_estado_civil: respLegalEstadoCivil.trim() || null,
        resp_legal_cargo: respLegalCargo.trim() || null,
        resp_legal_email: respLegalEmail.trim() || null,
        resp_legal_telefone: digitsOnly(respLegalTelefone) || null,
        resp_legal_endereco: respLegalEndereco.trim() || null,
        resp_legal_numero: respLegalNumero.trim() || null,
        resp_legal_complemento: respLegalComplemento.trim() || null,
        resp_legal_bairro: respLegalBairro.trim() || null,
        resp_legal_cidade: respLegalCidade.trim() || null,
        resp_legal_estado: respLegalEstado.trim() || null,
        resp_legal_cep: respLegalCep.replace(/\D/g, '') || null,
        ativo: ativoEmpresa,
      }
      if (editingEmpresaId) {
        await empresas.update(editingEmpresaId, payload)
        toast.showSuccess('Empresa atualizada.')
      } else {
        await empresas.create(payload)
        toast.showSuccess('Empresa cadastrada.')
      }
      setModalEmpresa(false)
      loadRedeEEmpresas()
      loadFuncionarios()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a empresa.'))
    } finally {
      setSavingEmpresa(false)
    }
  }

  async function handleDeleteEmpresa(empresaId: number) {
    if (!confirm('Excluir esta empresa?')) return
    try {
      await empresas.delete(empresaId)
      loadRedeEEmpresas()
      loadFuncionarios()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir a empresa.'))
    }
  }

  function preencherFormFuncionario(f: FuncionarioListaItem) {
    setNomeFuncionario(f.nome)
    setEmailFuncionario(f.email ?? '')
    setTipoFuncionario((f.tipo as TipoFuncionario) || 'colaborador')
    setAtivoFuncionario(f.ativo)
    setEmpresaIdFuncionario(f.empresa_id ?? '')
    setEmpresaIdsFuncionario(f.empresa_ids ?? [])
    setSenhaPortalFuncionario('')
    setMustChangePasswordFuncionario(f.must_change_password !== false)
    setPortalHabilitadoFuncionario(Boolean(f.portal_habilitado))
    setNotificarEmailPortalFuncionario(f.notificar_email_portal !== false)
  }

  function verFuncionarioDetalhe(f: FuncionarioListaItem) {
    navigate(`/funcionarios-rede/${f.id}`)
  }

  function openEditFuncionario(f: FuncionarioListaItem) {
    setEditingFuncionarioId(f.id)
    setModoFuncionario('edit')
    preencherFormFuncionario(f)
    setAba('funcionarios')
    setModalFuncionario(true)
  }

  function openNovoFuncionario() {
    setEditingFuncionarioId(null)
    setModoFuncionario('create')
    setNomeFuncionario('')
    setEmailFuncionario('')
    setTipoFuncionario('colaborador')
    setAtivoFuncionario(true)
    setEmpresaIdFuncionario('')
    setEmpresaIdsFuncionario([])
    setSenhaPortalFuncionario('')
    setMustChangePasswordFuncionario(true)
    setPortalHabilitadoFuncionario(false)
    setNotificarEmailPortalFuncionario(true)
    setAba('funcionarios')
    setModalFuncionario(true)
  }

  function fecharModalFuncionario() {
    setModalFuncionario(false)
    setModoFuncionario('edit')
    setEditingFuncionarioId(null)
    setSenhaPortalFuncionario('')
    setMustChangePasswordFuncionario(true)
    setPortalHabilitadoFuncionario(false)
    setNotificarEmailPortalFuncionario(true)
  }

  function toggleEmpresaFuncionario(id: number) {
    setEmpresaIdsFuncionario((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function handleSubmitFuncionario(ev: React.FormEvent) {
    ev.preventDefault()
    const empresasNaRede = empresasList.filter((em) => em.rede_id === redeId)
    if (tipoFuncionario === 'colaborador') {
      const em = empresasList.find((x) => x.id === empresaIdFuncionario)
      if (!em || em.rede_id !== redeId) {
        toast.showWarning('Selecione uma empresa desta rede.')
        return
      }
    }
    if (tipoFuncionario === 'supervisor') {
      if (!empresaIdsFuncionario.length) {
        toast.showWarning('Marque ao menos uma empresa da rede.')
        return
      }
      const invalid = empresaIdsFuncionario.some((eid) => !empresasNaRede.some((e) => e.id === eid))
      if (invalid) {
        toast.showWarning('Todas as empresas do supervisor devem ser desta rede.')
        return
      }
    }
    const senhaPortal = senhaPortalFuncionario.trim()
    if (senhaPortal) {
      if (!emailFuncionario.trim()) {
        toast.showWarning('Informe o e-mail do funcionário para habilitar o portal.')
        return
      }
      if (senhaPortal.length < 8) {
        toast.showWarning('A senha do portal deve ter ao menos 8 caracteres.')
        return
      }
    }
    const escopoEmpresas = tipoFuncionario === 'socio' ? 'all' : 'selected'
    setSavingFuncionario(true)
    try {
      const payload: FuncionariosRede.Create = {
        nome: nomeFuncionario.trim(),
        email: emailFuncionario.trim(),
        tipo: tipoFuncionario,
        ativo: ativoFuncionario,
        escopo_empresas: escopoEmpresas,
        rede_id: redeId,
        empresa_id: tipoFuncionario === 'colaborador' ? Number(empresaIdFuncionario) : undefined,
        empresa_ids: tipoFuncionario === 'supervisor' ? empresaIdsFuncionario : undefined,
        must_change_password: mustChangePasswordFuncionario,
        ...(senhaPortal ? { senha_portal: senhaPortal } : {}),
        ...(editingFuncionarioId
          ? { notificar_email_portal: notificarEmailPortalFuncionario }
          : {}),
      }
      const eraEdicao = editingFuncionarioId != null
      let idDetalhe: number
      if (editingFuncionarioId) {
        await funcionariosRede.update(editingFuncionarioId, payload)
        toast.showSuccess('Funcionário atualizado.')
        idDetalhe = editingFuncionarioId
      } else {
        const criado = await funcionariosRede.create(payload)
        toast.showSuccess('Funcionário cadastrado.')
        idDetalhe = criado.id
      }
      fecharModalFuncionario()
      loadRedeEEmpresas()
      if (eraEdicao) {
        loadFuncionarios()
      } else {
        setBuscaFuncionarios('')
        setDebouncedBuscaFuncionarios('')
        setPageFuncionarios(1)
        loadFuncionarios({ busca: '', page: 1 })
      }
      navigate(`/funcionarios-rede/${idDetalhe}`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o funcionário.'))
    } finally {
      setSavingFuncionario(false)
    }
  }

  async function handleDeleteFuncionario(funcionarioId: number) {
    if (!confirm('Excluir este funcionário?')) return
    try {
      await funcionariosRede.delete(funcionarioId)
      loadRedeEEmpresas()
      loadFuncionarios()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível excluir o funcionário.'))
    }
  }

  if (!id || isNaN(redeId)) {
    return (
      <CarregamentoFalhou
        titulo="Rede não encontrada."
        detalhe="O identificador na URL é inválido."
        onVoltar={voltarAnterior}
      />
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para acessar esta rede."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/redes"
          voltarLabel="Voltar para Redes"
        />
      </div>
    )
  }

  if (loading && !rede && !loadFailure) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <div className="h-4 w-24 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-9 w-2/3 max-w-md animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  if (loadFailure) {
    return <CarregamentoFalhou titulo={loadFailure.titulo} detalhe={loadFailure.detalhe} onVoltar={voltarAnterior} />
  }

  if (!rede && !loading) {
    return (
      <CarregamentoFalhou titulo="Rede não encontrada." onVoltar={voltarAnterior} />
    )
  }

  if (!rede) {
    return null
  }

  const linkRedes = <VoltarButton onClick={voltarAnterior} />

  const tituloEmpresaModal =
    nomeFantasiaEmpresa.trim() || razaoSocialEmpresa.trim() || (modoEmpresa === 'create' ? '' : 'Empresa')
  const labelEmpresaModal = modoEmpresa === 'create' ? 'Nova empresa' : tituloEmpresaModal || 'Empresa'
  const labelFuncionarioModal =
    modoFuncionario === 'create' ? 'Novo funcionário' : nomeFuncionario || 'Funcionário'
  const isViewEmpresa = modoEmpresa === 'view'
  const tipoNegocioNomeEmpresa =
    tipoNegocioIdEmpresa === '' ? '' : tiposNegocioList.find((t) => t.id === Number(tipoNegocioIdEmpresa))?.nome ?? ''

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <div className="flex flex-wrap items-center gap-3">
        <nav aria-label="breadcrumb" className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          {linkRedes}
          <span aria-hidden className="text-slate-300 dark:text-slate-600">
            /
          </span>
          <button
            type="button"
            onClick={() => {
              if (modalEmpresa) {
                setModoEmpresa('view')
                setAba('empresas')
              }
              setModalEmpresa(false)
              fecharModalFuncionario()
            }}
            className="font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
          >
            {rede.nome}
          </button>
          {modalEmpresa && (
            <>
              <span aria-hidden className="text-slate-300 dark:text-slate-600">
                /
              </span>
              <span className="truncate font-semibold text-slate-800 dark:text-slate-100">{labelEmpresaModal}</span>
            </>
          )}
          {modalFuncionario && (
            <>
              <span aria-hidden className="text-slate-300 dark:text-slate-600">
                /
              </span>
              <span className="truncate font-semibold text-slate-800 dark:text-slate-100">{labelFuncionarioModal}</span>
            </>
          )}
        </nav>
      </div>

      {!modalEmpresa && !modalFuncionario && (
        <div className="border-b border-slate-200 dark:border-slate-600">
          <nav className="flex gap-1 sm:gap-2" aria-label="Seções da rede">
            <button
              type="button"
              onClick={() => setAba('empresas')}
              aria-current={aba === 'empresas' ? 'page' : undefined}
              className={
                aba === 'empresas'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
              }
            >
              Empresas
            </button>
            <button
              type="button"
              onClick={() => setAba('funcionarios')}
              aria-current={aba === 'funcionarios' ? 'page' : undefined}
              className={
                aba === 'funcionarios'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
              }
            >
              Funcionários
            </button>
            <button
              type="button"
              onClick={() => setAba('analises')}
              aria-current={aba === 'analises' ? 'page' : undefined}
              className={
                aba === 'analises'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
              }
            >
              Análises
            </button>
            <button
              type="button"
              onClick={() => setAba('tickets')}
              aria-current={aba === 'tickets' ? 'page' : undefined}
              className={
                aba === 'tickets'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
              }
            >
              Tickets
            </button>
          </nav>
        </div>
      )}

      {aba === 'empresas' && modalEmpresa && (
        <Card title={isViewEmpresa ? 'Detalhe da empresa' : editingEmpresaId ? 'Editar empresa' : 'Nova empresa'}>
          {isViewEmpresa ? (
            <div className="space-y-6">
              <div className="border-b border-slate-200 dark:border-slate-600">
                <nav className="flex flex-wrap gap-1 sm:gap-2" aria-label="Seções do cadastro">
                  <button
                    type="button"
                    onClick={() => setAbaModalEmpresa('geral')}
                    aria-current={abaModalEmpresa === 'geral' ? 'page' : undefined}
                    className={
                      abaModalEmpresa === 'geral'
                        ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                        : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
                    }
                  >
                    Geral
                  </button>
                  <button
                    type="button"
                    onClick={() => setAbaModalEmpresa('tickets')}
                    aria-current={abaModalEmpresa === 'tickets' ? 'page' : undefined}
                    className={
                      abaModalEmpresa === 'tickets'
                        ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                        : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
                    }
                  >
                    Tickets
                  </button>
                  <button
                    type="button"
                    onClick={() => setAbaModalEmpresa('funcionarios')}
                    aria-current={abaModalEmpresa === 'funcionarios' ? 'page' : undefined}
                    className={
                      abaModalEmpresa === 'funcionarios'
                        ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                        : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
                    }
                  >
                    Funcionários
                  </button>
                  <button
                    type="button"
                    onClick={() => setAbaModalEmpresa('pdvs')}
                    aria-current={abaModalEmpresa === 'pdvs' ? 'page' : undefined}
                    className={
                      abaModalEmpresa === 'pdvs'
                        ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                        : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-white/30 dark:hover:text-slate-200'
                    }
                  >
                    PDVs
                  </button>
                </nav>
              </div>

              {abaModalEmpresa === 'geral' && (
                <>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Tipo de negócio</p>
                      <p className="text-sm text-slate-900 dark:text-slate-100">{tipoNegocioNomeEmpresa || '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">CNPJ / CPF</p>
                      <p className="text-sm break-all text-slate-900 dark:text-slate-100">{cnpjCpfEmpresa || '—'}</p>
                    </div>

                    <div className="sm:col-span-2">
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Nome nas listas</p>
                      <p className="text-sm text-slate-900 dark:text-slate-100">
                        {nomeParaApiEmpresa(nomeFantasiaEmpresa, razaoSocialEmpresa) || '—'}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        Usa o nome fantasia; se vazio, a razão social.
                      </p>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Razão social</p>
                      <p className="text-sm text-slate-900 dark:text-slate-100">{razaoSocialEmpresa || '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Nome fantasia</p>
                      <p className="text-sm text-slate-900 dark:text-slate-100">{nomeFantasiaEmpresa || '—'}</p>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Inscrição estadual</p>
                      <p className="text-sm text-slate-900 dark:text-slate-100">{inscricaoEstadualEmpresa || '—'}</p>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">E-mail</p>
                      <p className="text-sm text-slate-900 dark:text-slate-100">{emailEmpresa || '—'}</p>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Telefone</p>
                      <p className="text-sm text-slate-900 dark:text-slate-100">
                        {formatTelefoneBrExibicao(telefoneEmpresa) || '—'}
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">Endereço</p>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Logradouro</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{enderecoEmpresa || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Número</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{numeroEmpresa || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Complemento</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{complementoEmpresa || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Bairro</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{bairroEmpresa || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Cidade</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{cidadeEmpresa || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">UF</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{estadoEmpresa || '—'}</p>
                      </div>
                      <div className="sm:col-span-1">
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">CEP</p>
                        <p className="text-sm font-mono tabular-nums text-slate-900 dark:text-slate-100">
                          {maskCep(cepEmpresa) || '—'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-slate-200 pt-4 dark:border-slate-800">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Responsável legal
                    </p>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Nome completo</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalNome || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">CPF</p>
                        <p className="text-sm font-mono tabular-nums text-slate-900 dark:text-slate-100">
                          {respLegalCpf || '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">RG</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalRg || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Órgão emissor</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalOrgaoEmissor || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Nacionalidade</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalNacionalidade || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Estado civil</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">
                          {respLegalEstadoCivil.trim() || '—'}
                        </p>
                      </div>
                      <div className="sm:col-span-2">
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                          Cargo / qualificação na empresa
                        </p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalCargo || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">E-mail</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalEmail || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Telefone</p>
                        <p className="text-sm text-slate-900 dark:text-slate-100">
                          {formatTelefoneBrExibicao(respLegalTelefone) || '—'}
                        </p>
                      </div>
                      <div className="sm:col-span-2">
                        <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">Endereço residencial</p>
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                          <div className="sm:col-span-3">
                            <p className="text-xs text-slate-500 dark:text-slate-400">Logradouro</p>
                            <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalEndereco || '—'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 dark:text-slate-400">Número</p>
                            <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalNumero || '—'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 dark:text-slate-400">Complemento</p>
                            <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalComplemento || '—'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 dark:text-slate-400">Bairro</p>
                            <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalBairro || '—'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 dark:text-slate-400">Cidade</p>
                            <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalCidade || '—'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 dark:text-slate-400">UF</p>
                            <p className="text-sm text-slate-900 dark:text-slate-100">{respLegalEstado || '—'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 dark:text-slate-400">CEP</p>
                            <p className="text-sm font-mono tabular-nums text-slate-900 dark:text-slate-100">
                              {maskCep(respLegalCep) || '—'}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {abaModalEmpresa === 'tickets' && editingEmpresaId != null && (
                <>
                  <BarraBuscaPaginacao
                    busca={buscaTicketsEmpModal}
                    onBuscaChange={setBuscaTicketsEmpModal}
                    placeholder="Protocolo ou assunto..."
                    page={pageTicketsEmpModal}
                    total={ticketsEmpModalTotal}
                    onPageChange={setPageTicketsEmpModal}
                    disabled={loadingTicketsEmpModal}
                  />
                  <TicketsTabelaContexto
                    items={ticketsEmpModalItems}
                    loading={loadingTicketsEmpModal}
                    showEmpresaColumn={false}
                    emptyMessage="Nenhum ticket para esta empresa."
                  />
                </>
              )}

              {abaModalEmpresa === 'funcionarios' && editingEmpresaId != null && (
                <>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Funcionários da rede associados a esta empresa (sócio, supervisor ou colaborador).
                  </p>
                  <BarraBuscaPaginacao
                    busca={buscaFuncEmpModal}
                    onBuscaChange={setBuscaFuncEmpModal}
                    placeholder="Nome ou e-mail..."
                    page={pageFuncEmpModal}
                    total={funcEmpModalTotal}
                    onPageChange={setPageFuncEmpModal}
                    disabled={loadingFuncEmpModal}
                    extra={
                      <Link
                        to={`/funcionarios-rede/novo?empresa_id=${editingEmpresaId}&rede_id=${redeId}`}
                      >
                        <Button type="button">Adicionar funcionário</Button>
                      </Link>
                    }
                  />
                  <FuncionariosEmpresaLista
                    items={funcEmpModalItems}
                    loading={loadingFuncEmpModal}
                    emptyMessage="Nenhum funcionário vinculado a esta empresa."
                    emptyAction={
                      <Link
                        to={`/funcionarios-rede/novo?empresa_id=${editingEmpresaId}&rede_id=${redeId}`}
                        className="mt-3 inline-block"
                      >
                        <Button type="button">Cadastrar ou vincular funcionário</Button>
                      </Link>
                    }
                  />
                </>
              )}

              {abaModalEmpresa === 'pdvs' && editingEmpresaId != null && (
                <EmpresaPdvsPanel empresaId={editingEmpresaId} />
              )}

              <div className="flex items-center justify-between border-t border-slate-200 pt-4 dark:border-slate-800">
                <span
                  className={`rounded-md px-2 py-1 text-xs font-medium ${
                    ativoEmpresa
                      ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300'
                      : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                  }`}
                >
                  {ativoEmpresa ? 'Ativo' : 'Inativo'}
                </span>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setModoEmpresa('view')
                      setAba('empresas')
                      setModalEmpresa(false)
                    }}
                    aria-label="Voltar para a lista de empresas"
                    className="px-3"
                  >
                    <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <path d="M15 18l-6-6 6-6" />
                    </svg>
                    Voltar
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => setModoEmpresa('edit')}
                    className="px-3"
                  >
                    <IconPencil ariaHidden={false} />
                    Editar
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmitEmpresa} className="space-y-5 sm:space-y-6">
              <div className="space-y-5 pb-24 sm:space-y-6">
                <FormSection title="Classificação">
                  <Select
                    label="Tipo de negócio"
                    value={tipoNegocioIdEmpresa}
                    onChange={(v) => setTipoNegocioIdEmpresa(v === '' ? '' : Number(v))}
                    options={tiposNegocioList.map((t) => ({ value: t.id, label: t.nome }))}
                    includeEmpty
                    emptyLabel="Selecione"
                    placeholder="Selecione"
                  />
                </FormSection>

                <FormSection title="Documento e nomes" description={EMPRESA_SECAO_DOCUMENTO_NOMES}>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:items-end lg:gap-5">
                    <Input
                      id="rede-empresa-cnpj"
                      label="CNPJ / CPF"
                      inputMode="numeric"
                      placeholder="00.000.000/0001-00"
                      value={cnpjCpfEmpresa}
                      onChange={(e) => setCnpjCpfEmpresa(maskCnpjCpf(e.target.value))}
                      endAdornment={
                        <button
                          type="button"
                          onClick={handleConsultarCnpjEmpresa}
                          disabled={loadingCnpjEmpresa}
                          className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 disabled:pointer-events-none disabled:opacity-45 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                          aria-label="Consultar CNPJ na Receita"
                        >
                          {loadingCnpjEmpresa ? (
                            <span
                              className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                              aria-hidden
                            />
                          ) : (
                            <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                          )}
                        </button>
                      }
                    />
                    <Input
                      label="Inscrição estadual"
                      value={inscricaoEstadualEmpresa}
                      onChange={(e) =>
                        setInscricaoEstadualEmpresa(maskInscricaoEstadual(e.target.value))
                      }
                    />
                  </div>
                  <Input
                    label="Razão social"
                    value={razaoSocialEmpresa}
                    onChange={(e) => setRazaoSocialEmpresa(e.target.value)}
                  />
                  <Input
                    label="Nome fantasia"
                    value={nomeFantasiaEmpresa}
                    onChange={(e) => setNomeFantasiaEmpresa(e.target.value)}
                  />
                </FormSection>

                <FormSection title="Endereço">
                  <Input label="Logradouro" value={enderecoEmpresa} onChange={(e) => setEnderecoEmpresa(e.target.value)} />
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    <Input label="Número" value={numeroEmpresa} onChange={(e) => setNumeroEmpresa(e.target.value)} />
                    <Input label="Complemento" value={complementoEmpresa} onChange={(e) => setComplementoEmpresa(e.target.value)} />
                    <Input label="Bairro" value={bairroEmpresa} onChange={(e) => setBairroEmpresa(e.target.value)} />
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    <SelectUf
                      label="UF"
                      id="rede-empresa-uf"
                      value={estadoEmpresa}
                      onChange={(uf) => {
                        setEstadoEmpresa(uf)
                        setCidadeEmpresa('')
                      }}
                    />
                    <SelectCidadeUf
                      label="Cidade"
                      id="rede-empresa-cidade"
                      uf={estadoEmpresa}
                      value={cidadeEmpresa}
                      onChange={setCidadeEmpresa}
                    />
                    <InputCepComBusca
                      id="rede-empresa-cep"
                      label="CEP"
                      value={cepEmpresa}
                      onChange={setCepEmpresa}
                      onEnderecoCompleto={(r) => {
                        setEnderecoEmpresa(r.logradouro || '')
                        setBairroEmpresa(r.bairro || '')
                        setCidadeEmpresa(r.localidade || '')
                        setEstadoEmpresa((r.uf || '').toUpperCase().slice(0, 2))
                        if (r.complemento) setComplementoEmpresa(r.complemento)
                      }}
                    />
                  </div>
                </FormSection>

                <FormSection title="Contato">
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-5">
                    <Input label="E-mail" type="email" value={emailEmpresa} onChange={(e) => setEmailEmpresa(e.target.value)} />
                    <Input
                      label="Telefone"
                      inputMode="tel"
                      value={telefoneEmpresa}
                      maxLength={15}
                      onChange={(e) => setTelefoneEmpresa(maskTelefoneBr(e.target.value))}
                    />
                  </div>
                </FormSection>

                <FormSection title="Responsável legal" description={EMPRESA_SECAO_RESPONSAVEL_LEGAL}>
                  <Input label="Nome completo" value={respLegalNome} onChange={(e) => setRespLegalNome(e.target.value)} />
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:gap-5">
                    <Input
                      label="CPF"
                      inputMode="numeric"
                      placeholder="000.000.000-00"
                      maxLength={14}
                      value={respLegalCpf}
                      onChange={(e) => setRespLegalCpf(maskCnpjCpf(e.target.value))}
                    />
                    <Input label="RG" value={respLegalRg} onChange={(e) => setRespLegalRg(e.target.value)} />
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:gap-5">
                    <Input
                      label="Órgão emissor"
                      placeholder="Ex.: SSP/SP"
                      value={respLegalOrgaoEmissor}
                      onChange={(e) => setRespLegalOrgaoEmissor(e.target.value)}
                    />
                    <Input
                      label="Nacionalidade"
                      placeholder="Ex.: Brasileira"
                      value={respLegalNacionalidade}
                      onChange={(e) => setRespLegalNacionalidade(e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:gap-5">
                    <Select
                      label="Estado civil"
                      value={respLegalEstadoCivil}
                      onChange={(v) => setRespLegalEstadoCivil(v === '' ? '' : String(v))}
                      options={opcoesEstadoCivilEmpresa}
                      includeEmpty
                      emptyLabel="Selecione"
                      placeholder="Selecione"
                    />
                    <Input
                      label="Cargo na empresa"
                      placeholder="Ex.: Sócio administrador"
                      value={respLegalCargo}
                      onChange={(e) => setRespLegalCargo(e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:gap-5">
                    <Input label="E-mail" type="email" value={respLegalEmail} onChange={(e) => setRespLegalEmail(e.target.value)} />
                    <Input
                      label="Telefone"
                      inputMode="tel"
                      value={respLegalTelefone}
                      maxLength={15}
                      onChange={(e) => setRespLegalTelefone(maskTelefoneBr(e.target.value))}
                    />
                  </div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Endereço residencial
                  </p>
                  <Input label="Logradouro" value={respLegalEndereco} onChange={(e) => setRespLegalEndereco(e.target.value)} />
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    <Input label="Número" value={respLegalNumero} onChange={(e) => setRespLegalNumero(e.target.value)} />
                    <Input label="Complemento" value={respLegalComplemento} onChange={(e) => setRespLegalComplemento(e.target.value)} />
                    <Input label="Bairro" value={respLegalBairro} onChange={(e) => setRespLegalBairro(e.target.value)} />
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    <SelectUf
                      label="UF"
                      id="rede-empresa-resp-uf"
                      value={respLegalEstado}
                      onChange={(uf) => {
                        setRespLegalEstado(uf)
                        setRespLegalCidade('')
                      }}
                    />
                    <SelectCidadeUf
                      label="Cidade"
                      id="rede-empresa-resp-cidade"
                      uf={respLegalEstado}
                      value={respLegalCidade}
                      onChange={setRespLegalCidade}
                    />
                    <InputCepComBusca
                      id="rede-empresa-resp-cep"
                      label="CEP"
                      value={respLegalCep}
                      onChange={setRespLegalCep}
                      onEnderecoCompleto={(r) => {
                        setRespLegalEndereco(r.logradouro || '')
                        setRespLegalBairro(r.bairro || '')
                        setRespLegalCidade(r.localidade || '')
                        setRespLegalEstado((r.uf || '').toUpperCase().slice(0, 2))
                        if (r.complemento) setRespLegalComplemento(r.complemento)
                      }}
                    />
                  </div>
                </FormSection>

                <FormSection title="Situação no sistema">
                  <Switch
                    bare
                    showStatusPill
                    checked={ativoEmpresa}
                    onCheckedChange={setAtivoEmpresa}
                    label="Empresa ativa"
                    description={EMPRESA_HINT_ATIVA}
                  />
                </FormSection>
              </div>

              <div className="sticky bottom-0 -mx-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-800 dark:bg-slate-900">
                <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <Button
                    type="button"
                    variant="cancel"
                    className="w-full sm:w-auto"
                    onClick={() => setModalEmpresa(false)}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" loading={savingEmpresa} className="w-full sm:w-auto">
                    Salvar
                  </Button>
                </div>
              </div>
            </form>
          )}
        </Card>
      )}

      {aba === 'empresas' && !modalEmpresa && (
        <Card>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Empresas da rede</h2>
            <Button onClick={openNovaEmpresa}>Nova empresa</Button>
          </div>
          <BarraBuscaPaginacao
            busca={buscaEmpresas}
            onBuscaChange={setBuscaEmpresas}
            placeholder="Buscar empresa (nome, razão social, CNPJ...)"
            page={pageEmpresas}
            total={empresasFiltradas.length}
            onPageChange={setPageEmpresas}
            disabled={loading}
            extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
          />
          {loading && !empresasList.length ? (
            <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
          ) : empresasFiltradas.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400">Nenhuma empresa nesta rede.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
                    <CabecalhoOrdenavel
                      coluna="nome"
                      rotulo="Empresa"
                      ordenarPor={ordemColEmpresa}
                      ordem={dirEmpresa}
                      aoOrdenar={aoOrdEmpresa}
                    />
                    <CabecalhoOrdenavel
                      coluna="cnpj_cpf"
                      rotulo="CNPJ / CPF"
                      ordenarPor={ordemColEmpresa}
                      ordem={dirEmpresa}
                      aoOrdenar={aoOrdEmpresa}
                    />
                    <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                      <span className="sr-only">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {empresasPagina.map((e) => (
                    <tr
                      key={e.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => openViewEmpresa(e)}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' || ev.key === ' ') {
                          ev.preventDefault()
                          openViewEmpresa(e)
                        }
                      }}
                      className="cursor-pointer transition-colors hover:bg-slate-50/80 focus:outline-none focus-visible:bg-slate-100/80 dark:hover:bg-white/50"
                    >
                      <td className="px-4 py-3.5 sm:px-6">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`truncate font-medium ${e.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400 dark:text-slate-500'}`}
                          >
                            {e.nome}
                          </span>
                          {!e.ativo && (
                            <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600">Inativo</span>
                          )}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs text-slate-600 tabular-nums sm:px-6 dark:text-slate-300">
                        {e.cnpj_cpf ? maskCnpjCpf(e.cnpj_cpf) : '—'}
                      </td>
                      <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                        <div className="inline-flex gap-1.5">
                          <Button variant="ghost" onClick={() => openEditEmpresa(e)} aria-label="Editar empresa">
                            <IconPencil ariaHidden={false} />
                          </Button>
                          <Button variant="ghost" onClick={() => handleDeleteEmpresa(e.id)} aria-label="Excluir empresa">
                            <IconTrash ariaHidden={false} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {aba === 'analises' && !modalEmpresa && !modalFuncionario && Number.isFinite(redeId) ? (
        <Card>
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Análises da rede</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Agregados de tickets e demandas WhatsApp de todas as empresas desta rede.
            </p>
          </div>
          <PainelAnalisesCliente
            redeId={redeId}
            onVerTickets={() => setAba('tickets')}
          />
        </Card>
      ) : null}

      {aba === 'tickets' && !modalEmpresa && !modalFuncionario && (
        <Card>
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Tickets da rede</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Chamados de todas as empresas desta rede. Acompanhe status e responsáveis por empresa.
            </p>
          </div>
          <BarraBuscaPaginacao
            busca={buscaTicketsRede}
            onBuscaChange={setBuscaTicketsRede}
            placeholder="Protocolo, assunto ou empresa..."
            page={pageTicketsRede}
            total={ticketsRedeTotal}
            onPageChange={setPageTicketsRede}
            disabled={loadingTicketsRede}
            extra={
              <Link to="/tickets/novo">
                <Button type="button">Novo ticket</Button>
              </Link>
            }
          />
          <TicketsTabelaContexto
            items={ticketsRedeItems}
            loading={loadingTicketsRede}
            showEmpresaColumn
            emptyMessage="Nenhum ticket desta rede com os filtros atuais."
          />
        </Card>
      )}

      {aba === 'funcionarios' && modalFuncionario && (
        <Card title={modoFuncionario === 'create' ? 'Novo funcionário' : 'Editar funcionário'}>
          <>
              <p className="mb-4 text-sm text-slate-600">
                Rede: <span className="font-medium text-slate-800">{rede.nome}</span> — o vínculo será apenas com empresas desta rede.
              </p>
              <form onSubmit={handleSubmitFuncionario}>
                <div className="space-y-6">
                  <FormSection title="Dados do funcionário">
                    <Input
                      label="Nome *"
                      value={nomeFuncionario}
                      onChange={(e) => setNomeFuncionario(e.target.value)}
                      required
                    />
                    <Input
                      label="E-mail *"
                      type="email"
                      value={emailFuncionario}
                      onChange={(e) => setEmailFuncionario(e.target.value)}
                      required
                    />
                    <Select
                      label="Tipo"
                      value={tipoFuncionario}
                      onChange={(v) => {
                        const t = v as TipoFuncionario
                        setTipoFuncionario(t)
                        setEmpresaIdFuncionario('')
                        setEmpresaIdsFuncionario([])
                      }}
                      options={[
                        { value: 'socio', label: 'Sócio' },
                        { value: 'supervisor', label: 'Supervisor' },
                        { value: 'colaborador', label: 'Colaborador' },
                      ]}
                    />
                  </FormSection>

                  {tipoFuncionario !== 'socio' && (
                    <FormSection title="Vínculo">
                      {tipoFuncionario === 'colaborador' && (
                        <SelectComPesquisa
                          id="rede-detalhe-func-empresa"
                          label="Empresa desta rede *"
                          value={empresaIdFuncionario}
                          onChange={(id) => setEmpresaIdFuncionario(id)}
                          required
                          items={empresasDaRedeParaVinculo.map((x) => ({
                            id: x.id,
                            label: x.nome,
                            createdAt: x.created_at,
                          }))}
                          hint="Últimas empresas desta rede. Digite para buscar."
                        />
                      )}
                      {tipoFuncionario === 'supervisor' && (
                        <div>
                          <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">Empresas desta rede</label>
                          {empresasDaRedeParaVinculo.length === 0 ? (
                            <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma empresa ativa nesta rede.</p>
                          ) : (
                            <div className="flex max-h-44 flex-wrap gap-2 overflow-auto rounded-xl border border-slate-200 bg-slate-50/40 p-3 dark:border-slate-800 dark:bg-slate-800/40">
                              {empresasDaRedeParaVinculo.map((e) => (
                                <CheckboxField
                                  key={e.id}
                                  checked={empresaIdsFuncionario.includes(e.id)}
                                  onChange={() => toggleEmpresaFuncionario(e.id)}
                                >
                                  {e.nome}
                                </CheckboxField>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </FormSection>
                  )}

                  <FormSection title="Portal do cliente">
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Com e-mail e senha, o funcionário acessa{' '}
                      <span className="font-medium text-slate-700 dark:text-slate-200">/portal</span> para abrir e
                      acompanhar chamados.
                      {modoFuncionario === 'edit' && portalHabilitadoFuncionario ? (
                        <span className="ml-1 text-teal-700 dark:text-teal-400">Portal já habilitado.</span>
                      ) : null}
                    </p>
                    <Input
                      label={
                        modoFuncionario === 'edit'
                          ? 'Nova senha do portal (opcional)'
                          : 'Senha do portal (opcional)'
                      }
                      type="password"
                      value={senhaPortalFuncionario}
                      onChange={(e) => setSenhaPortalFuncionario(e.target.value)}
                      autoComplete="new-password"
                      placeholder={emailFuncionario.trim() ? 'Mínimo 8 caracteres' : 'Informe o e-mail primeiro'}
                      disabled={!emailFuncionario.trim()}
                    />
                    <Switch
                      bare
                      checked={mustChangePasswordFuncionario}
                      onCheckedChange={setMustChangePasswordFuncionario}
                      label="Exigir troca de senha no primeiro acesso"
                      showStatusPill
                      statusOnText="Sim"
                      statusOffText="Não"
                    />
                    {modoFuncionario === 'edit' ? (
                      <Switch
                        bare
                        checked={notificarEmailPortalFuncionario}
                        onCheckedChange={setNotificarEmailPortalFuncionario}
                        label="Notificar por e-mail sobre respostas nos chamados"
                        showStatusPill
                        statusOnText="Sim"
                        statusOffText="Não"
                      />
                    ) : null}
                  </FormSection>

                  <FormSection title="Situação no sistema">
                    <Switch
                      bare
                      checked={ativoFuncionario}
                      onCheckedChange={setAtivoFuncionario}
                      label="Funcionário ativo"
                      showStatusPill
                      statusOnText="Ativo"
                      statusOffText="Inativo"
                    />
                  </FormSection>
                </div>

                <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                    <Button type="button" variant="cancel" className="w-full sm:w-auto" onClick={() => fecharModalFuncionario()}>
                      Cancelar
                    </Button>
                    <Button type="submit" loading={savingFuncionario} className="w-full sm:w-auto">
                      Salvar
                    </Button>
                  </div>
                </div>
              </form>
          </>
        </Card>
      )}

      {aba === 'funcionarios' && !modalFuncionario && (
        <Card>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Funcionários da rede</h2>
            <Button onClick={openNovoFuncionario}>Novo funcionário</Button>
          </div>
          <BarraBuscaPaginacao
            busca={buscaFuncionarios}
            onBuscaChange={setBuscaFuncionarios}
            placeholder="Buscar por nome ou e-mail"
            page={pageFuncionarios}
            total={funcionariosTotal}
            onPageChange={setPageFuncionarios}
            disabled={loadingFuncionarios}
            extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
          />
          {loadingFuncionarios && !funcionariosList.length ? (
            <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
          ) : funcionariosList.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400">Nenhum funcionário vinculado a esta rede.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-400">
                    <CabecalhoOrdenavel
                      coluna="nome"
                      rotulo="Nome"
                      ordenarPor={ordemColFunc}
                      ordem={dirFunc}
                      aoOrdenar={aoOrdFunc}
                    />
                    <CabecalhoOrdenavel
                      coluna="email"
                      rotulo="E-mail"
                      ordenarPor={ordemColFunc}
                      ordem={dirFunc}
                      aoOrdenar={aoOrdFunc}
                    />
                    <CabecalhoOrdenavel
                      coluna="tipo"
                      rotulo="Tipo"
                      ordenarPor={ordemColFunc}
                      ordem={dirFunc}
                      aoOrdenar={aoOrdFunc}
                    />
                    <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">Vínculo</th>
                    <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                      <span className="sr-only">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {funcionariosList.map((f) => (
                    <tr
                      key={f.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => verFuncionarioDetalhe(f)}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' || ev.key === ' ') {
                          ev.preventDefault()
                          verFuncionarioDetalhe(f)
                        }
                      }}
                      className="cursor-pointer transition-colors hover:bg-slate-50/80 focus:outline-none focus-visible:bg-slate-100/80 dark:hover:bg-white/50"
                    >
                      <td className="px-4 py-3.5 font-medium text-slate-800 sm:px-6 dark:text-slate-100">{f.nome}</td>
                      <td className="max-w-[12rem] truncate px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300" title={f.email ?? undefined}>
                        {f.email}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300">
                        {tipoLabel[f.tipo] ?? f.tipo}
                      </td>
                      <td className="max-w-[14rem] truncate px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400" title={f.vinculado_a}>
                        {f.vinculado_a}
                      </td>
                      <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                        <div className="inline-flex gap-1.5">
                          <Button variant="ghost" onClick={() => openEditFuncionario(f)} aria-label="Editar funcionário">
                            <IconPencil ariaHidden={false} />
                          </Button>
                          <Button variant="ghost" onClick={() => handleDeleteFuncionario(f.id)} aria-label="Excluir funcionário">
                            <IconTrash ariaHidden={false} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
