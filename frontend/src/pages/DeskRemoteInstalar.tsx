import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { DESKREMOTE_FLUTTER_CLIENTE_INSTALLER_URL } from '../lib/rustdeskInstaller'

/** Página pública do QR: o técnico cola o mesmo endereço no DeskRemote do PDV. */
export function DeskRemoteInstalar() {
  const { token } = useParams()
  const [copia, setCopia] = useState<'ok' | 'erro' | null>(null)
  const url = useMemo(() => {
    if (typeof window === 'undefined') return ''
    return window.location.href.split('#')[0]
  }, [])

  async function copiar() {
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      setCopia('ok')
    } catch {
      setCopia('erro')
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-4 py-10 dark:bg-slate-950">
      <div className="w-full max-w-lg space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Instalar o DeskRemote</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Este link configura o computador no painel. Abra o DeskRemote neste PC e cole o endereço. Não compartilhe o
          link — ele vale uma vez.
        </p>
        {token ? (
          <p className="break-all rounded-lg bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-950 dark:text-slate-300">
            {url}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void copiar()}
            className="rounded-lg bg-cyan-700 px-3 py-2 text-sm font-medium text-white hover:bg-cyan-800"
          >
            Copiar link
          </button>
          <a
            href={DESKREMOTE_FLUTTER_CLIENTE_INSTALLER_URL}
            className="rounded-lg px-3 py-2 text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-300"
          >
            Baixar o DeskRemote
          </a>
        </div>
        {copia === 'ok' ? (
          <p className="text-xs text-emerald-700 dark:text-emerald-300">Link copiado.</p>
        ) : null}
        {copia === 'erro' ? (
          <p className="text-xs text-amber-800 dark:text-amber-200">
            Não foi possível copiar. Selecione o link acima e copie na mão.
          </p>
        ) : null}
        <p className="text-xs text-slate-500">
          Já tem o aplicativo? Cole o link na tela de instalação. <Link to="/login">Entrar no painel</Link>
        </p>
      </div>
    </div>
  )
}
