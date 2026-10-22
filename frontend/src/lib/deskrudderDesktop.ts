/** Ponte com o app Electron (preload `deskrudderDesktop`). Ausente no navegador. */

export type RemotoStatus = {
  instalado: boolean
  caminho?: string | null
}

export type RemotoConectarResultado = {
  ok: boolean
  modo?: string
  erro?: string
}

type DeskRudderDesktopBridge = {
  remotoStatus: () => Promise<RemotoStatus>
  conectarRemoto: (
    id: string,
    senha?: string | null,
    tituloSessao?: string | null,
  ) => Promise<RemotoConectarResultado>
  recarregarPainel: () => Promise<{ ok: boolean }>
}

declare global {
  interface Window {
    deskrudderDesktop?: DeskRudderDesktopBridge
  }
}

export function isDeskRudderDesktop(): boolean {
  return typeof window !== 'undefined' && Boolean(window.deskrudderDesktop)
}

export async function conectarRemotoPreferindoDesktop(
  id: string,
  senha?: string | null,
  tituloSessao?: string | null,
): Promise<RemotoConectarResultado | null> {
  if (!window.deskrudderDesktop) return null
  return window.deskrudderDesktop.conectarRemoto(id, senha, tituloSessao)
}
