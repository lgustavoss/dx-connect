import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ApiError,
  empresas as apiEmpresas,
  redes,
  tiposNegocio,
  type Empresas,
  type Redes,
  type TiposNegocio,
} from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { FormSection } from '../components/ui/FormSection'
import {
  EMPRESA_HINT_ATIVA,
  EMPRESA_HINT_EMITE_NFSE,
  EMPRESA_SECAO_DOCUMENTO_NOMES,
  EMPRESA_SECAO_RESPONSAVEL_LEGAL,
  nomeParaApiEmpresa,
} from '../components/empresa/empresaFormCopy'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { Select } from '../components/ui/Select'
import { SelectUf } from '../components/ui/SelectUf'
import { SelectCidadeUf } from '../components/ui/SelectCidadeUf'
import { InputCepComBusca } from '../components/ui/InputCepComBusca'
import { maskCnpjCpf, isCnpj } from '../utils/maskCnpjCpf'
import { digitsOnly, maskCep, maskTelefoneBr, maskInscricaoEstadual } from '../utils/masks'
import { ESTADOS_CIVIS_BR, type EstadoCivilBr } from '../constants/estadosCivis'
import { Switch } from '../components/ui/Switch'
import { InlineCadastroFooter } from '../components/ui/InlineCadastroPanel'
import { CadastroFormPageShell } from '../components/ui/CadastroFormPageShell'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'

function aplicarEmpresaNoFormulario(e: Empresas.Empresa, setters: {
  setRedeId: (v: number | '') => void
  setTipoNegocioId: (v: number | '') => void
  setCnpjCpf: (v: string) => void
  setRazaoSocial: (v: string) => void
  setNomeFantasia: (v: string) => void
  setInscricaoEstadual: (v: string) => void
  setEndereco: (v: string) => void
  setNumero: (v: string) => void
  setComplemento: (v: string) => void
  setBairro: (v: string) => void
  setCidade: (v: string) => void
  setEstado: (v: string) => void
  setCep: (v: string) => void
  setEmail: (v: string) => void
  setTelefone: (v: string) => void
  setRespLegalNome: (v: string) => void
  setRespLegalCpf: (v: string) => void
  setRespLegalRg: (v: string) => void
  setRespLegalOrgaoEmissor: (v: string) => void
  setRespLegalNacionalidade: (v: string) => void
  setRespLegalEstadoCivil: (v: string) => void
  setRespLegalCargo: (v: string) => void
  setRespLegalEmail: (v: string) => void
  setRespLegalTelefone: (v: string) => void
  setRespLegalEndereco: (v: string) => void
  setRespLegalNumero: (v: string) => void
  setRespLegalComplemento: (v: string) => void
  setRespLegalBairro: (v: string) => void
  setRespLegalCidade: (v: string) => void
  setRespLegalEstado: (v: string) => void
  setRespLegalCep: (v: string) => void
  setAtivo: (v: boolean) => void
  setEmiteNfse: (v: boolean) => void
}) {
  setters.setRedeId(e.rede_id)
  setters.setTipoNegocioId(e.tipo_negocio_id ?? '')
  setters.setCnpjCpf(e.cnpj_cpf ? maskCnpjCpf(e.cnpj_cpf) : '')
  setters.setRazaoSocial(e.razao_social ?? '')
  setters.setNomeFantasia(e.nome_fantasia ?? '')
  setters.setInscricaoEstadual(e.inscricao_estadual ?? '')
  setters.setEndereco(e.endereco ?? '')
  setters.setNumero(e.numero ?? '')
  setters.setComplemento(e.complemento ?? '')
  setters.setBairro(e.bairro ?? '')
  setters.setCidade(e.cidade ?? '')
  setters.setEstado((e.estado ?? '').toUpperCase().slice(0, 2))
  setters.setCep(e.cep ? maskCep(e.cep.replace(/\D/g, '')) : '')
  setters.setEmail(e.email ?? '')
  setters.setTelefone(e.telefone ? maskTelefoneBr(e.telefone) : '')
  setters.setRespLegalNome(e.resp_legal_nome ?? '')
  setters.setRespLegalCpf(e.resp_legal_cpf ? maskCnpjCpf(e.resp_legal_cpf) : '')
  setters.setRespLegalRg(e.resp_legal_rg ?? '')
  setters.setRespLegalOrgaoEmissor(e.resp_legal_orgao_emissor ?? '')
  setters.setRespLegalNacionalidade(e.resp_legal_nacionalidade ?? '')
  setters.setRespLegalEstadoCivil(e.resp_legal_estado_civil ?? '')
  setters.setRespLegalCargo(e.resp_legal_cargo ?? '')
  setters.setRespLegalEmail(e.resp_legal_email ?? '')
  setters.setRespLegalTelefone(e.resp_legal_telefone ? maskTelefoneBr(e.resp_legal_telefone) : '')
  setters.setRespLegalEndereco(e.resp_legal_endereco ?? '')
  setters.setRespLegalNumero(e.resp_legal_numero ?? '')
  setters.setRespLegalComplemento(e.resp_legal_complemento ?? '')
  setters.setRespLegalBairro(e.resp_legal_bairro ?? '')
  setters.setRespLegalCidade(e.resp_legal_cidade ?? '')
  setters.setRespLegalEstado((e.resp_legal_estado ?? '').toUpperCase().slice(0, 2))
  setters.setRespLegalCep(e.resp_legal_cep ? maskCep(e.resp_legal_cep.replace(/\D/g, '')) : '')
  setters.setAtivo(e.ativo)
  setters.setEmiteNfse(e.emite_nfse !== false)
}

