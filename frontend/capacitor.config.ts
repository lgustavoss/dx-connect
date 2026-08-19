import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'br.com.deskrudder.app',
  appName: 'DeskRudder',
  webDir: 'dist',
  android: {
    allowMixedContent: true,
  },
  server: {
    androidScheme: 'https',
  },
  plugins: {
    // Pedidos nativos (OkHttp) — o WebView em https://localhost não sofre CORS da API do cliente.
    CapacitorHttp: {
      enabled: true,
    },
  },
}

export default config
