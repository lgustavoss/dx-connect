import { useEffect } from 'react'
import { DESKTOP_WINDOWS_INSTALLER_URL } from '../lib/desktopInstaller'

/** Rota pública: sem login. Preferir redirect no Nginx; isto é o fallback do SPA. */
export function DesktopDownload() {
  useEffect(() => {
    window.location.replace(DESKTOP_WINDOWS_INSTALLER_URL)
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <p className="text-sm text-slate-600 dark:text-slate-300">Baixando o DeskRudder para Windows…</p>
    </div>
  )
}
