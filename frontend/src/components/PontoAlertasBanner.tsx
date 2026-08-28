import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ponto } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

/** Banner de lembretes de ponto (#773 / #769 / #968) — sem batida automática. */
export function PontoAlertasBanner() {
  const { user } = useAuth()
  const [mensagens, setMensagens] = useState<string[]>([])
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (!user || user.must_change_password || user.role === 'saas_ops') return
    let cancelled = false

    const carregar = () => {
      void ponto
        .alertas()
        .then((a) => {
          if (cancelled) return
          setMensagens(a.mensagens ?? [])
          if ((a.mensagens ?? []).length === 0) setDismissed(false)
        })
        .catch(() => {
          /* silencioso — não bloquear o painel */
        })
    }

    carregar()
    const id = window.setInterval(carregar, 60_000)
    const onVis = () => {
      if (document.visibilityState === 'visible') carregar()
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      cancelled = true
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [user])

  if (dismissed || mensagens.length === 0) return null

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
      <div className="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-2">
        <div className="space-y-0.5">
          {mensagens.map((m) => (
            <p key={m}>{m}</p>
          ))}
          <Link to="/ponto" className="font-medium underline underline-offset-2">
            Ir para Meu ponto
          </Link>
        </div>
        <button
          type="button"
          className="shrink-0 rounded px-2 py-1 text-xs hover:bg-amber-100 dark:hover:bg-amber-900/50"
          onClick={() => setDismissed(true)}
        >
          Dispensar
        </button>
      </div>
    </div>
  )
}