export function EmpresaForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/empresas')

  const empresaId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [metaLoading, setMetaLoading] = useState(true)
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
  const [emiteNfse, setEmiteNfse] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadingCnpj, setLoadingCnpj] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [redesList, setRedesList] = useState<Redes.Rede[]>([])
  const [tiposList, setTiposList] = useState<TiposNegocio.Tipo[]>([])

  useEffect(() => {
    let cancelled = false
    setMetaLoading(true)
    Promise.all([
      coletarTodasPaginas<Redes.Rede>((o, l) => redes.list({ incluir_inativos: true, offset: o, limit: l })),
      coletarTodasPaginas<TiposNegocio.Tipo>((o, l) =>
        tiposNegocio.list({ incluir_inativos: true, offset: o, limit: l }),
      ),
    ])
      .then(([redesAll, tiposAll]) => {
        if (cancelled) return
        setRedesList(redesAll)
        setTiposList(tiposAll)
        if (!isEdit && redeId === '') {
          const sorted = [...redesAll].sort(
            (a, b) => (Date.parse(b.created_at ?? '') || 0) - (Date.parse(a.created_at ?? '') || 0),
          )
          setRedeId(sorted[0]?.id ?? '')
        }
      })
      .finally(() => {
        if (!cancelled) setMetaLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isEdit, redeId])

  useEffect(() => {
    if (!isEdit) {
      setLoading(false)
      return
    }
    if (!id || Number.isNaN(empresaId)) {
      setInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setInexistente(null)
    apiEmpresas
      .get(empresaId)
      .then((emp) => {
        if (cancelled) return
        aplicarEmpresaNoFormulario(emp, {
          setRedeId,
          setTipoNegocioId,
          setCnpjCpf,
          setRazaoSocial,
          setNomeFantasia,
          setInscricaoEstadual,
          setEndereco,
          setNumero,
          setComplemento,
          setBairro,
          setCidade,
          setEstado,
          setCep,
          setEmail,
          setTelefone,
          setRespLegalNome,
          setRespLegalCpf,
          setRespLegalRg,
          setRespLegalOrgaoEmissor,
          setRespLegalNacionalidade,
          setRespLegalEstadoCivil,
          setRespLegalCargo,
          setRespLegalEmail,
          setRespLegalTelefone,
          setRespLegalEndereco,
          setRespLegalNumero,
          setRespLegalComplemento,
          setRespLegalBairro,
          setRespLegalCidade,
          setRespLegalEstado,
          setRespLegalCep,
          setAtivo,
          setEmiteNfse,
        })
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setInexistente({})
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Empresa não encontrada.')
        toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, empresaId, toast])

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
      toast.showError(mensagemFalhaParaToast(err, 'Erro ao consultar CNPJ.'))
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
        emite_nfse: emiteNfse,
      }
      if (isEdit && !Number.isNaN(empresaId)) {
        await apiEmpresas.update(empresaId, payload)
        toast.showSuccess('Empresa atualizada.')
        navigate(`/empresas/${empresaId}`, { replace: true })
      } else {
        const criada = await apiEmpresas.create(payload)
        toast.showSuccess('Empresa cadastrada.')
        navigate(`/empresas/${criada.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a empresa.'))
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

  if (loading || metaLoading) {
    return (
      <CadastroFormPageShell onVoltar={voltarAnterior} wide>
        <div className="h-96 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para editar empresas."
        voltarPara="/empresas"
        voltarLabel="Voltar para Empresas"
      />
    )
  }

  if (inexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto w-full min-w-0 max-w-6xl space-y-4 pb-10"
        titulo="Empresa não encontrada."
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior} wide>
      <Card title={isEdit ? 'Editar empresa' : 'Nova empresa'}>
        <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
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
                <Switch
                  bare
                  showStatusPill
                  checked={emiteNfse}
                  onCheckedChange={setEmiteNfse}
                  label="Emite NFS-e"
                  description={EMPRESA_HINT_EMITE_NFSE}
                />
              </FormSection>

          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
