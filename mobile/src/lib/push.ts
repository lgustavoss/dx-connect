/** Stub web: o Metro do Expo 58 não resolve expo-notifications no browser. */

export function instalarHandlerNotificacao(): void {}

export function escutarAberturaNotificacao(): () => void {
  return () => undefined
}

export async function registrarDispositivo(): Promise<void> {}

export async function revogarDispositivo(): Promise<void> {}
