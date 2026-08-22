import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { bindCapacitorBackButton } from './lib/capacitorNative'

bindCapacitorBackButton()

const root = createRoot(document.getElementById('root')!)

async function boot() {
  // APK e browser usam o mesmo App (paridade mobile web). Capacitor só muda
  // Conta/slug, HTTP nativo, push e chrome (safe-area) via isCapacitorNative().
  const { default: App } = await import('./App.tsx')
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void boot()
