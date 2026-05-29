import { useState } from 'react'
import { Link } from 'react-router-dom'
import { auth } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'

const fieldClass =
  'w-full rounded-xl border border-white/10 bg-white/[0.06] px-3.5 py-3 text-[0.9375rem] text-slate-100 placeholder:text-slate-500 shadow-inner shadow-black/20 backdrop-blur-sm transition-colors focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/25'

export function EsqueciSenha() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [enviado, setEnviado] = useState(false)
  const { showError, showSuccess } = useToast()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = email.trim()
    if (!trimmed || !trimmed.includes('@')) {
      showError('Informe um e-mail válido.')
      return
    }
    setLoading(true)
    try {
      const res = await auth.solicitarRedefinicaoSenha(trimmed)
      setEnviado(true)
      showSuccess(res.detail)
    } catch (err) {
      showError(mensagemFalhaParaToast(err, 'Não foi possível processar o pedido. Tente novamente.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col justify-center bg-[#050810] px-4 py-10 font-[family-name:'Plus_Jakarta_Sans',system-ui,sans-serif] text-slate-100 antialiased">
      <div className="mx-auto w-full max-w-[400px] space-y-6">
        <header className="text-center">
          <h1 className="text-2xl font-semibold text-white">Esqueci minha senha</h1>
          <p className="mt-2 text-sm text-slate-400">
            Informe o e-mail da sua conta. Se estiver cadastrado, enviaremos um link para redefinir a senha.
          </p>
        </header>

        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5 shadow-2xl shadow-black/40 backdrop-blur-md sm:p-6">
          {enviado ? (
            <p className="text-center text-sm leading-relaxed text-slate-300">
              Verifique sua caixa de entrada (e o spam). O link expira em pouco tempo por segurança.
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <div>
                <label htmlFor="reset-email" className="mb-1.5 block text-sm font-medium text-slate-300">
                  E-mail
                </label>
                <input
                  id="reset-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="nome@empresa.com"
                  className={fieldClass}
                />
              </div>
              <Button
                type="submit"
                className="w-full rounded-xl py-3 text-base font-semibold shadow-lg shadow-cyan-500/25 disabled:opacity-60"
                loading={loading}
              >
                Enviar link
              </Button>
            </form>
          )}
        </div>

        <p className="text-center text-sm">
          <Link to="/login" className="text-cyan-400/90 hover:text-cyan-300">
            Voltar ao login
          </Link>
        </p>
      </div>
    </div>
  )
}
