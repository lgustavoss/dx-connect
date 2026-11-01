import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { bindCapacitorBackButton } from './lib/capacitorNative'

bindCapacitorBackButton()

/** PWA descontinuada: tira service workers antigos (install + Web Push no browser). */
function unregisterLegacyPwa(): void {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return
  void navigator.serviceWorker.getRegistrations().then((regs) => {
    for (const reg of regs) void reg.unregister()
  })
}
unregisterLegacyPwa()

const root = createRoot(document.getElementById('root')!)

async function boot() {
  // APK e browser usam o mesmo App (paridade mobile web). Capacitor só muda
  // Conta/slug, HTTP nativo, push e chrome (safe-area) via isCapacitorNative().
  // No desktop o Setup Electron é o caminho oficial — sem prompt «Instale o app».
  const { default: App } = await import('./App.tsx')
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void boot()
