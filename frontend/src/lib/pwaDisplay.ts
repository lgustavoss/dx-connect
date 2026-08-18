/** Detecção de PWA / iOS Safari (#691 / #695). */

export function isStandaloneDisplay(): boolean {
  if (typeof window === 'undefined') return false
  if (window.matchMedia('(display-mode: standalone)').matches) return true
  const nav = window.navigator as Navigator & { standalone?: boolean }
  return nav.standalone === true
}

export function isIosSafari(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  const iOS =
    /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  if (!iOS) return false
  return /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua)
}

/** No iPhone/iPad, Web Push só funciona na PWA do ecrã inicial (Safari 16.4+). */
export function webPushRequerPwaIos(): boolean {
  return isIosSafari() && !isStandaloneDisplay()
}
