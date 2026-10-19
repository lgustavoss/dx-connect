/** URL pública do instalador Windows DeskRudder (Release estável no GitHub). */
export const RUSTDESK_WINDOWS_INSTALLER_URL = (
  (import.meta.env.VITE_RUSTDESK_INSTALLER_URL as string | undefined)?.trim() ||
  'https://github.com/lgustavoss/dx-connect/releases/download/acesso-remoto-windows/DeskRudder-AcessoRemoto.exe'
).replace(/\s+/g, '')
