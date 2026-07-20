import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { PortalAuthProvider, usePortalAuth } from '../../contexts/PortalAuthContext'
import { usePortalBranding } from '../../contexts/PortalBrandingContext'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'
import { PortalBrandLogo } from './PortalBrandLogo'
import { portalInputClass, portalPrimaryBtnClass } from './portalUi'
import { PageLoading } from '../../components/ui/PageLoading'

const iconEye = (
  <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden>
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
    />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const iconEyeOff = (
  <svg className="size-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden>
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
    />
  </svg>
)

function PortalLoginForm() {
  const { user, loading, login } = usePortalAuth()
  const branding = usePortalBranding()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [lembrarMe, setLembrarMe] = useState(true)
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const { showError, showSuccess } = useToast()
  const navigate = useNavigate()
  const [params] = useSearchParams()

  if (loading) {
    return <PageLoading fullscreen label="Carregando…" />
  }
  if (user) {
    const dest = user.must_change_password ? '/portal/trocar-senha' : '/portal/tickets'
    return <Navigate to={dest} replace />
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim() || !senha.trim()) {
      showError('Informe e-mail e senha.')
      return
    }
    setSubmitting(true)
    try {
      await login(email.trim(), senha, lembrarMe)
      showSuccess('Bem-vindo ao portal.')
      const returnTo = params.get('returnTo')
      navigate(returnTo && returnTo.startsWith('/portal') ? returnTo : '/portal/tickets', {
        replace: true,
      })
    } catch (err) {
      showError(mensagemFalhaParaToast(err, 'Falha no login. Verifique suas credenciais.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-4 py-12">
      {/* Fundo minimalista: grade suave + manchas de marca */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundColor: branding.cor_fundo || '#F8FAFC',
          backgroundImage: [
            `radial-gradient(ellipse 80% 55% at 50% -10%, color-mix(in srgb, ${branding.cor_header} 22%, transparent), transparent 55%)`,
            `radial-gradient(ellipse 50% 40% at 100% 100%, color-mix(in srgb, ${branding.cor_primaria} 14%, transparent), transparent 50%)`,
            `radial-gradient(ellipse 40% 35% at 0% 85%, color-mix(in srgb, ${branding.cor_header} 8%, transparent), transparent 45%)`,
          ].join(', '),
        }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgb(15 23 42 / 0.04) 1px, transparent 1px), linear-gradient(to bottom, rgb(15 23 42 / 0.04) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse 70% 60% at 50% 40%, black 20%, transparent 75%)',
        }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-1"
        style={{ backgroundColor: branding.cor_header }}
        aria-hidden
      />

      <div className="relative w-full max-w-md animate-[fadeIn_0.45s_ease-out]">
        <div className="mb-9 text-center">
          <div className="mx-auto mb-6 flex w-full items-center justify-center">
            <PortalBrandLogo className="mx-auto h-auto w-full max-h-24 object-contain object-center sm:max-h-28" />
          </div>
          <h1
            className="text-2xl font-semibold tracking-tight sm:text-[1.65rem]"
            style={{ color: branding.cor_texto_corpo }}
          >
            {branding.portal_titulo}
          </h1>
          <p className="mx-auto mt-2.5 max-w-sm text-sm leading-relaxed text-slate-500">
            {branding.texto_boas_vindas}
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200/70 bg-white/90 p-6 shadow-[0_20px_50px_-24px_rgb(15_23_42_/0.25)] backdrop-blur-md sm:p-7"
        >
          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">E-mail</span>
            <input
              type="email"
              autoComplete="username"
              className={portalInputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              required
            />
          </label>
          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">Senha</span>
            <div className="relative">
              <input
                type={mostrarSenha ? 'text' : 'password'}
                autoComplete="current-password"
                className={`${portalInputClass} pr-12`}
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
              />
              <button
                type="button"
                className="absolute right-1.5 top-1/2 flex size-9 -translate-y-1/2 items-center justify-center rounded-lg transition-colors hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--portal-primary)]/30"
                style={{ color: branding.cor_link }}
                onClick={() => setMostrarSenha((v) => !v)}
                aria-label={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}
                aria-pressed={mostrarSenha}
              >
                {mostrarSenha ? iconEyeOff : iconEye}
              </button>
            </div>
          </label>
          <label className="mb-6 flex items-center gap-2.5 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={lembrarMe}
              onChange={(e) => setLembrarMe(e.target.checked)}
              className="size-4 rounded border-slate-300 focus:ring-[var(--portal-primary)]"
              style={{ accentColor: branding.cor_primaria }}
            />
            Manter conectado neste aparelho
          </label>
          <button
            type="submit"
            className={`${portalPrimaryBtnClass} w-full py-2.5`}
            style={{ backgroundColor: 'var(--portal-primary)' }}
            disabled={submitting}
          >
            {submitting ? 'Entrando…' : 'Entrar'}
          </button>
        </form>

        <p className="mt-7 text-center text-xs text-slate-500">
          É da equipe de suporte?{' '}
          <Link
            to="/login"
            className="font-medium underline-offset-2 hover:underline"
            style={{ color: branding.cor_link }}
          >
            Acessar painel interno
          </Link>
        </p>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}

export function PortalLogin() {
  return (
    <PortalAuthProvider>
      <PortalLoginForm />
    </PortalAuthProvider>
  )
}
