import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { clearAuthToken } from '../api/client'
import { PageLoading } from '../components/ui/PageLoading'
import { isMarketingHost } from '../lib/marketingHost'

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'

/**
 * Recebe tokens no hash após login na apex comercial e grava a sessão no subdomínio do cliente.
 * O fragmento não é enviado ao servidor; limpamos da URL logo após ler.
 */
export function AuthSessao() {
  const navigate = useNavigate()
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (isMarketingHost()) {
      navigate('/login', { replace: true })
      return
    }

    const raw = window.location.hash.replace(/^#/, '')
    if (!raw) {
      setErro('Sessão inválida ou expirada. Faça login novamente.')
      return
    }

    const params = new URLSearchParams(raw)
    const access = params.get('access_token')
    const refresh = params.get('refresh_token')
    const lembrar = params.get('lembrar') !== '0'

    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)

    if (!access) {
      setErro('Sessão inválida ou expirada. Faça login novamente.')
      return
    }

    clearAuthToken()
    const store = lembrar ? localStorage : sessionStorage
    store.setItem(TOKEN_KEY, access)
    if (refresh) store.setItem(REFRESH_TOKEN_KEY, refresh)

    // Full reload para o AuthProvider ler os tokens no boot.
    window.location.replace('/')
  }, [navigate])

  if (erro) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-[#050810] px-4 text-center text-slate-200">
        <p className="max-w-sm text-sm text-slate-400">{erro}</p>
        <a href="/login" className="text-sm font-medium text-cyan-400 hover:text-cyan-300">
          Ir para o login
        </a>
      </div>
    )
  }

  return <PageLoading fullscreen label="Entrando no painel…" />
}
