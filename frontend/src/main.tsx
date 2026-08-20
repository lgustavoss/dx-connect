import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { bindCapacitorBackButton } from './lib/capacitorNative'

bindCapacitorBackButton()

const root = createRoot(document.getElementById('root')!)

async function boot() {
  const { default: App } = __DX_CONNECT_CAPACITOR__
    ? await import('./AppNative.tsx')
    : await import('./App.tsx')
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void boot()
