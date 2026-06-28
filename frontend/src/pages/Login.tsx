import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { BrandLogo, LOGIN_EMAIL_STORAGE_KEY, LOGIN_EMAIL_STORAGE_KEY_LEGACY, brandAssets } from '../brand'

const fieldClass =
  'w-full rounded-xl border border-white/10 bg-white/[0.06] px-3.5 py-3 text-[0.9375rem] text-slate-100 placeholder:text-slate-500 shadow-inner shadow-black/20 backdrop-blur-sm transition-colors focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/25'

function readRememberedEmail(): string {
  try {
    return localStorage.getItem(LOGIN_EMAIL_STORAGE_KEY) ?? localStorage.getItem(LOGIN_EMAIL_STORAGE_KEY_LEGACY) ?? ''
  } catch {
    return ''
  }
}

/** Decoração leve estilo “plexus” para mobile (sem imagem pesada). */
function LoginMeshBg() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden lg:hidden"
    >
      <div className="absolute -left-1/4 top-0 h-[min(70vh,480px)] w-[min(120vw,600px)] rounded-full bg-cyan-500/[0.12] blur-[80px]" />
      <div className="absolute -right-1/4 bottom-0 h-[min(50vh,360px)] w-[min(100vw,480px)] rounded-full bg-blue-600/[0.10] blur-[72px]" />
      <svg className="absolute left-0 top-12 h-64 w-full opacity-[0.2]" viewBox="0 0 400 200" fill="none">
        <path
          d="M0 120 L80 60 L160 100 L240 40 L320 90 L400 50"
          stroke="url(#login-line)"
          strokeWidth="1"
        />
        <path
          d="M40 180 L120 130 L200 160 L280 110 L360 150"
          stroke="url(#login-line)"
          strokeWidth="1"
          opacity="0.6"
        />
        {[
          [80, 60],
          [160, 100],
          [240, 40],
          [320, 90],
          [120, 130],
          [200, 160],
        ].map(([cx, cy], i) => (
          <circle key={i} cx={cx} cy={cy} r="2.5" fill="#22d3ee" fillOpacity="0.7" />
        ))}
        <defs>
          <linearGradient id="login-line" x1="0" y1="0" x2="400" y2="0">
            <stop stopColor="#22d3ee" stopOpacity="0.5" />
            <stop offset="1" stopColor="#3b82f6" stopOpacity="0.3" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  )
}

export function Login() {
  const [email, setEmail] = useState(readRememberedEmail)
  const [senha, setSenha] = useState('')
  const [lembrarMe, setLembrarMe] = useState(() => !!readRememberedEmail())
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const { showError, showSuccess } = useToast()
  const navigate = useNavigate()

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
      navigate('/', { replace: true })
    } catch (err) {
      showError(mensagemFalhaParaToast(err, 'Falha no login. Verifique suas credenciais e tente novamente.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="relative flex min-h-dvh flex-col bg-[#050810] font-sans text-slate-100 antialiased lg:flex-row"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <LoginMeshBg />

      <aside
        className="relative hidden min-h-0 shrink-0 overflow-hidden lg:flex lg:w-[min(44vw,540px)] xl:w-[min(38vw,520px)]"
        aria-hidden
      >
        <img
          src={brandAssets.loginPlexusPanel}
          alt=""
          className="absolute inset-0 size-full object-cover object-left"
          decoding="async"
          fetchPriority="low"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#050810]/20 to-[#050810]" />
      </aside>

      <main className="relative flex flex-1 flex-col justify-center px-4 py-10 sm:px-8 lg:px-12 xl:px-16">
        <div className="mx-auto w-full max-w-[400px] space-y-8 sm:space-y-10">
          <header className="w-full">
            <BrandLogo
              variant="full"
              size="lg"
              markVariant="onDark"
              className="w-full flex-col items-center gap-4 sm:flex-row sm:items-center sm:justify-start sm:gap-5 lg:gap-6"
            />
          </header>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5 shadow-2xl shadow-black/40 backdrop-blur-md sm:p-6">
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
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
                  <button
                    type="button"
                    onClick={() => setMostrarSenha((v) => !v)}
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
                </div>
              </div>

              <div className="text-right">
                <Link
                  to="/esqueci-senha"
                  className="text-sm text-cyan-400/90 transition-colors hover:text-cyan-300"
                >
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
          </div>

          <p className="text-center text-xs leading-relaxed text-slate-500 lg:text-left">
            Use o usuário cadastrado pelo administrador. Problemas para acessar? Contate o suporte interno.
          </p>
        </div>
      </main>
    </div>
  )
}
