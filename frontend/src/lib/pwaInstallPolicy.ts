/** Política de instalação PWA: no PC o caminho oficial é o Setup Electron; no celular mantém PWA. */

import { isIosSafari } from './pwaDisplay'

/** Dispositivo em que o convite / critério de instalação PWA continua ativo. */
export function isMobileForPwaInstall(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  if (/Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)) return true
  // iPadOS 13+ reporta-se como MacIntel com touch.
  if (/iPad/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
    return true
  }
  return isIosSafari()
}
