import { useCallback, useEffect, useRef, useState } from 'react'
import { empresas, fetchEmpresaSistemaLogoBlob, systemSettings, type SystemSettings } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { InputCepComBusca } from '../components/ui/InputCepComBusca'
import { SelectCidadeUf } from '../components/ui/SelectCidadeUf'
import { SelectUf } from '../components/ui/SelectUf'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { IconEye, IconEyeOff } from '../components/ui/IconEye'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { digitsOnly, isCnpj, maskCep, maskCnpjCpf, maskTelefoneBr } from '../utils/masks'

type Aba = 'empresa' | 'email'

const fieldClass =
  'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-[0.9375rem] text-slate-900 shadow-inner placeholder:text-slate-400 focus:border-cyan-500/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/25 dark:border-white/10 dark:bg-white/[0.06] dark:text-slate-100 dark:placeholder:text-slate-500'

function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  hint,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  autoComplete: string
  hint?: string
}) {
  const [show, setShow] = useState(false)
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      {hint ? <p className="mb-1.5 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          className={`${fieldClass} pr-12`}
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          className="absolute right-1.5 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-slate-800/70 dark:hover:text-slate-200"
          aria-label={show ? 'Ocultar' : 'Mostrar'}
          aria-pressed={show}
        >
          {show ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
        </button>
      </div>
    </div>
  )
}

export function ConfigEmpresaEmail() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [aba, setAba] = useState<Aba>('empresa')
  const loadSeqRef = useRef(0)
  const logoBlobUrlRef = useRef<string | null>(null)

  const [cnpj, setCnpj] = useState('')
  const [cnpjImutavel, setCnpjImutavel] = useState(false)
  const [loadingCnpj, setLoadingCnpj] = useState(false)
  const [razaoSocial, setRazaoSocial] = useState('')
  const [nomeFantasia, setNomeFantasia] = useState('')
  const [emailEmpresa, setEmailEmpresa] = useState('')
  const [telefone, setTelefone] = useState('')
  const [enderecoLogradouro, setEnderecoLogradouro] = useState('')
  const [enderecoNumero, setEnderecoNumero] = useState('')
  const [enderecoComplemento, setEnderecoComplemento] = useState('')
  const [enderecoBairro, setEnderecoBairro] = useState('')
  const [enderecoCidade, setEnderecoCidade] = useState('')
  const [enderecoUf, setEnderecoUf] = useState('')
  const [enderecoCep, setEnderecoCep] = useState('')
  const [empresaAtiva, setEmpresaAtiva] = useState(true)
  const [salvandoEmpresa, setSalvandoEmpresa] = useState(false)
  const [logoBlobUrl, setLogoBlobUrl] = useState<string | null>(null)
  const [logoLoading, setLogoLoading] = useState(false)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [logoDeleting, setLogoDeleting] = useState(false)

  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState('')
  const [smtpUser, setSmtpUser] = useState('')
  const [smtpPassword, setSmtpPassword] = useState('')
  const [smtpPasswordTouched, setSmtpPasswordTouched] = useState(false)
  const [hadSmtpPassword, setHadSmtpPassword] = useState(false)
  const [smtpStarttls, setSmtpStarttls] = useState(true)
  const [smtpFromEmail, setSmtpFromEmail] = useState('')
  const [smtpFromName, setSmtpFromName] = useState('')

  const [imapHost, setImapHost] = useState('')
  const [imapPort, setImapPort] = useState('')
  const [imapUser, setImapUser] = useState('')
  const [imapPassword, setImapPassword] = useState('')
  const [imapPasswordTouched, setImapPasswordTouched] = useState(false)
  const [hadImapPassword, setHadImapPassword] = useState(false)
  const [imapSsl, setImapSsl] = useState(true)
  const [imapFolder, setImapFolder] = useState('')

  const [salvandoEmail, setSalvandoEmail] = useState(false)
  const [testandoSmtp, setTestandoSmtp] = useState(false)
  const [testandoImap, setTestandoImap] = useState(false)

  const carregar = useCallback(async () => {
    const seq = ++loadSeqRef.current
    setLoading(true)
    try {
      const [emp, mail] = await Promise.all([
        systemSettings.getEmpresaSistema(),
        systemSettings.getEmail(),
      ])

      if (seq !== loadSeqRef.current) return

      const cj = (emp.cnpj ?? '').trim()
      setCnpj(cj)
      setCnpjImutavel(Boolean(cj))
      setRazaoSocial((emp.razao_social ?? '').trim())
      setNomeFantasia((emp.nome_fantasia ?? '').trim())
      setEmailEmpresa((emp.email ?? '').trim())
      setTelefone((emp.telefone ?? '').trim())
      // endereço: backend guarda em string única; aqui mostramos campos organizados.
      // Estratégia: se não for possível “parsear”, coloca tudo em logradouro para não perder informação.
      const endRaw = (emp.endereco ?? '').trim()
      setEnderecoLogradouro(endRaw)
      setEnderecoNumero('')
      setEnderecoComplemento('')
      setEnderecoBairro('')
      setEnderecoCidade('')
      setEnderecoUf('')
      setEnderecoCep('')
      setEmpresaAtiva(emp.ativo !== false)

      // logo: precisa de fetch autenticado (não dá pra usar <img src> direto).
      if (logoBlobUrlRef.current) URL.revokeObjectURL(logoBlobUrlRef.current)
      logoBlobUrlRef.current = null
      setLogoBlobUrl(null)
      if (emp.logo_url) {
        setLogoLoading(true)
        try {
          const b = await fetchEmpresaSistemaLogoBlob()
          if (seq !== loadSeqRef.current) return
          if (b) {
            const u = URL.createObjectURL(b)
            logoBlobUrlRef.current = u
            setLogoBlobUrl(u)
          }
        } finally {
          setLogoLoading(false)
        }
      }

      if (seq !== loadSeqRef.current) return

      setSmtpHost((mail.smtp_host ?? '').trim())
      setSmtpPort(mail.smtp_port != null ? String(mail.smtp_port) : '')
      setSmtpUser((mail.smtp_user ?? '').trim())
      setSmtpPassword('')
      setSmtpPasswordTouched(false)
      setHadSmtpPassword(Boolean(mail.has_smtp_password))
      setSmtpStarttls(mail.smtp_use_starttls !== false)
      setSmtpFromEmail((mail.smtp_from_email ?? '').trim())
      setSmtpFromName((mail.smtp_from_name ?? '').trim())

      setImapHost((mail.imap_host ?? '').trim())
      setImapPort(mail.imap_port != null ? String(mail.imap_port) : '')
      setImapUser((mail.imap_user ?? '').trim())
      setImapPassword('')
      setImapPasswordTouched(false)
      setHadImapPassword(Boolean(mail.has_imap_password))
      setImapSsl(mail.imap_use_ssl !== false)
      setImapFolder((mail.imap_folder ?? '').trim())
    } catch (err) {
      if (seq === loadSeqRef.current) {
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as configurações.'))
      }
    } finally {
      if (seq === loadSeqRef.current) setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    void carregar()
    // carregar é estável (deps só de toast), então roda apenas no mount.
  }, [])

  useEffect(() => {
    if (logoPreviewUrl) return () => URL.revokeObjectURL(logoPreviewUrl)
  }, [logoPreviewUrl])

  useEffect(() => {
    return () => {
      if (logoBlobUrlRef.current) URL.revokeObjectURL(logoBlobUrlRef.current)
      if (logoPreviewUrl) URL.revokeObjectURL(logoPreviewUrl)
    }
  }, [logoPreviewUrl])

  async function salvarEmpresa() {
    const cnpjTrim = cnpj.trim()
    if (!cnpjImutavel && !cnpjTrim) {
      toast.showError('Informe o CNPJ da empresa do sistema.')
      return
    }
    setSalvandoEmpresa(true)
    try {
      const parts1 = [enderecoLogradouro.trim()].filter(Boolean)
      const num = enderecoNumero.trim()
      const comp = enderecoComplemento.trim()
      const numComp = [num, comp].filter(Boolean).join(' ')
      if (numComp) parts1.push(numComp)
      const linha1 = parts1.join(', ')
      const linha2 = [enderecoBairro.trim()].filter(Boolean).join('')
      const cidade = enderecoCidade.trim()
      const uf = enderecoUf.trim().toUpperCase()
      const cidadeUf = [cidade, uf].filter(Boolean).join('/')
      const cep = digitsOnly(enderecoCep)
      const linha3 = [cidadeUf, cep ? `CEP ${maskCep(cep)}` : ''].filter(Boolean).join(' - ')
      const enderecoUnico = [linha1, linha2, linha3].filter(Boolean).join(' - ') || null

      const payload: SystemSettings.EmpresaSistemaUpdate = {
        razao_social: razaoSocial.trim() || null,
        nome_fantasia: nomeFantasia.trim() || null,
        email: emailEmpresa.trim() || null,
        telefone: telefone.trim() || null,
        endereco: enderecoUnico,
        ativo: empresaAtiva,
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

  async function consultarCnpj() {
    // invalida qualquer load em andamento para não sobrescrever o state preenchido pela consulta
    loadSeqRef.current += 1
    const d = digitsOnly(cnpj)
    if (!isCnpj(cnpj)) {
      toast.showWarning('Informe um CNPJ com 14 dígitos para consultar.')
      return
    }
    setLoadingCnpj(true)
    try {
      const data = await empresas.consultarCnpj(d)
      setCnpj(maskCnpjCpf(d))
      setRazaoSocial((data.razao_social ?? '').trim())
      setNomeFantasia((data.nome_fantasia ?? '').trim())

      setEnderecoLogradouro((data.endereco ?? '').trim())
      setEnderecoNumero((data.numero ?? '').trim())
      setEnderecoComplemento((data.complemento ?? '').trim())
      setEnderecoBairro((data.bairro ?? '').trim())
      setEnderecoCidade((data.cidade ?? '').trim())
      setEnderecoUf((data.estado ?? '').trim().toUpperCase())
      setEnderecoCep(data.cep ? maskCep(String(data.cep)) : '')

      setEmailEmpresa((data.email ?? '').trim())
      setTelefone(data.telefone ? maskTelefoneBr(data.telefone) : '')

      toast.showSuccess('Dados preenchidos com sucesso.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Erro ao consultar CNPJ.'))
    } finally {
      setLoadingCnpj(false)
    }
  }

  function montarPayloadEmail(): SystemSettings.EmailSettingsUpdate {
    const p: SystemSettings.EmailSettingsUpdate = {
      smtp_host: smtpHost.trim() || null,
      smtp_port: smtpPort.trim() ? Number.parseInt(smtpPort.trim(), 10) : null,
      smtp_user: smtpUser.trim() || null,
      smtp_use_starttls: smtpStarttls,
      smtp_from_email: smtpFromEmail.trim() || null,
      smtp_from_name: smtpFromName.trim() || null,
      imap_host: imapHost.trim() || null,
      imap_port: imapPort.trim() ? Number.parseInt(imapPort.trim(), 10) : null,
      imap_user: imapUser.trim() || null,
      imap_use_ssl: imapSsl,
      imap_folder: imapFolder.trim() || null,
    }
    if (smtpPasswordTouched) {
      p.smtp_password = smtpPassword.trim() === '' ? '' : smtpPassword
    }
    if (imapPasswordTouched) {
      p.imap_password = imapPassword.trim() === '' ? '' : imapPassword
    }
    return p
  }

  async function salvarEmail() {
    if (smtpPort.trim() && Number.isNaN(Number.parseInt(smtpPort.trim(), 10))) {
      toast.showError('Porta SMTP inválida.')
      return
    }
    if (imapPort.trim() && Number.isNaN(Number.parseInt(imapPort.trim(), 10))) {
      toast.showError('Porta IMAP inválida.')
      return
    }
    setSalvandoEmail(true)
    try {
      const mail = await systemSettings.putEmail(montarPayloadEmail())
      setHadSmtpPassword(Boolean(mail.has_smtp_password))
      setHadImapPassword(Boolean(mail.has_imap_password))
      setSmtpPassword('')
      setImapPassword('')
      setSmtpPasswordTouched(false)
      setImapPasswordTouched(false)
      toast.showSuccess('Configuração de e-mail salva.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o e-mail.'))
    } finally {
      setSalvandoEmail(false)
    }
  }

  async function testarSmtp() {
    setTestandoSmtp(true)
    try {
      const r = await systemSettings.testEmailSmtp()
      if (r.ok) {
        toast.showSuccess(r.detail?.trim() || 'SMTP OK.')
      } else {
        toast.showError(r.detail?.trim() || 'Falha ao testar SMTP.')
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível testar SMTP.'))
    } finally {
      setTestandoSmtp(false)
    }
  }

  async function testarImap() {
    setTestandoImap(true)
    try {
      const r = await systemSettings.testEmailImap()
      if (r.ok) {
        toast.showSuccess(r.detail?.trim() || 'IMAP OK.')
      } else {
        toast.showError(r.detail?.trim() || 'Falha ao testar IMAP.')
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível testar IMAP.'))
    } finally {
      setTestandoImap(false)
    }
  }

  if (loading) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <Card title="Empresa do sistema e e-mail">
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Dados institucionais da instalação e credenciais SMTP/IMAP usadas pelo sistema (apenas administradores).
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
          <div className="mt-6 space-y-4">
            <div className="rounded-lg border border-amber-200/80 bg-amber-50/90 px-3 py-2 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100">
              O CNPJ é obrigatório no primeiro cadastro. Depois de salvo, <strong>não pode ser alterado</strong>.
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/40">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Logo</h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Envie uma imagem (PNG/JPG/WEBP). Tamanho recomendado: até 2MB.
              </p>

              <div className="mt-4 flex flex-col gap-3">
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
                      O sistema usa esse logo nas telas e relatórios.
                    </p>
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

            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/40">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Identificação</h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Dados obtidos pelo CNPJ podem preencher os campos automaticamente.
              </p>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Input
                    id="ce-cnpj"
                    label={cnpjImutavel ? 'CNPJ' : 'CNPJ *'}
                    inputMode="numeric"
                    placeholder="00.000.000/0001-00"
                    value={cnpj}
                    onChange={(e) => setCnpj(maskCnpjCpf(e.target.value))}
                    disabled={cnpjImutavel}
                    autoComplete="organization"
                    endAdornment={
                      <button
                        type="button"
                        onClick={consultarCnpj}
                        disabled={loadingCnpj}
                        className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 disabled:pointer-events-none disabled:opacity-45 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                        aria-label="Consultar CNPJ"
                      >
                        {loadingCnpj ? (
                          <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
                        ) : (
                          <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                        )}
                      </button>
                    }
                  />
                </div>
                <div>
                  <label htmlFor="ce-rs" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Razão social
                  </label>
                  <input
                    id="ce-rs"
                    value={razaoSocial}
                    onChange={(e) => setRazaoSocial(e.target.value)}
                    className={fieldClass}
                  />
                </div>
                <div>
                  <label htmlFor="ce-nf" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Nome fantasia
                  </label>
                  <input
                    id="ce-nf"
                    value={nomeFantasia}
                    onChange={(e) => setNomeFantasia(e.target.value)}
                    className={fieldClass}
                  />
                </div>
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
                  <input id="ce-tel" value={telefone} onChange={(e) => setTelefone(e.target.value)} className={fieldClass} />
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/40">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Endereço</h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Campos organizados; o backend guarda em um único texto por compatibilidade.
              </p>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label htmlFor="ce-end-log" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Logradouro
                  </label>
                  <input
                    id="ce-end-log"
                    value={enderecoLogradouro}
                    onChange={(e) => setEnderecoLogradouro(e.target.value)}
                    className={fieldClass}
                  />
                </div>
                <div>
                  <label htmlFor="ce-end-num" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Número
                  </label>
                  <input
                    id="ce-end-num"
                    value={enderecoNumero}
                    onChange={(e) => setEnderecoNumero(e.target.value)}
                    className={fieldClass}
                  />
                </div>
                <div>
                  <label htmlFor="ce-end-comp" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Complemento
                  </label>
                  <input
                    id="ce-end-comp"
                    value={enderecoComplemento}
                    onChange={(e) => setEnderecoComplemento(e.target.value)}
                    className={fieldClass}
                  />
                </div>
                <div>
                  <label htmlFor="ce-end-bairro" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Bairro
                  </label>
                  <input
                    id="ce-end-bairro"
                    value={enderecoBairro}
                    onChange={(e) => setEnderecoBairro(e.target.value)}
                    className={fieldClass}
                  />
                </div>
                <div>
                  <InputCepComBusca
                    id="ce-end-cep"
                    value={enderecoCep}
                    onChange={setEnderecoCep}
                    onEnderecoCompleto={(d) => {
                      setEnderecoLogradouro((d.logradouro ?? '').trim() || enderecoLogradouro)
                      setEnderecoBairro((d.bairro ?? '').trim() || enderecoBairro)
                      setEnderecoCidade((d.localidade ?? '').trim() || enderecoCidade)
                      setEnderecoUf((d.uf ?? '').trim().toUpperCase() || enderecoUf)
                    }}
                  />
                </div>
                <div>
                  <SelectUf id="ce-end-uf" value={enderecoUf} onChange={(uf) => { setEnderecoUf(uf); setEnderecoCidade('') }} />
                </div>
                <div className="sm:col-span-2">
                  <SelectCidadeUf id="ce-end-cidade" uf={enderecoUf} value={enderecoCidade} onChange={setEnderecoCidade} />
                </div>
              </div>
            </div>
            <Switch checked={empresaAtiva} onCheckedChange={setEmpresaAtiva} label="Empresa ativa" bare className="pt-1" />
            <div className="flex flex-wrap gap-3 pt-2">
              <Button type="button" disabled={salvandoEmpresa} onClick={() => void salvarEmpresa()}>
                {salvandoEmpresa ? 'Salvando…' : 'Salvar empresa'}
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-6 space-y-8">
            <section className="space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">SMTP (envio)</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="ce-sh" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Servidor
                  </label>
                  <input id="ce-sh" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} className={fieldClass} />
                </div>
                <div>
                  <label htmlFor="ce-sp" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Porta
                  </label>
                  <input id="ce-sp" value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} className={fieldClass} inputMode="numeric" />
                </div>
                <div>
                  <label htmlFor="ce-su" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Usuário
                  </label>
                  <input id="ce-su" value={smtpUser} onChange={(e) => setSmtpUser(e.target.value)} className={fieldClass} autoComplete="off" />
                </div>
                <PasswordField
                  id="ce-spw"
                  label="Senha SMTP"
                  value={smtpPassword}
                  onChange={(v) => {
                    setSmtpPassword(v)
                    setSmtpPasswordTouched(true)
                  }}
                  autoComplete="new-password"
                  hint={
                    hadSmtpPassword && !smtpPasswordTouched
                      ? 'Já existe uma senha salva. Deixe em branco para manter; digite para substituir; salve com o campo vazio para remover.'
                      : hadSmtpPassword
                        ? 'Vazio ao salvar remove a senha salva.'
                        : undefined
                  }
                />
                <div>
                  <label htmlFor="ce-sfe" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    E-mail remetente (From)
                  </label>
                  <input
                    id="ce-sfe"
                    type="email"
                    value={smtpFromEmail}
                    onChange={(e) => setSmtpFromEmail(e.target.value)}
                    className={fieldClass}
                  />
                </div>
                <div>
                  <label htmlFor="ce-sfn" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Nome remetente
                  </label>
                  <input id="ce-sfn" value={smtpFromName} onChange={(e) => setSmtpFromName(e.target.value)} className={fieldClass} />
                </div>
              </div>
              <Switch
                checked={smtpStarttls}
                onCheckedChange={setSmtpStarttls}
                label="STARTTLS"
                description="Ative se o servidor exigir TLS na porta (ex.: 587)."
                bare
              />
              <div className="flex flex-wrap gap-3">
                <Button type="button" variant="secondary" onClick={() => void testarSmtp()} disabled={testandoSmtp}>
                  {testandoSmtp ? 'Testando…' : 'Testar SMTP'}
                </Button>
              </div>
            </section>

            <section className="space-y-4 border-t border-slate-200 pt-6 dark:border-slate-700/80">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">IMAP (recepção)</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="ce-ih" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Servidor
                  </label>
                  <input id="ce-ih" value={imapHost} onChange={(e) => setImapHost(e.target.value)} className={fieldClass} />
                </div>
                <div>
                  <label htmlFor="ce-ip" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Porta
                  </label>
                  <input id="ce-ip" value={imapPort} onChange={(e) => setImapPort(e.target.value)} className={fieldClass} inputMode="numeric" />
                </div>
                <div>
                  <label htmlFor="ce-iu" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Usuário
                  </label>
                  <input id="ce-iu" value={imapUser} onChange={(e) => setImapUser(e.target.value)} className={fieldClass} autoComplete="off" />
                </div>
                <PasswordField
                  id="ce-ipw"
                  label="Senha IMAP"
                  value={imapPassword}
                  onChange={(v) => {
                    setImapPassword(v)
                    setImapPasswordTouched(true)
                  }}
                  autoComplete="new-password"
                  hint={
                    hadImapPassword && !imapPasswordTouched
                      ? 'Já existe uma senha salva. Deixe em branco para manter; digite para substituir; salve com o campo vazio para remover.'
                      : hadImapPassword
                        ? 'Vazio ao salvar remove a senha salva.'
                        : undefined
                  }
                />
                <div className="sm:col-span-2">
                  <label htmlFor="ce-if" className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Pasta (opcional)
                  </label>
                  <input id="ce-if" value={imapFolder} onChange={(e) => setImapFolder(e.target.value)} className={fieldClass} />
                </div>
              </div>
              <Switch
                checked={imapSsl}
                onCheckedChange={setImapSsl}
                label="SSL/TLS (porta típica 993)"
                bare
              />
              <div className="flex flex-wrap gap-3">
                <Button type="button" variant="secondary" onClick={() => void testarImap()} disabled={testandoImap}>
                  {testandoImap ? 'Testando…' : 'Testar IMAP'}
                </Button>
              </div>
            </section>

            <div className="flex flex-wrap gap-3 border-t border-slate-200 pt-4 dark:border-slate-700/80">
              <Button type="button" disabled={salvandoEmail} onClick={() => void salvarEmail()}>
                {salvandoEmail ? 'Salvando…' : 'Salvar e-mail'}
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
