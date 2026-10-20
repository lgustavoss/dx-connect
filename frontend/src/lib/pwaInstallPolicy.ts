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

/**
 * No desktop: remove o manifest e engole `beforeinstallprompt` para o Chrome/Edge
 * não sugerirem «Instale o app». No mobile não faz nada.
 */
export function suppressDesktopPwaInstallPrompt(): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  if (isMobileForPwaInstall()) return

  const removeManifest = () => {
    document.querySelectorAll('link[rel="manifest"]').forEach((el) => el.remove())
  }
  removeManifest()
  // VitePWA pode reinjetar o link depois do boot — manter o observer pela vida da página.
  const obs = new MutationObserver(removeManifest)
  obs.observe(document.documentElement, { childList: true, subtree: true })

  const onPrompt = (e: Event) => {
    e.preventDefault()
  }
  window.addEventListener('beforeinstallprompt', onPrompt)
}
