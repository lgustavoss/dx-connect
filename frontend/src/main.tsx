import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { bindCapacitorBackButton } from './lib/capacitorNative'
import { suppressDesktopPwaInstallPrompt } from './lib/pwaInstallPolicy'

bindCapacitorBackButton()
suppressDesktopPwaInstallPrompt()

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
