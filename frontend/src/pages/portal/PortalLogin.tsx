import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { PortalAuthProvider, usePortalAuth } from '../../contexts/PortalAuthContext'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { BrandLogo } from '../../brand'
import { PageLoading } from '../../components/ui/PageLoading'

const fieldClass =
  'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-[0.9375rem] text-slate-900 placeholder:text-slate-400 shadow-sm transition-colors focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/25'

function PortalLoginForm() {
  const { user, loading, login } = usePortalAuth()
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
    <div className="relative flex min-h-dvh flex-col items-center justify-center bg-gradient-to-br from-slate-100 via-white to-teal-50 px-4 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 20%, rgba(13,148,136,0.12), transparent 40%), radial-gradient(circle at 80% 80%, rgba(15,23,42,0.06), transparent 45%)',
        }}
      />
      <div className="relative w-full max-w-md">
        <div className="mb-8 text-center">
          <BrandLogo className="mx-auto h-10 w-auto" />
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-slate-900">
            Portal do cliente
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            Acompanhe e abra chamados da sua empresa com a equipe de suporte.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200/80 bg-white/95 p-6 shadow-lg shadow-slate-200/60 backdrop-blur"
        >
          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">E-mail</span>
            <input
              type="email"
              autoComplete="username"
              className={fieldClass}
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
                className={`${fieldClass} pr-16`}
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
              />
              <button
                type="button"
                className="absolute inset-y-0 right-2 my-auto h-8 rounded-md px-2 text-xs font-medium text-teal-700 hover:bg-teal-50"
                onClick={() => setMostrarSenha((v) => !v)}
              >
                {mostrarSenha ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>
          </label>
          <label className="mb-5 flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={lembrarMe}
              onChange={(e) => setLembrarMe(e.target.checked)}
              className="size-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
            />
            Manter conectado neste aparelho
          </label>
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? 'Entrando…' : 'Entrar'}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-500">
          É da equipe de suporte?{' '}
          <Link to="/login" className="font-medium text-teal-700 underline-offset-2 hover:underline">
            Acessar painel interno
          </Link>
        </p>
      </div>
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
