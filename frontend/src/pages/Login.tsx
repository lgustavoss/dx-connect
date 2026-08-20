import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { clearAuthToken } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import {
  BrandLogo,
  LOGIN_EMAIL_STORAGE_KEY,
  LOGIN_EMAIL_STORAGE_KEY_LEGACY,
  brandAssets,
} from '../brand'
import { landingMailtoHref } from '../content/landing'
import {
  buildSessionHandoffUrl,
  clearRememberedAccount,
  isMarketingHost,
  loginAgainstClientInstance,
  marketingHomeHref,
  normalizeClientSlug,
  readRememberedAccount,
  writeRememberedAccount,
} from '../lib/marketingHost'
import { isCapacitorNative } from '../lib/capacitorNative'
import { isSaasControlPlaneFrontend, SAAS_LICENCAS_PATH } from '../lib/saasControlPlane'

const fieldClass =
  'w-full rounded-xl border border-white/10 bg-white/[0.06] px-3.5 py-3 text-base text-slate-100 placeholder:text-slate-500 shadow-inner shadow-black/20 backdrop-blur-sm transition-colors focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/25'

const secondaryLinkClass =
  'inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/15 bg-white/[0.06] px-4 py-2.5 text-sm font-medium transition hover:border-sky-400/40 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/40'

/** «Voltar ao site» — LP na apex; em tenant aponta para a apex absoluta (#677). */
function VoltarAoSiteLink({ className }: { className: string }) {
  const dest = marketingHomeHref()
  if (dest.mode === 'spa') {
    return (
      <Link to={dest.to} className={className}>
        ← Voltar ao site
      </Link>
    )
  }
  return (
    <a href={dest.href} className={className}>
      ← Voltar ao site
    </a>
  )
}

function readRememberedEmail(): string {
  try {
    return localStorage.getItem(LOGIN_EMAIL_STORAGE_KEY) ?? localStorage.getItem(LOGIN_EMAIL_STORAGE_KEY_LEGACY) ?? ''
  } catch {
    return ''
  }
}

/** Login local na apex (control-plane), em vez do handoff para subdomínio do cliente. */
function wantsOpsLogin(searchParams: URLSearchParams, pathname = ''): boolean {
  if (pathname === '/login/admin' || pathname.endsWith('/login/admin')) return true
  const ops = (searchParams.get('ops') || '').trim().toLowerCase()
  if (ops === '1' || ops === 'true' || ops === 'yes') return true
  const next = (searchParams.get('next') || '').trim()
  return next.startsWith('/saas')
}

/** Painel lateral estendido em tela cheia; escurece à direita para o formulário. */
function LoginBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-[#050810]">
      <img
        src={brandAssets.loginBackground}
        alt=""
        className="absolute inset-0 size-full object-cover object-left"
        decoding="async"
        fetchPriority="high"
      />
      <div className="absolute inset-0 bg-gradient-to-r from-[#050810]/30 via-[#050810]/55 to-[#050810]/90" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#050810]/25 via-transparent to-[#050810]/35" />
    </div>
  )
}

function LoginShell({ children, footer }: { children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <div
      className="relative min-h-dvh font-sans text-slate-100 antialiased"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <LoginBackground />
      <main className="relative flex min-h-dvh flex-col items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-[400px] space-y-8 sm:space-y-10">
          <header className="flex w-full justify-center">
            <BrandLogo
              variant="full"
              size="lg"
              markVariant="onDark"
              className="flex-col items-center gap-4 sm:flex-row sm:items-center sm:justify-center sm:gap-5"
            />
          </header>
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5 shadow-2xl shadow-black/40 backdrop-blur-md sm:p-6">
            {children}
          </div>
          {footer}
        </div>
      </main>
    </div>
  )
}

