import { useEffect } from 'react'
import { RUSTDESK_WINDOWS_INSTALLER_URL } from '../lib/rustdeskInstaller'

/** Rota pública: sem login. Preferir redirect no Nginx; isto é o fallback do SPA. */
export function AcessoRemotoDownload() {
  useEffect(() => {
    window.location.replace(RUSTDESK_WINDOWS_INSTALLER_URL)
  }, [])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 px-4 dark:bg-slate-950">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Baixando o instalador do DeskRudder Acesso Remoto…
      </p>
      <a
        href={RUSTDESK_WINDOWS_INSTALLER_URL}
        className="text-sm font-medium text-cyan-600 underline-offset-2 hover:underline dark:text-cyan-400"
      >
        Se o download não começar, clique aqui
      </a>
    </div>
  )
}
