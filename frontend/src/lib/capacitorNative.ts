import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'

/** WebView nativo (Capacitor). O host é `localhost` — não é a landing comercial. */
export function isCapacitorNative(): boolean {
  return Capacitor.isNativePlatform()
}

/** Botão voltar do Android no WebView (#735). No browser não faz nada. */
export function bindCapacitorBackButton(): void {
  if (!Capacitor.isNativePlatform()) return
  void App.addListener('backButton', ({ canGoBack }) => {
    if (canGoBack || window.history.length > 1) {
      window.history.back()
      return
    }
    void App.exitApp()
  })
}