function PasswordToggle({
  mostrarSenha,
  onToggle,
}: {
  mostrarSenha: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute right-1.5 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-cyan-400/85 transition-colors hover:bg-white/5 hover:text-cyan-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/40"
      aria-label={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}
      aria-pressed={mostrarSenha}
    >
      {mostrarSenha ? (
        <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
        </svg>
      ) : (
        <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      )}
    </button>
  )
}

/** Apex comercial: conta + e-mail + senha → autentica na API do cliente e entra no painel. */
function LoginConta() {
  const [conta, setConta] = useState(readRememberedAccount)
  const [email, setEmail] = useState(readRememberedEmail)
  const [senha, setSenha] = useState('')
  const [lembrarMe, setLembrarMe] = useState(() => !!readRememberedEmail())
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [loading, setLoading] = useState(false)
  const { showError } = useToast()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const slug = normalizeClientSlug(conta)
    if (!slug) {
      showError('Informe a conta da empresa (ex.: suaempresa), só letras minúsculas, números e hífen.')
      return
    }
    if (!email.trim() || !senha.trim()) {
      showError('Informe e-mail e senha.')
      return
    }
    if (!email.includes('@')) {
      showError('Informe um e-mail válido.')
      return
    }

    setLoading(true)
    try {
      const tokens = await loginAgainstClientInstance(slug, email.trim(), senha)
      writeRememberedAccount(slug)
      try {
        if (lembrarMe) {
          localStorage.setItem(LOGIN_EMAIL_STORAGE_KEY, email.trim())
        } else {
          localStorage.removeItem(LOGIN_EMAIL_STORAGE_KEY)
          localStorage.removeItem(LOGIN_EMAIL_STORAGE_KEY_LEGACY)
        }
      } catch {
        /* storage indisponível */
      }
      window.location.assign(buildSessionHandoffUrl(slug, tokens, lembrarMe))
    } catch (err) {
      showError(mensagemFalhaParaToast(err, 'Falha no login. Verifique conta, e-mail e senha.'))
      setLoading(false)
    }
  }

  return (
    <LoginShell
      footer={
        <div className="space-y-4">
          <p className="text-center text-xs leading-relaxed text-slate-500">
            Após validar, você entra direto no painel da sua empresa.
          </p>
          <div className="flex flex-col gap-2.5 sm:flex-row sm:justify-center">
            <VoltarAoSiteLink className={`${secondaryLinkClass} text-sky-300 hover:text-sky-200 sm:w-auto`} />
            <a
              href={landingMailtoHref()}
              className={`${secondaryLinkClass} text-cyan-300 hover:text-cyan-200 sm:w-auto`}
            >
              Solicitar uma demonstração
            </a>
          </div>
          {isSaasControlPlaneFrontend() ? (
            <p className="text-center text-xs text-slate-500">
              Equipa DeskRudder?{' '}
              <Link to="/login/admin" className="font-medium text-sky-300 hover:text-sky-200">
                Acesso ao painel admin
              </Link>
            </p>
          ) : null}
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <label htmlFor="login-conta" className="mb-1.5 block text-sm font-medium text-slate-300">
            Conta da empresa
          </label>
          <input
            id="login-conta"
            type="text"
            value={conta}
            onChange={(e) => setConta(e.target.value.toLowerCase())}
            autoComplete="organization"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            placeholder="ex.: suaempresa"
            className={fieldClass}
          />
          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            Sem espaços. Em geral é o nome curto da empresa (o mesmo do subdomínio).
          </p>
        </div>

        <div>
          <label htmlFor="login-email-apex" className="mb-1.5 block text-sm font-medium text-slate-300">
            E-mail
          </label>
          <input
            id="login-email-apex"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            placeholder="nome@empresa.com"
            className={fieldClass}
          />
        </div>

        <div>
          <label htmlFor="login-senha-apex" className="mb-1.5 block text-sm font-medium text-slate-300">
            Senha
          </label>
          <div className="relative">
            <input
              id="login-senha-apex"
              type={mostrarSenha ? 'text' : 'password'}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              className={`${fieldClass} pr-12`}
            />
            <PasswordToggle mostrarSenha={mostrarSenha} onToggle={() => setMostrarSenha((v) => !v)} />
          </div>
        </div>

        <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={lembrarMe}
            onChange={(e) => setLembrarMe(e.target.checked)}
            className="mt-0.5 size-4 shrink-0 rounded border-white/20 bg-white/[0.06] text-cyan-500 accent-cyan-500 focus:ring-2 focus:ring-cyan-400/30"
          />
          <span>Lembrar-me neste dispositivo</span>
        </label>

        <Button
          type="submit"
          className="w-full rounded-xl py-3 text-base font-semibold shadow-lg shadow-cyan-500/25 focus-visible:ring-offset-[#050810] disabled:opacity-60"
          loading={loading}
        >
          Entrar
        </Button>
      </form>
    </LoginShell>
  )
}

