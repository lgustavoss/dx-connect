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
  salvarSessao?: (
    accessToken: string,
    refreshToken?: string | null,
  ) => Promise<{ ok: boolean }>
  limparSessao?: () => Promise<{ ok: boolean }>
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

/** Grava a sessão do painel para o atalho do DeskRemote herdar o login. */
export function salvarSessaoDeskRemote(
  accessToken: string | null | undefined,
  refreshToken?: string | null,
): void {
  const bridge = typeof window !== 'undefined' ? window.deskrudderDesktop : undefined
  if (!bridge?.salvarSessao) return
  const access = (accessToken || '').trim()
  if (!access) {
    void bridge.limparSessao?.()
    return
  }
  void bridge.salvarSessao(access, refreshToken ?? null)
}

export function limparSessaoDeskRemote(): void {
  const bridge = typeof window !== 'undefined' ? window.deskrudderDesktop : undefined
  if (!bridge?.limparSessao) return
  void bridge.limparSessao()
}
