import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { auth } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { IconEye, IconEyeOff } from '../components/ui/IconEye'

const fieldClass =
  'w-full rounded-xl border border-white/10 bg-white/[0.06] px-3.5 py-3 text-[0.9375rem] text-slate-100 placeholder:text-slate-500 shadow-inner shadow-black/20 backdrop-blur-sm transition-colors focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/25'

export function RedefinirSenha() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')?.trim() ?? ''
  const [senhaNova, setSenhaNova] = useState('')
  const [senhaConf, setSenhaConf] = useState('')
  const [mostrarNova, setMostrarNova] = useState(false)
  const [mostrarConf, setMostrarConf] = useState(false)
  const [loading, setLoading] = useState(false)
  const { showError, showSuccess } = useToast()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!token) {
      showError('Link inválido. Solicite uma nova redefinição de senha.')
      return
    }
    if (senhaNova.length < 8) {
      showError('A nova senha deve ter pelo menos 8 caracteres.')
      return
    }
    if (senhaNova !== senhaConf) {
      showError('A confirmação não coincide com a nova senha.')
      return
    }
    setLoading(true)
    try {
      const res = await auth.redefinirSenha(token, senhaNova)
      showSuccess(res.detail)
      navigate('/login', { replace: true })
    } catch (err) {
      showError(mensagemFalhaParaToast(err, 'Não foi possível redefinir a senha.'))
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="flex h-dvh max-h-dvh flex-col items-center justify-center overflow-y-auto bg-[#050810] px-4 text-center text-slate-100">
        <p className="mb-4 text-sm text-slate-400">Link inválido ou incompleto.</p>
        <Link to="/esqueci-senha" className="text-cyan-400/90 hover:text-cyan-300">
          Solicitar novo link
        </Link>
      </div>
    )
  }

  return (
    <div className="relative flex h-dvh max-h-dvh min-h-0 flex-col overflow-y-auto bg-[#050810] px-4 py-10 font-[family-name:'Plus_Jakarta_Sans',system-ui,sans-serif] text-slate-100 antialiased">
      <div className="mx-auto w-full max-w-[400px] space-y-6">
        <header className="text-center">
          <h1 className="text-2xl font-semibold text-white">Nova senha</h1>
          <p className="mt-2 text-sm text-slate-400">Defina uma senha forte com pelo menos 8 caracteres.</p>
        </header>

        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5 shadow-2xl shadow-black/40 backdrop-blur-md sm:p-6">
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="pwd-nova" className="mb-1.5 block text-sm font-medium text-slate-300">
                Nova senha
              </label>
              <div className="relative">
                <input
                  id="pwd-nova"
                  type={mostrarNova ? 'text' : 'password'}
                  value={senhaNova}
                  onChange={(e) => setSenhaNova(e.target.value)}
                  autoComplete="new-password"
                  className={`${fieldClass} pr-12`}
                  minLength={8}
                  required
                />
                <button
                  type="button"
                  onClick={() => setMostrarNova((v) => !v)}
                  className="absolute right-1.5 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-cyan-400/85 hover:bg-white/5"
                  aria-label={mostrarNova ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {mostrarNova ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
                </button>
              </div>
            </div>
            <div>
              <label htmlFor="pwd-conf" className="mb-1.5 block text-sm font-medium text-slate-300">
                Confirmar senha
              </label>
              <div className="relative">
                <input
                  id="pwd-conf"
                  type={mostrarConf ? 'text' : 'password'}
                  value={senhaConf}
                  onChange={(e) => setSenhaConf(e.target.value)}
                  autoComplete="new-password"
                  className={`${fieldClass} pr-12`}
                  minLength={8}
                  required
                />
                <button
                  type="button"
                  onClick={() => setMostrarConf((v) => !v)}
                  className="absolute right-1.5 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-cyan-400/85 hover:bg-white/5"
                  aria-label={mostrarConf ? 'Ocultar confirmação' : 'Mostrar confirmação'}
                >
                  {mostrarConf ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
                </button>
              </div>
            </div>
            <Button
              type="submit"
              className="w-full rounded-xl py-3 text-base font-semibold shadow-lg shadow-cyan-500/25 disabled:opacity-60"
              loading={loading}
            >
              Salvar senha
            </Button>
          </form>
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
