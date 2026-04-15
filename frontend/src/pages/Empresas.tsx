import { useState, useEffect, useMemo, useCallback } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { useNavigate, useLocation } from 'react-router-dom'
import { empresas as apiEmpresas, redes, tiposNegocio, type Empresas, type Redes, type TiposNegocio } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
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
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { Select } from '../components/ui/Select'
import { SelectUf } from '../components/ui/SelectUf'
import { SelectCidadeUf } from '../components/ui/SelectCidadeUf'
import { InputCepComBusca } from '../components/ui/InputCepComBusca'
import { maskCnpjCpf, isCnpj } from '../utils/maskCnpjCpf'
import { digitsOnly, maskCep, maskTelefoneBr, maskInscricaoEstadual } from '../utils/masks'
import { ESTADOS_CIVIS_BR, type EstadoCivilBr } from '../constants/estadosCivis'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { Switch } from '../components/ui/Switch'

type ColunaEmpresa = 'nome' | 'cnpj_cpf' | 'rede'

export function Empresas() {
  const navigate = useNavigate()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaEmpresa>()
  const location = useLocation()
  const toast = useToast()
  const [list, setList] = useState<Empresas.Empresa[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [redesList, setRedesList] = useState<Redes.Rede[]>([])
  const [tiposList, setTiposList] = useState<TiposNegocio.Tipo[]>([])
  const [loading, setLoading] = useState(true)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [redeId, setRedeId] = useState<number | ''>('')
  const [tipoNegocioId, setTipoNegocioId] = useState<number | ''>('')
  const [cnpjCpf, setCnpjCpf] = useState('')
  const [razaoSocial, setRazaoSocial] = useState('')
  const [nomeFantasia, setNomeFantasia] = useState('')
  const [inscricaoEstadual, setInscricaoEstadual] = useState('')
  const [endereco, setEndereco] = useState('')
  const [numero, setNumero] = useState('')
  const [complemento, setComplemento] = useState('')
  const [bairro, setBairro] = useState('')
  const [cidade, setCidade] = useState('')
  const [estado, setEstado] = useState('')
  const [cep, setCep] = useState('')
  const [email, setEmail] = useState('')
  const [telefone, setTelefone] = useState('')
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
  const [ativo, setAtivo] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadingCnpj, setLoadingCnpj] = useState(false)

  useEffect(() => {
    if (!modalOpen) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [modalOpen])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos, ordenarPor, ordem])

  const load = useCallback(() => {
    setLoading(true)
    apiEmpresas
      .list<Empresas.Empresa>({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
        ...sortParams,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    coletarTodasPaginas<Redes.Rede>((o, l) => redes.list({ incluir_inativos: true, offset: o, limit: l })).then(
      setRedesList,
    )
    coletarTodasPaginas<TiposNegocio.Tipo>((o, l) =>
      tiposNegocio.list({ incluir_inativos: true, offset: o, limit: l }),
    ).then(setTiposList)
  }, [])

  function openCreate() {
    setEditingId(null)
    const sorted = [...redesList].sort(
      (a, b) => (Date.parse(b.created_at ?? '') || 0) - (Date.parse(a.created_at ?? '') || 0),
    )
    setRedeId(sorted[0]?.id ?? '')
    setTipoNegocioId('')
    setCnpjCpf('')
    setRazaoSocial('')
    setNomeFantasia('')
    setInscricaoEstadual('')
    setEndereco('')
    setNumero('')
    setComplemento('')
    setBairro('')
    setCidade('')
    setEstado('')
    setCep('')
    setEmail('')
    setTelefone('')
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
    setAtivo(true)
    setModalOpen(true)
  }

  function openEdit(e: Empresas.Empresa) {
    setEditingId(e.id)
    setRedeId(e.rede_id)
    setTipoNegocioId(e.tipo_negocio_id ?? '')
    setCnpjCpf(e.cnpj_cpf ? maskCnpjCpf(e.cnpj_cpf) : '')
    setRazaoSocial(e.razao_social ?? '')
    setNomeFantasia(e.nome_fantasia ?? '')
    setInscricaoEstadual(e.inscricao_estadual ?? '')
    setEndereco(e.endereco ?? '')
    setNumero(e.numero ?? '')
    setComplemento(e.complemento ?? '')
    setBairro(e.bairro ?? '')
    setCidade(e.cidade ?? '')
    setEstado((e.estado ?? '').toUpperCase().slice(0, 2))
    setCep(e.cep ? maskCep(e.cep.replace(/\D/g, '')) : '')
    setEmail(e.email ?? '')
    setTelefone(e.telefone ? maskTelefoneBr(e.telefone) : '')
    setRespLegalNome(e.resp_legal_nome ?? '')
    setRespLegalCpf(e.resp_legal_cpf ? maskCnpjCpf(e.resp_legal_cpf) : '')
    setRespLegalRg(e.resp_legal_rg ?? '')
    setRespLegalOrgaoEmissor(e.resp_legal_orgao_emissor ?? '')
    setRespLegalNacionalidade(e.resp_legal_nacionalidade ?? '')
    setRespLegalEstadoCivil(e.resp_legal_estado_civil ?? '')
    setRespLegalCargo(e.resp_legal_cargo ?? '')
    setRespLegalEmail(e.resp_legal_email ?? '')
    setRespLegalTelefone(e.resp_legal_telefone ? maskTelefoneBr(e.resp_legal_telefone) : '')
    setRespLegalEndereco(e.resp_legal_endereco ?? '')
    setRespLegalNumero(e.resp_legal_numero ?? '')
    setRespLegalComplemento(e.resp_legal_complemento ?? '')
    setRespLegalBairro(e.resp_legal_bairro ?? '')
    setRespLegalCidade(e.resp_legal_cidade ?? '')
    setRespLegalEstado((e.resp_legal_estado ?? '').toUpperCase().slice(0, 2))
    setRespLegalCep(e.resp_legal_cep ? maskCep(e.resp_legal_cep.replace(/\D/g, '')) : '')
    setAtivo(e.ativo)
    setModalOpen(true)
  }

  useEffect(() => {
    const editId = (location.state as { empresaEditId?: number } | null)?.empresaEditId
    if (editId == null) return
    navigate('/empresas', { replace: true, state: {} })
    apiEmpresas
      .get(editId)
      .then((emp) => openEdit(emp))
      .catch(() => toast.showWarning('Empresa não encontrada.'))
  // eslint-disable-next-line react-hooks/exhaustive-deps -- abre edição ao retornar da tela de detalhe com state
  }, [location.state])

  function handleCnpjCpfChange(value: string) {
    setCnpjCpf(maskCnpjCpf(value))
  }

  async function handleConsultarCnpj() {
    const d = digitsOnly(cnpjCpf)
    if (!isCnpj(cnpjCpf)) {
      toast.showWarning('Informe um CNPJ com 14 dígitos para consultar. CPF não possui consulta automática.')
      return
    }
    setLoadingCnpj(true)
    try {
      const data = await apiEmpresas.consultarCnpj(d)
      setRazaoSocial(data.razao_social ?? '')
      setNomeFantasia(data.nome_fantasia ?? '')
      setEndereco(data.endereco ?? '')
      setNumero(data.numero ?? '')
      setComplemento(data.complemento ?? '')
      setBairro(data.bairro ?? '')
      setCidade(data.cidade ?? '')
      setEstado(data.estado ?? '')
      setCep(data.cep ? maskCep(data.cep.replace(/\D/g, '')) : '')
      setEmail(data.email ?? '')
      setTelefone(data.telefone ? maskTelefoneBr(data.telefone) : '')
      toast.showSuccess('Dados preenchidos com sucesso.')
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro ao consultar CNPJ')
    } finally {
      setLoadingCnpj(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!redeId) {
      toast.showWarning('Selecione a rede.')
      return
    }
    const nomeGravado = nomeParaApiEmpresa(nomeFantasia, razaoSocial)
    if (!nomeGravado) {
      toast.showWarning('Informe o nome fantasia ou a razão social.')
      return
    }
    setSaving(true)
    try {
      const payload = {
        rede_id: Number(redeId),
        tipo_negocio_id: tipoNegocioId === '' ? null : Number(tipoNegocioId),
        nome: nomeGravado,
        cnpj_cpf: cnpjCpf.replace(/\D/g, '') || null,
        razao_social: razaoSocial.trim() || null,
        nome_fantasia: nomeFantasia.trim() || null,
        inscricao_estadual: inscricaoEstadual.trim() || null,
        endereco: endereco.trim() || null,
        numero: numero.trim() || null,
        complemento: complemento.trim() || null,
        bairro: bairro.trim() || null,
        cidade: cidade.trim() || null,
        estado: estado.trim() || null,
        cep: cep.replace(/\D/g, '') || null,
        email: email.trim() || null,
        telefone: digitsOnly(telefone) || null,
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
        ativo,
      }
      if (editingId) {
        await apiEmpresas.update(editingId, payload)
        toast.showSuccess('Empresa atualizada.')
        setModalOpen(false)
        load()
        navigate(`/empresas/${editingId}`, { replace: true })
      } else {
        const criada = await apiEmpresas.create(payload)
        toast.showSuccess('Empresa cadastrada.')
        setModalOpen(false)
        load()
        navigate(`/empresas/${criada.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro')
    } finally {
      setSaving(false)
    }
  }

  const opcoesEstadoCivil = useMemo(() => {
    const base = ESTADOS_CIVIS_BR.map((c) => ({ value: c, label: c }))
    const cur = respLegalEstadoCivil.trim()
    if (cur && !ESTADOS_CIVIS_BR.includes(cur as EstadoCivilBr)) {
      return [{ value: cur, label: `${cur} (cadastro atual)` }, ...base]
    }
    return base
  }, [respLegalEstadoCivil])

  async function handleDelete(id: number) {
    if (!confirm('Excluir esta empresa?')) return
    try {
      await apiEmpresas.delete(id)
      load()
    } catch (err) {
      toast.showWarning(err instanceof Error ? err.message : 'Erro ao excluir')
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      {!modalOpen && (
        <div className="flex justify-between">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Empresas</h1>
          <Button onClick={openCreate} disabled={modalOpen}>Nova empresa</Button>
        </div>
      )}

      {modalOpen && (
        <div className="fixed inset-y-0 left-0 right-0 z-20 flex items-start justify-center bg-black/85 px-4 pb-6 pt-16 sm:px-6 md:left-[var(--sidebar-w)]">
          <Card
            title={editingId ? 'Editar empresa' : 'Nova empresa'}
            className="max-h-[min(92vh,56rem)] w-full max-w-6xl overflow-y-auto rounded-2xl bg-white dark:bg-slate-900"
          >
            <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
              <div className="space-y-5 pb-24 sm:space-y-6">
                <FormSection title="Classificação">
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-5">
                    <SelectComPesquisa
                      id="empresa-rede"
                      label="Rede"
                      value={redeId}
                      onChange={(id) => setRedeId(id)}
                      required
                      items={redesList.map((r) => ({
                        id: r.id,
                        label: r.nome,
                        createdAt: r.created_at,
                      }))}
                    />
                    <Select
                      label="Tipo de negócio"
                      value={tipoNegocioId}
                      onChange={(v) => setTipoNegocioId(v === '' ? '' : Number(v))}
                      options={tiposList.map((t) => ({ value: t.id, label: t.nome }))}
                      includeEmpty
                      emptyLabel="Selecione"
                      placeholder="Selecione"
                    />
                  </div>
                </FormSection>

              <FormSection title="Documento e nomes" description={EMPRESA_SECAO_DOCUMENTO_NOMES}>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:items-end lg:gap-5">
                  <Input
                    id="empresa-cnpj"
                    label="CNPJ / CPF"
                    inputMode="numeric"
                    placeholder="00.000.000/0001-00 ou CPF"
                    value={cnpjCpf}
                    onChange={(e) => handleCnpjCpfChange(e.target.value)}
                    endAdornment={
                      <button
                        type="button"
                        onClick={handleConsultarCnpj}
                        disabled={loadingCnpj}
                        className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 disabled:pointer-events-none disabled:opacity-45 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                        aria-label="Consultar CNPJ na Receita"
                      >
                        {loadingCnpj ? (
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
                    value={inscricaoEstadual}
                    onChange={(e) => setInscricaoEstadual(maskInscricaoEstadual(e.target.value))}
                  />
                </div>
                <Input label="Razão social" value={razaoSocial} onChange={(e) => setRazaoSocial(e.target.value)} />
                <Input label="Nome fantasia" value={nomeFantasia} onChange={(e) => setNomeFantasia(e.target.value)} />
              </FormSection>

              <FormSection title="Endereço">
                <Input label="Logradouro" value={endereco} onChange={(e) => setEndereco(e.target.value)} />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <Input label="Número" value={numero} onChange={(e) => setNumero(e.target.value)} />
                  <Input label="Complemento" value={complemento} onChange={(e) => setComplemento(e.target.value)} />
                  <Input label="Bairro" value={bairro} onChange={(e) => setBairro(e.target.value)} />
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <div className="xl:col-span-1">
                    <SelectUf
                      id="empresa-uf"
                      value={estado}
                      onChange={(uf) => {
                        setEstado(uf)
                        setCidade('')
                      }}
                    />
                  </div>
                  <div className="sm:col-span-2 xl:col-span-1">
                    <SelectCidadeUf id="empresa-cidade" uf={estado} value={cidade} onChange={setCidade} />
                  </div>
                  <InputCepComBusca
                    id="empresa-cep"
                    value={cep}
                    onChange={setCep}
                    onEnderecoCompleto={(d) => {
                      setEndereco(d.logradouro)
                      setBairro(d.bairro)
                      setCidade(d.localidade)
                      setEstado(d.uf)
                      if (d.complemento) setComplemento(d.complemento)
                    }}
                  />
                </div>
              </FormSection>

              <FormSection title="Contato">
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-5">
                  <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                  <Input
                    label="Telefone"
                    inputMode="tel"
                    placeholder="(00) 00000-0000"
                    value={telefone}
                    onChange={(e) => setTelefone(maskTelefoneBr(e.target.value))}
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
                    id="empresa-resp-estado-civil"
                    label="Estado civil"
                    value={respLegalEstadoCivil}
                    onChange={(v) => setRespLegalEstadoCivil(v === '' ? '' : String(v))}
                    options={opcoesEstadoCivil}
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
                    placeholder="(00) 00000-0000"
                    value={respLegalTelefone}
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
                  <div className="xl:col-span-1">
                    <SelectUf
                      id="empresa-resp-uf"
                      value={respLegalEstado}
                      onChange={(uf) => {
                        setRespLegalEstado(uf)
                        setRespLegalCidade('')
                      }}
                    />
                  </div>
                  <div className="sm:col-span-2 xl:col-span-1">
                    <SelectCidadeUf
                      id="empresa-resp-cidade"
                      uf={respLegalEstado}
                      value={respLegalCidade}
                      onChange={setRespLegalCidade}
                    />
                  </div>
                  <InputCepComBusca
                    id="empresa-resp-cep"
                    value={respLegalCep}
                    onChange={setRespLegalCep}
                    onEnderecoCompleto={(d) => {
                      setRespLegalEndereco(d.logradouro)
                      setRespLegalBairro(d.bairro)
                      setRespLegalCidade(d.localidade)
                      setRespLegalEstado(d.uf)
                      if (d.complemento) setRespLegalComplemento(d.complemento)
                    }}
                  />
                </div>
              </FormSection>

              <FormSection title="Situação no sistema">
                <Switch
                  bare
                  showStatusPill
                  checked={ativo}
                  onCheckedChange={setAtivo}
                  label="Empresa ativa"
                  description={EMPRESA_HINT_ATIVA}
                />
              </FormSection>
              </div>

              <div className="sticky bottom-0 -mx-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
                <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <Button
                    type="button"
                    variant="secondary"
                    className="w-full sm:w-auto"
                    onClick={() => setModalOpen(false)}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" loading={saving} className="w-full sm:w-auto">
                    Salvar
                  </Button>
                </div>
              </div>
            </form>
          </Card>
        </div>
      )}

      {!modalOpen && (
        <Card>
          <BarraBuscaPaginacao
            busca={busca}
            onBuscaChange={setBusca}
            placeholder="Buscar por nome, razão social, CNPJ ou e-mail"
            page={page}
            total={total}
            onPageChange={setPage}
            disabled={loading}
            extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
          />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhuma empresa encontrada.</p>
        ) : (
          <div className="-mx-2 overflow-x-auto rounded-lg">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <CabecalhoOrdenavel
                    coluna="nome"
                    rotulo="Empresa"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="py-2.5 pl-2 pr-4"
                  />
                  <CabecalhoOrdenavel
                    coluna="cnpj_cpf"
                    rotulo="CNPJ / CPF"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="py-2.5 pr-4"
                  />
                  <CabecalhoOrdenavel
                    coluna="rede"
                    rotulo="Rede"
                    ordenarPor={ordenarPor}
                    ordem={ordem}
                    aoOrdenar={aoOrdenarColuna}
                    className="min-w-[8rem] py-2.5 pr-4"
                  />
                  <th className="w-px py-2.5 pr-2 text-right" aria-hidden />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((e) => {
                  const redeNome = redesList.find((r) => r.id === e.rede_id)?.nome ?? '—'
                  const doc = e.cnpj_cpf ? maskCnpjCpf(e.cnpj_cpf) : '—'
                  return (
                    <tr
                      key={e.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => navigate(`/empresas/${e.id}`)}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' || ev.key === ' ') {
                          ev.preventDefault()
                          navigate(`/empresas/${e.id}`)
                        }
                      }}
                      className="cursor-pointer transition-colors hover:bg-slate-50/90 focus-within:bg-slate-50/90 dark:hover:bg-slate-800/50 dark:focus-within:bg-slate-800/50"
                    >
                      <td className="max-w-0 py-3 pl-2 pr-4">
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                          <span className={`truncate font-medium ${e.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>
                            {e.nome}
                          </span>
                          {!e.ativo && (
                            <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                              Inativo
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="whitespace-nowrap py-3 pr-4 font-mono text-xs text-slate-600 tabular-nums dark:text-slate-400">
                        {doc}
                      </td>
                      <td className="max-w-[14rem] truncate py-3 pr-4 text-slate-600 dark:text-slate-400" title={redeNome}>
                        {redeNome}
                      </td>
                      <td className="py-3 pr-2 text-right" onClick={(ev) => ev.stopPropagation()}>
                        <div className="inline-flex gap-0.5">
                          <Button
                            variant="ghost"
                            onClick={(ev) => {
                              ev.stopPropagation()
                              openEdit(e)
                            }}
                            aria-label="Editar empresa"
                          >
                            <IconPencil ariaHidden={false} />
                          </Button>
                          <Button variant="ghost" onClick={() => handleDelete(e.id)} aria-label="Excluir empresa">
                            <IconTrash ariaHidden={false} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        </Card>
      )}
    </div>
  )
}
