/** URL pública do Setup Windows DeskRudder (Release estável no GitHub). */
export const DESKTOP_WINDOWS_INSTALLER_URL = (
  (import.meta.env.VITE_DESKTOP_INSTALLER_URL as string | undefined)?.trim() ||
  'https://github.com/lgustavoss/dx-connect/releases/download/desktop-windows/DeskRudder-Setup.exe'
).replace(/\s+/g, '')

/** Caminho no domínio da instância — sem login; Nginx (ou o SPA) redireciona ao .exe. */
export const DESKTOP_WINDOWS_INSTALLER_PATH = '/app/download'

/** Link curto para o atendente (ex.: https://cliente.deskrudder.com.br/app/download). */
export function urlDownloadAppNaInstancia(): string {
  if (typeof window === 'undefined' || !window.location?.origin) {
    return DESKTOP_WINDOWS_INSTALLER_PATH
  }
  return `${window.location.origin}${DESKTOP_WINDOWS_INSTALLER_PATH}`
}

/** Dispara o download do Setup sem navegar o SPA (sem tela intermediária). */
export function iniciarDownloadAppWindows(): void {
  const a = document.createElement('a')
  a.href = DESKTOP_WINDOWS_INSTALLER_URL
  a.rel = 'noopener'
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  a.remove()
}
