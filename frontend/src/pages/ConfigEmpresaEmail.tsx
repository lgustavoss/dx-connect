import { useCallback, useEffect, useRef, useState } from 'react'
import {
  API_VERSION_PREFIX,
  empresas,
  fetchEmpresaSistemaLogoBlob,
  resolvedApiBaseUrl,
  setores,
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
import { IconEye, IconEyeOff } from '../components/ui/IconEye'
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

  const [transactionalFromEmail, setTransactionalFromEmail] = useState('')
  const [transactionalFromName, setTransactionalFromName] = useState('')
  const [resendApiKey, setResendApiKey] = useState('')
  const [resendApiKeyTouched, setResendApiKeyTouched] = useState(false)
  const [hadResendApiKey, setHadResendApiKey] = useState(false)
  const [resendApiKeyCampoVisivel, setResendApiKeyCampoVisivel] = useState(true)
  const [showResendKey, setShowResendKey] = useState(false)

  const [salvandoEmail, setSalvandoEmail] = useState(false)
  const [testandoTransactional, setTestandoTransactional] = useState(false)

  const tenantId = resolveTenantIdFromHostname()
  const [tenantInfo, setTenantInfo] = useState<TenantApi.TenantRead | null>(null)
  const [inboundAddresses, setInboundAddresses] = useState<TenantApi.InboundAddressRead[]>([])
  const [setoresLista, setSetoresLista] = useState<Array<{ id: number; nome: string }>>([])
  const [inboundLocalPart, setInboundLocalPart] = useState(`${tenantId}_suporte`)
  const [inboundLabel, setInboundLabel] = useState('Suporte')
  const [inboundSetorId, setInboundSetorId] = useState<number | ''>('')
  const [criandoInbound, setCriandoInbound] = useState(false)

  useEffect(() => {
    logoBlobUrlRef.current = logoBlobUrl
  }, [logoBlobUrl])

  const carregar = useCallback(async () => {
    setLoading(true)
    try {
      const [emp, mail, tenantAtual, inbound, setoresPag] = await Promise.all([
        systemSettings.getEmpresaSistema(),
        systemSettings.getEmail(),
        tenantApi.getAtual().catch(() => null),
        tenantApi.listInboundAddresses().catch(() => [] as TenantApi.InboundAddressRead[]),
        setores.list({ limit: 100 }).catch(() => ({ items: [] as Array<{ id: number; nome: string }> })),
      ])
      setTenantInfo(tenantAtual)
      setInboundAddresses(inbound)
      const setorItems = setoresPag.items ?? []
      setSetoresLista(setorItems.map((s) => ({ id: s.id, nome: s.nome })))
      if (setorItems.length && inboundSetorId === '') {
        setInboundSetorId(setorItems[0].id)
      }

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

      setTransactionalFromEmail((mail.transactional_from_email ?? '').trim())
      setTransactionalFromName((mail.transactional_from_name ?? '').trim())
      setResendApiKey('')
      setResendApiKeyTouched(false)
      const temKey = Boolean(mail.has_transactional_api_key)
      setHadResendApiKey(temKey)
      setResendApiKeyCampoVisivel(!temKey)
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

  function montarPayloadEmail(): SystemSettings.EmailSettingsUpdate {
    const p: SystemSettings.EmailSettingsUpdate = {
      transactional_from_email: transactionalFromEmail.trim() || null,
      transactional_from_name: transactionalFromName.trim() || null,
    }
    if (resendApiKeyTouched) {
      p.transactional_api_key = resendApiKey.trim() === '' ? '' : resendApiKey.trim()
    }
    return p
  }

  async function salvarEmail(e: React.FormEvent) {
    e.preventDefault()
    setSalvandoEmail(true)
    try {
      const mail = await systemSettings.putEmail(montarPayloadEmail())
      const temKey = Boolean(mail.has_transactional_api_key)
      setHadResendApiKey(temKey)
      setResendApiKeyCampoVisivel(!temKey)
      setResendApiKey('')
      setResendApiKeyTouched(false)
      toast.showSuccess('Configuração de e-mail salva.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o e-mail.'))
    } finally {
      setSalvandoEmail(false)
    }
  }

  async function criarEnderecoInbound(e: React.FormEvent) {
    e.preventDefault()
    if (!inboundSetorId) {
      toast.showWarning('Selecione o setor de destino.')
      return
    }
    setCriandoInbound(true)
    try {
      const row = await tenantApi.createInboundAddress({
        local_part: inboundLocalPart.trim(),
        label: inboundLabel.trim() || null,
        setor_id: Number(inboundSetorId),
      })
      setInboundAddresses((prev) => [...prev, row].sort((a, b) => a.local_part.localeCompare(b.local_part)))
      toast.showSuccess('Endereço de encaminhamento criado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível criar o endereço.'))
    } finally {
      setCriandoInbound(false)
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
          Dados institucionais da instalação e envio transaccional (Resend) para tickets e mensagens do sistema
          (apenas administradores).
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
          <form onSubmit={salvarEmail} className="mt-6 space-y-8">
            <p className="max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              O envio de e-mails (respostas da equipa, auto-respostas e testes) usa a API{' '}
              <a
                href="https://resend.com/docs"
                className="text-sky-600 underline decoration-sky-500/40 underline-offset-2 hover:text-sky-700 dark:text-sky-400 dark:hover:text-sky-300"
                target="_blank"
                rel="noreferrer"
              >
                Resend
              </a>
              . Crie uma API key no painel da Resend, verifique o domínio ou use o remetente de teste indicado por eles,
              e guarde os dados abaixo.
            </p>

            <div className="max-w-3xl space-y-3 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-relaxed text-slate-700 dark:border-white/10 dark:bg-slate-900/40 dark:text-slate-300">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Acesso por tenant</h3>
              <p className="text-xs">
                Tenant <span className="font-mono font-semibold">{tenantInfo?.id ?? tenantId}</span>
                {tenantInfo?.nome ? ` — ${tenantInfo.nome}` : ''}. URL:{' '}
                <span className="font-mono">{tenantAppOrigin(tenantInfo?.id ?? tenantId) ?? '—'}</span>
              </p>
            </div>

            <section className="max-w-3xl space-y-4 rounded-xl border border-slate-200 p-4 dark:border-white/10">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Encaminhamento de e-mail</h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Endereço por canal (ex. <span className="font-mono">{tenantId}_comercial</span>). Encaminhe a caixa do
                cliente para esse endereço. Identificador deve começar por <span className="font-mono">{tenantId}_</span>.
              </p>
              {inboundAddresses.map((a) => (
                <p key={a.id} className="font-mono text-sm">
                  {a.full_address} <span className="text-slate-500">({a.label || a.setor_nome})</span>
                </p>
              ))}
              <form onSubmit={criarEnderecoInbound} className="grid gap-3 sm:grid-cols-2">
                <input
                  value={inboundLocalPart}
                  onChange={(e) => setInboundLocalPart(e.target.value)}
                  className={fieldClass}
                  placeholder={`${tenantId}_suporte`}
                />
                <input value={inboundLabel} onChange={(e) => setInboundLabel(e.target.value)} className={fieldClass} placeholder="Rótulo" />
                <select
                  value={inboundSetorId === '' ? '' : String(inboundSetorId)}
                  onChange={(e) => setInboundSetorId(e.target.value ? Number(e.target.value) : '')}
                  className={`${fieldClass} sm:col-span-2`}
                >
                  <option value="">Setor…</option>
                  {setoresLista.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.nome}
                    </option>
                  ))}
                </select>
                <Button type="submit" variant="secondary" disabled={criandoInbound} className="sm:col-span-2">
                  {criandoInbound ? 'A criar…' : 'Adicionar endereço'}
                </Button>
              </form>
            </section>

            <div className="max-w-3xl space-y-3 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-relaxed text-slate-700 dark:border-white/10 dark:bg-slate-900/40 dark:text-slate-300">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Ingestão por webhook (tickets)</h3>
              <p>
                O destinatário (<span className="font-mono">local@inbound…</span>) define tenant e setor quando
                configurado acima.
              </p>
              <p className="font-mono text-xs text-slate-800 dark:text-slate-200">
                POST {resolvedApiBaseUrl()}
                {API_VERSION_PREFIX}/webhooks/email-inbound
              </p>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Cabeçalho obrigatório: <span className="font-mono text-slate-800 dark:text-slate-200">X-Dx-Email-Webhook-Secret</span>.
                A Resend configurada aqui é usada para o envio ao cliente (respostas da equipa e e-mail automático quando
                a thread continua mas o chamado original já estiver encerrado).
              </p>
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Campos úteis na resposta JSON:</p>
              <ul className="list-inside list-disc space-y-1 text-xs text-slate-600 dark:text-slate-400">
                <li>
                  <span className="font-mono text-slate-800 dark:text-slate-200">duplicate</span> — reenvio do mesmo
                  Message-ID.
                </li>
                <li>
                  <span className="font-mono text-slate-800 dark:text-slate-200">threaded</span> — mensagem ligada a um
                  ticket <strong>aberto</strong> (mesma thread).
                </li>
                <li>
                  <span className="font-mono text-slate-800 dark:text-slate-200">after_close_new_ticket</span> — criado
                  ticket de triagem porque a thread apontava para um chamado já fechado.
                </li>
                <li>
                  <span className="font-mono text-slate-800 dark:text-slate-200">auto_reply_sent</span> — enviada
                  resposta automática ao remetente (se Resend estiver configurada).
                </li>
              </ul>
            </div>

            <section className="max-w-xl space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Resend (envio transaccional)
              </h3>
              <div>
                <label htmlFor="ce-resend-key" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  API Key
                </label>
                {hadResendApiKey && !resendApiKeyTouched && resendApiKey === '' && !resendApiKeyCampoVisivel ? (
                  <div className="space-y-2">
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      A chave está guardada no servidor (não é mostrada). Use o botão abaixo só para substituir ou remover.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <div
                        className={`${fieldClass} flex min-h-[2.75rem] flex-1 items-center text-slate-500 dark:text-slate-400`}
                        role="status"
                      >
                        <span className="select-none tracking-[0.35em]" aria-hidden>
                          ••••••••••
                        </span>
                      </div>
                      <Button type="button" variant="secondary" onClick={() => setResendApiKeyCampoVisivel(true)}>
                        Substituir ou remover
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="relative">
                    <input
                      id="ce-resend-key"
                      type={showResendKey ? 'text' : 'password'}
                      value={resendApiKey}
                      onChange={(e) => {
                        setResendApiKey(e.target.value)
                        setResendApiKeyTouched(true)
                      }}
                      autoComplete="new-password"
                      className={`${fieldClass} pr-12`}
                      placeholder="re_…"
                    />
                    <button
                      type="button"
                      onClick={() => setShowResendKey((v) => !v)}
                      className="absolute right-1.5 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-slate-800/70 dark:hover:text-slate-200"
                      aria-label={showResendKey ? 'Ocultar' : 'Mostrar'}
                      aria-pressed={showResendKey}
                    >
                      {showResendKey ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
                    </button>
                  </div>
                )}
                {hadResendApiKey && resendApiKeyCampoVisivel ? (
                  <button
                    type="button"
                    className="mt-1.5 text-left text-xs text-slate-500 underline decoration-slate-400/80 underline-offset-2 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                    onClick={() => {
                      setResendApiKeyCampoVisivel(false)
                      setResendApiKey('')
                      setResendApiKeyTouched(false)
                    }}
                  >
                    Manter a chave guardada e voltar ao resumo
                  </button>
                ) : null}
                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                  Também pode definir <span className="font-mono">RESEND_API_KEY</span> no servidor em vez de gravar aqui.
                </p>
              </div>
              <div>
                <label htmlFor="ce-from-email" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  E-mail remetente (From)
                </label>
                <input
                  id="ce-from-email"
                  type="email"
                  value={transactionalFromEmail}
                  onChange={(e) => setTransactionalFromEmail(e.target.value)}
                  className={fieldClass}
                  placeholder="onboarding@resend.dev ou o seu domínio verificado"
                />
              </div>
              <div>
                <label htmlFor="ce-from-name" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Nome remetente (opcional)
                </label>
                <input
                  id="ce-from-name"
                  value={transactionalFromName}
                  onChange={(e) => setTransactionalFromName(e.target.value)}
                  className={fieldClass}
                  placeholder="Suporte DX Connect"
                />
              </div>
            </section>

            <div className="flex flex-wrap gap-3 border-t border-slate-200 pt-4 dark:border-slate-700/80">
              <Button type="submit" disabled={salvandoEmail}>
                {salvandoEmail ? 'Salvando…' : 'Salvar e-mail'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => void testarTransactional()}
                disabled={testandoTransactional}
              >
                {testandoTransactional ? 'Enviando…' : 'Enviar teste para o meu e-mail'}
              </Button>
            </div>
            <p className="max-w-xl text-xs text-slate-500 dark:text-slate-400">
              O teste usa o endereço do utilizador administrador em sessão. Confirme que esse utilizador tem e-mail
              válido no cadastro.
            </p>
          </form>
        )}
      </Card>
    </div>
  )
}