/** App Capacitor: conta (slug) persiste no aparelho e os pedidos vão para `api-{slug}` (#736). */
function LoginCapacitor() {
  const remembered = readRememberedAccount()
  const [conta, setConta] = useState(remembered)
  const [trocarEmpresa, setTrocarEmpresa] = useState(!remembered)
  const [email, setEmail] = useState(readRememberedEmail)
  const [senha, setSenha] = useState('')
  const [lembrarMe, setLembrarMe] = useState(() => !!readRememberedEmail())
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const { showError, showSuccess } = useToast()
  const navigate = useNavigate()

  function pedirOutraEmpresa() {
    clearRememberedAccount()
    clearAuthToken()
    setConta('')
    setTrocarEmpresa(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const slug = normalizeClientSlug(conta)
    if (!slug) {
      showError('Informe a conta da empresa (ex.: duplexsoft), só letras minúsculas, números e hífen.')
      return
    }
    if (!email.trim() || !senha.trim()) {
      showError('Informe e-mail e senha.')
      return
    }
    if (!email.includes('@')) {
      showError('Informe um e-mail válido.')
      return
    }

    setLoading(true)
    const slugAnterior = readRememberedAccount()
    // Precisa do slug no storage para apiBaseUrl() apontar à instância; só fica se o login OK.
    writeRememberedAccount(slug)
    try {
      await login(email.trim(), senha, lembrarMe)
      try {
        if (lembrarMe) {
          localStorage.setItem(LOGIN_EMAIL_STORAGE_KEY, email.trim())
        } else {
          localStorage.removeItem(LOGIN_EMAIL_STORAGE_KEY)
          localStorage.removeItem(LOGIN_EMAIL_STORAGE_KEY_LEGACY)
        }
      } catch {
        /* storage indisponível */
      }
      showSuccess('Login realizado com sucesso.')
      navigate('/chat/atendendo', { replace: true })
    } catch (err) {
      if (slugAnterior) writeRememberedAccount(slugAnterior)
      else clearRememberedAccount()
      showError(mensagemFalhaParaToast(err, 'Falha no login. Verifique conta, e-mail e senha.'))
    } finally {
      setLoading(false)
    }
  }

  const mostrarCampoConta = trocarEmpresa || !remembered

  return (
    <LoginShell
      footer={
        <p className="text-center text-xs leading-relaxed text-slate-500">
          Use o usuário cadastrado pelo administrador desta empresa.
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {mostrarCampoConta ? (
          <div>
            <label htmlFor="login-conta-nativo" className="mb-1.5 block text-sm font-medium text-slate-300">
              Conta da empresa
            </label>
            <input
              id="login-conta-nativo"
              type="text"
              value={conta}
              onChange={(e) => setConta(e.target.value.toLowerCase())}
              autoComplete="organization"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder="ex.: duplexsoft"
              className={fieldClass}
            />
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              O mesmo identificador do endereço do painel (ex.: duplexsoft.deskrudder.com.br).
            </p>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-3">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Empresa</p>
              <p className="truncate font-medium text-slate-100">{remembered}</p>
            </div>
            <button
              type="button"
              onClick={pedirOutraEmpresa}
              className="shrink-0 text-sm font-medium text-cyan-300 hover:text-cyan-200"
            >
              Trocar
            </button>
          </div>
        )}

        <div>
          <label htmlFor="login-email-nativo" className="mb-1.5 block text-sm font-medium text-slate-300">
            E-mail
          </label>
          <input
            id="login-email-nativo"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            placeholder="nome@empresa.com"
            className={fieldClass}
          />
        </div>

        <div>
          <label htmlFor="login-senha-nativo" className="mb-1.5 block text-sm font-medium text-slate-300">
            Senha
          </label>
          <div className="relative">
            <input
              id="login-senha-nativo"
              type={mostrarSenha ? 'text' : 'password'}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              className={`${fieldClass} pr-12`}
            />
            <PasswordToggle mostrarSenha={mostrarSenha} onToggle={() => setMostrarSenha((v) => !v)} />
          </div>
        </div>

        <div className="text-right">
          <Link to="/esqueci-senha" className="text-sm text-cyan-400/90 transition-colors hover:text-cyan-300">
            Esqueci minha senha
          </Link>
        </div>

        <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={lembrarMe}
            onChange={(e) => setLembrarMe(e.target.checked)}
            className="mt-0.5 size-4 shrink-0 rounded border-white/20 bg-white/[0.06] text-cyan-500 accent-cyan-500 focus:ring-2 focus:ring-cyan-400/30"
          />
          <span>Lembrar-me neste dispositivo</span>
        </label>

        <Button
          type="submit"
          className="w-full rounded-xl py-3 text-base font-semibold shadow-lg shadow-cyan-500/25 focus-visible:ring-offset-[#050810] disabled:opacity-60"
          loading={loading}
        >
          Entrar
        </Button>
      </form>
    </LoginShell>
  )
}

/** Credenciais locais: subdomínio do cliente, ou painel admin SaaS na apex (`/login/admin`). */
function LoginCredenciais({ variant = 'tenant' }: { variant?: 'tenant' | 'ops' }) {
  const isOps = variant === 'ops'
  const [email, setEmail] = useState(readRememberedEmail)
  const [senha, setSenha] = useState('')
  const [lembrarMe, setLembrarMe] = useState(() => !!readRememberedEmail())
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [loading, setLoading] = useState(false)
  const { login, logout } = useAuth()
  const { showError, showSuccess } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  function destinoAposLogin(role: string): string {
    if (role === 'saas_ops') return SAAS_LICENCAS_PATH
    const next = (searchParams.get('next') || '').trim()
    if (next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/saas')) return next
    const from = (location.state as { from?: { pathname?: string; search?: string } } | null)?.from
    if (
      from?.pathname &&
      from.pathname !== '/login' &&
      !from.pathname.startsWith('/login/') &&
      !from.pathname.startsWith('/saas')
    ) {
      return `${from.pathname}${from.search || ''}`
    }
    return '/'
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim() || !senha.trim()) {
      showError('Informe e-mail e senha.')
      return
    }
    if (!email.includes('@')) {
      showError('Informe um e-mail válido.')
      return
    }
    setLoading(true)
    try {
      await login(email.trim(), senha, lembrarMe)
      const { atendentes } = await import('../api/client')
      const me = await atendentes.me()
      if (isOps && me.role !== 'saas_ops') {
        logout()
        showError('Esta conta não é da equipa SaaS. Use o login do atendimento (/login).')
        return
      }
      if (!isOps && me.role === 'saas_ops') {
        showSuccess('Login ops realizado. Abrindo o painel SaaS…')
        navigate(SAAS_LICENCAS_PATH, { replace: true })
        return
      }
      try {
        if (lembrarMe) {
          localStorage.setItem(LOGIN_EMAIL_STORAGE_KEY, email.trim())
        } else {
          localStorage.removeItem(LOGIN_EMAIL_STORAGE_KEY)
          localStorage.removeItem(LOGIN_EMAIL_STORAGE_KEY_LEGACY)
        }
      } catch {
        /* storage indisponível */
      }
      showSuccess('Login realizado com sucesso. Redirecionando...')
      navigate(destinoAposLogin(me.role), { replace: true })
    } catch (err) {
      showError(mensagemFalhaParaToast(err, 'Falha no login. Verifique suas credenciais e tente novamente.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <LoginShell
      footer={
        <>
          <p className="text-center text-xs leading-relaxed text-slate-500">
            {isOps
              ? 'Acesso da equipa DeskRudder — gestão de licenças, leads e instâncias SaaS.'
              : 'Use o usuário cadastrado pelo administrador. Problemas para acessar? Contate o suporte interno.'}
          </p>
          <div className="flex flex-col gap-2.5">
            {isOps ? (
              <p className="text-center">
                <Link to="/login" className={`${secondaryLinkClass} text-cyan-300 hover:text-cyan-200`}>
                  Já sou cliente — entrar na conta da empresa
                </Link>
              </p>
            ) : null}
            <p className="text-center">
              <VoltarAoSiteLink className={`${secondaryLinkClass} text-sky-300 hover:text-sky-200`} />
            </p>
          </div>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {isOps ? (
          <div className="space-y-1.5 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-300/90">Painel admin</p>
            <h1 className="text-xl font-semibold text-white sm:text-2xl">Gestão SaaS DeskRudder</h1>
            <p className="text-sm text-slate-400">
              Conta da equipa comercial (role saas_ops). Em local: ops@deskrudder.local
            </p>
          </div>
        ) : null}
        <div>
          <label htmlFor="login-email" className="mb-1.5 block text-sm font-medium text-slate-300">
            E-mail
          </label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            placeholder="nome@empresa.com"
            className={fieldClass}
          />
        </div>

        <div>
          <label htmlFor="login-senha" className="mb-1.5 block text-sm font-medium text-slate-300">
            Senha
          </label>
          <div className="relative">
            <input
              id="login-senha"
              type={mostrarSenha ? 'text' : 'password'}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              className={`${fieldClass} pr-12`}
            />
            <PasswordToggle mostrarSenha={mostrarSenha} onToggle={() => setMostrarSenha((v) => !v)} />
          </div>
        </div>

        <div className="text-right">
          <Link to="/esqueci-senha" className="text-sm text-cyan-400/90 transition-colors hover:text-cyan-300">
            Esqueci minha senha
          </Link>
        </div>

        <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={lembrarMe}
            onChange={(e) => setLembrarMe(e.target.checked)}
            className="mt-0.5 size-4 shrink-0 rounded border-white/20 bg-white/[0.06] text-cyan-500 accent-cyan-500 focus:ring-2 focus:ring-cyan-400/30"
          />
          <span>Lembrar-me neste dispositivo</span>
        </label>

        <Button
          type="submit"
          className="w-full rounded-xl py-3 text-base font-semibold shadow-lg shadow-cyan-500/25 focus-visible:ring-offset-[#050810] disabled:opacity-60"
          loading={loading}
        >
          Entrar
        </Button>
      </form>
    </LoginShell>
  )
}

export function Login() {
  const [searchParams] = useSearchParams()
  const { pathname } = useLocation()
  if (isCapacitorNative()) {
    return <LoginCapacitor />
  }
  // Apex: conta da empresa. Admin SaaS: `/login/admin`, `?ops=1` ou `?next=/saas…`.
  if (wantsOpsLogin(searchParams, pathname)) {
    return <LoginCredenciais variant="ops" />
  }
  if (isMarketingHost()) {
    return <LoginConta />
  }
  return <LoginCredenciais variant="tenant" />
}
