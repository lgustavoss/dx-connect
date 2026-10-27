/** URL pública do instalador Windows DeskRudder (Release estável no GitHub). */
export const RUSTDESK_WINDOWS_INSTALLER_URL = (
  (import.meta.env.VITE_RUSTDESK_INSTALLER_URL as string | undefined)?.trim() ||
  'https://github.com/lgustavoss/dx-connect/releases/download/acesso-remoto-windows/DeskRudder-AcessoRemoto.exe'
).replace(/\s+/g, '')

/** Spike Flutter do cliente (não substitui o Sciter em `acesso-remoto-windows`). */
export const DESKREMOTE_FLUTTER_CLIENTE_INSTALLER_URL = (
  (import.meta.env.VITE_DESKREMOTE_FLUTTER_CLIENTE_URL as string | undefined)?.trim() ||
  'https://github.com/lgustavoss/dx-connect/releases/download/acesso-remoto-windows-flutter/DeskRudder-AcessoRemoto-Flutter.exe'
).replace(/\s+/g, '')

/** Caminho no domínio da instância — sem login; Nginx (ou o SPA) redireciona ao .exe. */
export const RUSTDESK_WINDOWS_INSTALLER_PATH = '/acesso-remoto/download'

/** Link curto para colar no navegador do posto (ex.: https://cliente.deskrudder.com.br/acesso-remoto/download). */
export function urlDownloadInstaladorNaInstancia(): string {
  if (typeof window === 'undefined' || !window.location?.origin) {
    return RUSTDESK_WINDOWS_INSTALLER_PATH
  }
  return `${window.location.origin}${RUSTDESK_WINDOWS_INSTALLER_PATH}`
}

/**
 * Dispara o download sem navegar o SPA (evita a tela «Baixando o instalador…»).
 * O link curto `/acesso-remoto/download` continua para enviar ao posto.
 */
export function iniciarDownloadInstaladorWindows(): void {
  const a = document.createElement('a')
  a.href = RUSTDESK_WINDOWS_INSTALLER_URL
  a.rel = 'noopener'
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  a.remove()
}
