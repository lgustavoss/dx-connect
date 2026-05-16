import { useCallback, useEffect, useRef, useState } from 'react'
import {
  empresas,
  fetchEmpresaSistemaLogoBlob,
  systemSettings,
  tenantApi,
  type CadastroAux,
  type SystemSettings,
  type TenantApi,
} from '../api/client'
import { resolveTenantIdFromHostname, tenantAppOrigin } from '../lib/tenant'
import { nomeParaApiEmpresa } from '../components/empresa/empresaFormCopy'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { InputCepComBusca } from '../components/ui/InputCepComBusca'
import { SelectCidadeUf } from '../components/ui/SelectCidadeUf'
import { SelectUf } from '../components/ui/SelectUf'
import { useToast } from '../components/ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { isCnpj, maskCnpjCpf } from '../utils/maskCnpjCpf'
import { digitsOnly, formatTelefoneBrExibicao, maskCep, maskTelefoneBr } from '../utils/masks'

type Aba = 'empresa' | 'email'

const fieldClass =
  'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-[0.9375rem] text-slate-900 shadow-inner placeholder:text-slate-400 focus:border-cyan-500/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/25 dark:border-white/10 dark:bg-white/[0.06] dark:text-slate-100 dark:placeholder:text-slate-500'

export function ConfigEmpresaEmail() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [aba, setAba] = useState<Aba>('empresa')

  const [cnpj, setCnpj] = useState('')
  const [cnpjImutavel, setCnpjImutavel] = useState(false)
  const [razaoSocial, setRazaoSocial] = useState('')
  const [nomeFantasia, setNomeFantasia] = useState('')
  const [emailEmpresa, setEmailEmpresa] = useState('')
  const [telefone, setTelefone] = useState('')
  const [endereco, setEndereco] = useState('')
  const [numero, setNumero] = useState('')
  const [complemento, setComplemento] = useState('')
  const [bairro, setBairro] = useState('')
  const [cidade, setCidade] = useState('')
  const [estado, setEstado] = useState('')
  const [cep, setCep] = useState('')
  const [salvandoEmpresa, setSalvandoEmpresa] = useState(false)
  const [loadingCnpjConsulta, setLoadingCnpjConsulta] = useState(false)
  const [logoBlobUrl, setLogoBlobUrl] = useState<string | null>(null)
  const logoBlobUrlRef = useRef<string | null>(null)
  const [logoLoading, setLogoLoading] = useState(false)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [logoDeleting, setLogoDeleting] = useState(false)

  const [emailOutbound, setEmailOutbound] = useState<SystemSettings.EmailSettingsRead | null>(null)
  const [testandoTransactional, setTestandoTransactional] = useState(false)

  const tenantId = resolveTenantIdFromHostname()
  const [tenantInfo, setTenantInfo] = useState<TenantApi.TenantRead | null>(null)
  const [inboundAddresses, setInboundAddresses] = useState<TenantApi.InboundAddressRead[]>([])
  const [carregandoInbound, setCarregandoInbound] = useState(false)

  useEffect(() => {
    logoBlobUrlRef.current = logoBlobUrl
  }, [logoBlobUrl])

  const carregar = useCallback(async () => {
    setLoading(true)
    try {
      const [emp, mail, tenantAtual, inbound] = await Promise.all([
        systemSettings.getEmpresaSistema(),
        systemSettings.getEmail(),
        tenantApi.getAtual().catch(() => null),
        tenantApi.listInboundAddresses().catch(() => [] as TenantApi.InboundAddressRead[]),
      ])
      setTenantInfo(tenantAtual)
      setInboundAddresses(inbound)

      const cj = (emp.cnpj ?? '').trim()
      setCnpj(cj ? maskCnpjCpf(cj) : '')
      setCnpjImutavel(Boolean(cj))
      setRazaoSocial((emp.razao_social ?? '').trim())
      setNomeFantasia((emp.nome_fantasia ?? '').trim())
      setEmailEmpresa((emp.email ?? '').trim())
      setTelefone(formatTelefoneBrExibicao(emp.telefone))
      setEndereco((emp.endereco ?? '').trim())
      setNumero((emp.numero ?? '').trim())
      setComplemento((emp.complemento ?? '').trim())
      setBairro((emp.bairro ?? '').trim())
      setCidade((emp.cidade ?? '').trim())
      setEstado((emp.estado ?? '').trim().toUpperCase().slice(0, 2))
      setCep(emp.cep ? maskCep(digitsOnly(emp.cep)) : '')

      // logo: precisa de fetch autenticado (não dá pra usar <img src> direto).
      const prevBlob = logoBlobUrlRef.current
      if (prevBlob) URL.revokeObjectURL(prevBlob)
      logoBlobUrlRef.current = null
      setLogoBlobUrl(null)
      if (emp.logo_url) {
        setLogoLoading(true)
        try {
          const b = await fetchEmpresaSistemaLogoBlob()
          if (b) setLogoBlobUrl(URL.createObjectURL(b))
        } finally {
          setLogoLoading(false)
        }
      }

      setEmailOutbound(mail)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as configurações.'))
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    if (logoPreviewUrl) return () => URL.revokeObjectURL(logoPreviewUrl)
  }, [logoPreviewUrl])

  useEffect(() => {
    return () => {
      if (logoBlobUrl) URL.revokeObjectURL(logoBlobUrl)
      if (logoPreviewUrl) URL.revokeObjectURL(logoPreviewUrl)
    }
  }, [logoBlobUrl, logoPreviewUrl])

  async function consultarCnpjReceita() {
    if (!isCnpj(cnpj)) {
      toast.showWarning('Informe um CNPJ com 14 dígitos para consultar.')
      return
    }
    setLoadingCnpjConsulta(true)
    try {
      const data = await empresas.consultarCnpj(digitsOnly(cnpj))
      setRazaoSocial((data.razao_social ?? '').trim())
      setNomeFantasia((data.nome_fantasia ?? '').trim())
      setEmailEmpresa((data.email ?? '').trim())
      setTelefone(data.telefone ? maskTelefoneBr(data.telefone) : '')
      setEndereco((data.endereco ?? '').trim())
      setNumero((data.numero ?? '').trim())
      setComplemento((data.complemento ?? '').trim())
      setBairro((data.bairro ?? '').trim())
      setCidade((data.cidade ?? '').trim())
      setEstado((data.estado ?? '').trim().toUpperCase().slice(0, 2))
      setCep(data.cep ? maskCep(digitsOnly(data.cep)) : '')
      setCnpj(maskCnpjCpf(digitsOnly(cnpj)))
      toast.showSuccess('Dados preenchidos a partir da Receita Federal.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Erro ao consultar CNPJ.'))
    } finally {
      setLoadingCnpjConsulta(false)
    }
  }

  async function salvarEmpresa(e: React.FormEvent) {
    e.preventDefault()
    const cnpjTrim = cnpj.trim()
    if (!cnpjImutavel && !cnpjTrim) {
      toast.showError('Informe o CNPJ da empresa do sistema.')
      return
    }
    const nomeGravado = nomeParaApiEmpresa(nomeFantasia, razaoSocial)
    if (!nomeGravado) {
      toast.showWarning('Informe o nome fantasia ou a razão social.')
      return
    }
    setSalvandoEmpresa(true)
    try {
      const payload: SystemSettings.EmpresaSistemaUpdate = {
        nome: nomeGravado,
        razao_social: razaoSocial.trim() || null,
        nome_fantasia: nomeFantasia.trim() || null,
        email: emailEmpresa.trim() || null,
        telefone: digitsOnly(telefone) || null,
        endereco: endereco.trim() || null,
        numero: numero.trim() || null,
        complemento: complemento.trim() || null,
        bairro: bairro.trim() || null,
        cidade: cidade.trim() || null,
        estado: estado.trim() || null,
        cep: digitsOnly(cep) || null,
      }
      if (!cnpjImutavel) {
        payload.cnpj = cnpjTrim
      }
      const out = await systemSettings.putEmpresaSistema(payload)
      setCnpjImutavel(Boolean((out.cnpj ?? '').trim()))
      toast.showSuccess('Dados da empresa salvos.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a empresa.'))
    } finally {
      setSalvandoEmpresa(false)
    }
  }

  async function uploadLogo() {
    if (!logoFile) {
      toast.showError('Selecione um arquivo de imagem para enviar.')
      return
    }
    if (!/^image\//.test(logoFile.type)) {
      toast.showError('Envie um arquivo de imagem (PNG/JPG/WEBP).')
      return
    }
    setLogoUploading(true)
    try {
      await systemSettings.uploadEmpresaLogo(logoFile)
      toast.showSuccess('Logo salvo.')
      setLogoFile(null)
      if (logoPreviewUrl) {
        URL.revokeObjectURL(logoPreviewUrl)
        setLogoPreviewUrl(null)
      }
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar o logo.'))
    } finally {
      setLogoUploading(false)
    }
  }

  async function removerLogo() {
    if (!confirm('Remover o logo atual?')) return
    setLogoDeleting(true)
    try {
      await systemSettings.deleteEmpresaLogo()
      toast.showSuccess('Logo removido.')
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível remover o logo.'))
    } finally {
      setLogoDeleting(false)
    }
  }

  const recarregarInbound = useCallback(async () => {
    setCarregandoInbound(true)
    try {
      const inbound = await tenantApi.listInboundAddresses()
      setInboundAddresses(inbound)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar os endereços por setor.'))
    } finally {
      setCarregandoInbound(false)
    }
  }, [toast])

  useEffect(() => {
    if (aba !== 'email' || loading) return
    void recarregarInbound()
  }, [aba, loading, recarregarInbound])

  async function copiarEndereco(email: string) {
    try {
      await navigator.clipboard.writeText(email)
      toast.showSuccess('Endereço copiado.')
    } catch {
      toast.showError('Não foi possível copiar. Selecione o texto manualmente.')
    }
  }

  async function testarTransactional() {
    setTestandoTransactional(true)
    try {
      const r = await systemSettings.testEmailTransactional()
      if (r.ok) {
        toast.showSuccess(r.detail?.trim() || 'E-mail de teste enviado.')
      } else {
        toast.showError(r.detail?.trim() || 'Falha no teste de envio.')
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar o teste.'))
    } finally {
      setTestandoTransactional(false)
    }
  }
  if (loading) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <Card title="Empresa do sistema e e-mail">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Dados institucionais da instalação e endereços de encaminhamento por setor para tickets por e-mail (apenas
          administradores).
        </p>

        <div className="mt-5 border-b border-slate-200 dark:border-slate-700/80">
          <nav className="flex gap-1 sm:gap-2" aria-label="Seções">
            <button
              type="button"
              onClick={() => setAba('empresa')}
              aria-current={aba === 'empresa' ? 'page' : undefined}
              className={
                aba === 'empresa'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800/30 dark:hover:text-slate-200'
              }
            >
              Empresa
            </button>
            <button
              type="button"
              onClick={() => setAba('email')}
              aria-current={aba === 'email' ? 'page' : undefined}
              className={
                aba === 'email'
                  ? 'border-b-2 border-sky-500 px-3 py-2 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:bg-slate-800/50 dark:text-white'
                  : 'border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800/30 dark:hover:text-slate-200'
              }
            >
              E-mail
            </button>
          </nav>
        </div>

        {aba === 'empresa' ? (
          <form onSubmit={salvarEmpresa} className="mt-6 space-y-4">
            <div className="rounded-lg border border-amber-200/80 bg-amber-50/90 px-3 py-2 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100">
              O CNPJ é obrigatório no primeiro cadastro. Depois de salvo, <strong>não pode ser alterado</strong>.
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Logo</label>
                <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-inner dark:border-white/10 dark:bg-white/[0.04]">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="h-14 w-14 overflow-hidden rounded-lg border border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-slate-900">
                      {logoLoading ? (
                        <div className="flex h-full w-full items-center justify-center text-xs text-slate-500 dark:text-slate-400">
                          Carregando…
                        </div>
                      ) : logoPreviewUrl ? (
                        <img src={logoPreviewUrl} alt="Prévia do logo" className="h-full w-full object-contain" />
                      ) : logoBlobUrl ? (
                        <img src={logoBlobUrl} alt="Logo atual" className="h-full w-full object-contain" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-xs text-slate-500 dark:text-slate-400">
                          —
                        </div>
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-slate-700 dark:text-slate-300">
                        Envie uma imagem (PNG/JPG/WEBP). O sistema usa esse logo nas telas e relatórios.
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Tamanho recomendado: até 2MB.</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={(e) => {
                        const f = e.target.files?.[0] ?? null
                        setLogoFile(f)
                        if (logoPreviewUrl) URL.revokeObjectURL(logoPreviewUrl)
                        setLogoPreviewUrl(f ? URL.createObjectURL(f) : null)
                      }}
                      className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-800 hover:file:bg-slate-200 dark:text-slate-300 dark:file:bg-slate-800 dark:file:text-slate-100 dark:hover:file:bg-slate-700 sm:w-auto"
                    />
                    <Button type="button" variant="secondary" onClick={() => void uploadLogo()} disabled={!logoFile || logoUploading}>
                      {logoUploading ? 'Enviando…' : 'Enviar logo'}
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => void removerLogo()} disabled={logoDeleting || (!logoBlobUrl && !logoLoading)}>
                      {logoDeleting ? 'Removendo…' : 'Remover logo'}
                    </Button>
                  </div>
                </div>
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="ce-cnpj" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  CNPJ {cnpjImutavel ? '' : <span className="text-red-600 dark:text-red-400">*</span>}
                </label>
                <div className="relative">
                  <input
                    id="ce-cnpj"
                    value={cnpj}
                    onChange={(e) => setCnpj(maskCnpjCpf(e.target.value))}
                    disabled={cnpjImutavel}
                    inputMode="numeric"
                    placeholder="00.000.000/0001-00"
                    className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-70 ${!cnpjImutavel ? 'pr-12' : ''}`}
                    autoComplete="organization"
                  />
                  {!cnpjImutavel ? (
                    <button
                      type="button"
                      onClick={() => void consultarCnpjReceita()}
                      disabled={loadingCnpjConsulta}
                      className="absolute right-1.5 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 disabled:pointer-events-none disabled:opacity-45 dark:text-slate-400 dark:hover:bg-slate-800/70 dark:hover:text-slate-200"
                      aria-label="Consultar CNPJ na Receita Federal"
                    >
                      {loadingCnpjConsulta ? (
                        <span
                          className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                          aria-hidden
                        />
                      ) : (
                        <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                          />
                        </svg>
                      )}
                    </button>
                  ) : null}
                </div>
              </div>
              <div>
                <label htmlFor="ce-rs" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Razão social
                </label>
                <input id="ce-rs" value={razaoSocial} onChange={(e) => setRazaoSocial(e.target.value)} className={fieldClass} />
              </div>
              <div>
                <label htmlFor="ce-nf" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Nome fantasia
                </label>
                <input id="ce-nf" value={nomeFantasia} onChange={(e) => setNomeFantasia(e.target.value)} className={fieldClass} />
              </div>
              <p className="sm:col-span-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                O nome exibido no sistema usa o nome fantasia; se estiver vazio, usa a razão social.
              </p>
              <div>
                <label htmlFor="ce-mail" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  E-mail
                </label>
                <input
                  id="ce-mail"
                  type="email"
                  value={emailEmpresa}
                  onChange={(e) => setEmailEmpresa(e.target.value)}
                  className={fieldClass}
                  autoComplete="email"
                />
              </div>
              <div>
                <label htmlFor="ce-tel" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Telefone
                </label>
                <input
                  id="ce-tel"
                  value={telefone}
                  onChange={(e) => setTelefone(maskTelefoneBr(e.target.value))}
                  className={fieldClass}
                  inputMode="tel"
                  placeholder="(00) 00000-0000"
                />
              </div>
              <div className="sm:col-span-2">
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Endereço
                </h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <label htmlFor="ce-end" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Logradouro
                    </label>
                    <input id="ce-end" value={endereco} onChange={(e) => setEndereco(e.target.value)} className={fieldClass} />
                  </div>
                  <div>
                    <label htmlFor="ce-num" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Número
                    </label>
                    <input id="ce-num" value={numero} onChange={(e) => setNumero(e.target.value)} className={fieldClass} />
                  </div>
                  <div>
                    <label htmlFor="ce-comp" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Complemento
                    </label>
                    <input id="ce-comp" value={complemento} onChange={(e) => setComplemento(e.target.value)} className={fieldClass} />
                  </div>
                  <div className="sm:col-span-2">
                    <label htmlFor="ce-bairro" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                      Bairro
                    </label>
                    <input id="ce-bairro" value={bairro} onChange={(e) => setBairro(e.target.value)} className={fieldClass} />
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:col-span-2 lg:grid-cols-3">
                    <div className="min-w-0">
                      <SelectUf
                        id="ce-uf"
                        value={estado}
                        onChange={(uf) => {
                          setEstado(uf)
                          setCidade('')
                        }}
                      />
                    </div>
                    <div className="min-w-0">
                      <SelectCidadeUf id="ce-cidade" uf={estado} value={cidade} onChange={setCidade} />
                    </div>
                    <div className="min-w-0">
                      <InputCepComBusca
                        id="ce-cep"
                        value={cep}
                        onChange={setCep}
                        onEnderecoCompleto={(d: CadastroAux.CepEndereco) => {
                          setEndereco(d.logradouro)
                          setBairro(d.bairro)
                          setCidade(d.localidade)
                          setEstado(d.uf)
                          if (d.complemento) setComplemento(d.complemento)
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 pt-2">
              <Button type="submit" disabled={salvandoEmpresa}>
                {salvandoEmpresa ? 'Salvando…' : 'Salvar empresa'}
              </Button>
            </div>
          </form>
        ) : (
          <div className="mt-6 space-y-8">
            <p className="max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Configure o <strong>encaminhamento</strong> por departamento (entrada de tickets). As{' '}
              <strong>respostas por e-mail</strong> são enviadas pela infraestrutura DX Connect — não é necessário criar
              conta Resend nem configurar SMTP na sua organização.
            </p>

            <div
              className={
                emailOutbound?.outbound_configured
                  ? 'max-w-3xl rounded-xl border border-emerald-200/80 bg-emerald-50/90 px-4 py-3 text-sm text-emerald-950 dark:border-emerald-900/50 dark:bg-emerald-950/25 dark:text-emerald-100'
                  : 'max-w-3xl rounded-xl border border-amber-200/80 bg-amber-50/90 px-4 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/25 dark:text-amber-100'
              }
            >
              <h3 className="font-semibold">Envio de respostas (plataforma)</h3>
              {emailOutbound?.outbound_configured ? (
                <p className="mt-1.5">
                  Ativo. Remetente:{' '}
                  <span className="font-mono">
                    {emailOutbound.transactional_from_name
                      ? `${emailOutbound.transactional_from_name} <${emailOutbound.transactional_from_email}>`
                      : emailOutbound.transactional_from_email}
                  </span>
                </p>
              ) : (
                <p className="mt-1.5">
                  Indisponível neste servidor. A equipa de operação deve definir{' '}
                  <span className="font-mono">RESEND_API_KEY</span> e{' '}
                  <span className="font-mono">TRANSACTIONAL_FROM_EMAIL</span> no ambiente (VPS). Enquanto isso, os
                  tickets por encaminhamento funcionam; respostas ao cliente pelo painel não saem por e-mail.
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void testarTransactional()}
                  disabled={testandoTransactional || !emailOutbound?.outbound_configured}
                >
                  {testandoTransactional ? 'Enviando…' : 'Enviar teste para o meu e-mail'}
                </Button>
              </div>
              <p className="mt-2 text-xs opacity-90">
                O teste usa o e-mail do administrador em sessão.
              </p>
            </div>

            <div className="max-w-3xl space-y-3 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-relaxed text-slate-700 dark:border-white/10 dark:bg-slate-900/40 dark:text-slate-300">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Acesso por tenant</h3>
              <p className="text-xs">
                Tenant <span className="font-mono font-semibold">{tenantInfo?.id ?? tenantId}</span>
                {tenantInfo?.nome ? ` — ${tenantInfo.nome}` : ''}. URL:{' '}
                <span className="font-mono">{tenantAppOrigin(tenantInfo?.id ?? tenantId) ?? '—'}</span>
              </p>
            </div>

            <section className="max-w-3xl space-y-4 rounded-xl border border-slate-200 p-4 dark:border-white/10">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    E-mails por departamento (encaminhamento)
                  </h3>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                    Cada setor ativo recebe automaticamente um endereço no formato{' '}
                    <span className="font-mono">
                      &lt;setor&gt;.t{tenantId}@…
                    </span>
                    . Configure o encaminhamento da caixa do cliente para o endereço correspondente.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={carregandoInbound}
                  onClick={() => void recarregarInbound()}
                >
                  {carregandoInbound ? 'A atualizar…' : 'Atualizar lista'}
                </Button>
              </div>

              {inboundAddresses.length === 0 ? (
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Nenhum setor ativo com endereço gerado. Cadastre setores em Configurações → Setores e volte aqui.
                </p>
              ) : null}

              {inboundAddresses.length > 0 ? (
                <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-white/10">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900/60 dark:text-slate-400">
                      <tr>
                        <th className="px-3 py-2 font-semibold">Setor</th>
                        <th className="px-3 py-2 font-semibold">E-mail para encaminhamento</th>
                        <th className="px-3 py-2 font-semibold w-24" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-white/10">
                      {inboundAddresses.map((a) => (
                        <tr key={a.id}>
                          <td className="px-3 py-2.5 font-medium text-slate-900 dark:text-slate-100">
                            {a.setor_nome ?? a.label ?? '—'}
                          </td>
                          <td className="px-3 py-2.5 font-mono text-xs sm:text-sm text-slate-800 dark:text-slate-200">
                            {a.full_address}
                          </td>
                          <td className="px-3 py-2.5">
                            <Button type="button" variant="secondary" onClick={() => void copiarEndereco(a.full_address)}>
                              Copiar
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              <div className="rounded-lg border border-sky-200/80 bg-sky-50/90 px-4 py-3 text-sm leading-relaxed text-sky-950 dark:border-sky-900/50 dark:bg-sky-950/25 dark:text-sky-100">
                <h4 className="font-semibold text-sky-950 dark:text-sky-50">O que o cliente deve fazer</h4>
                <ol className="mt-2 list-decimal space-y-2 pl-5">
                  <li>
                    Para cada departamento da tabela, abra as configurações da caixa de e-mail usada por essa equipa (ex.{' '}
                    <span className="font-mono">suporte@empresa.com.br</span>).
                  </li>
                  <li>
                    Ative <strong>encaminhamento automático</strong> ou <strong>reenvio</strong> (Gmail: Configurações →
                    Encaminhamento; Outlook: Regras → Encaminhar para).
                  </li>
                  <li>
                    Adicione o endereço DX Connect do setor (botão <strong>Copiar</strong>) como destino do encaminhamento.
                    Mantenha uma cópia na caixa original se a ferramenta permitir.
                  </li>
                  <li>
                    Guarde e envie um e-mail de teste para a caixa do cliente; o ticket deve aparecer no setor correto no
                    painel.
                  </li>
                  <li>Repita para todos os departamentos listados acima.</li>
                </ol>
                <p className="mt-3 text-xs text-sky-900/90 dark:text-sky-200/80">
                  Não é necessário criar endereços manualmente: ao cadastrar um setor ativo, o sistema gera o e-mail{' '}
                  <span className="font-mono">slug-do-setor.t{tenantId}</span>{' '}
                  na próxima atualização desta lista.
                </p>
              </div>
            </section>

          </div>
        )}
      </Card>
    </div>
  )
}
