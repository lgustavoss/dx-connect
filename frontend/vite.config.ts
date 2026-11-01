import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // APK Capacitor: o SW da PWA no WebView nativo compete com o runtime (#735).
  const capacitorNative = process.env.VITE_CAPACITOR === 'true'
  if (capacitorNative) {
    process.env.VITE_CAPACITOR = 'true'
  }

  if (mode === 'production' && !capacitorNative && !env.VITE_API_URL?.trim()) {
    throw new Error(
      'Build de produção exige VITE_API_URL. Crie frontend/.env.production (veja frontend/.env.example).',
    )
  }

  return {
    plugins: [
      react(),
      tailwindcss(),
      // PWA descontinuada (#1311): o caminho mobile é o companion Expo, não instalar o painel.
      // O plugin fica desligado; `unregisterLegacyPwa` em main.tsx limpa SWs antigos.
      VitePWA({ disable: true }),
    ],
    resolve: {
      // react e react-dom devem ser a mesma versão exata (erro React #527 se divergirem).
      dedupe: ['react', 'react-dom'],
      alias: {
        'qrcode.react': path.resolve(__dirname, 'node_modules/qrcode.react/lib/esm/index.js'),
      },
    },
    optimizeDeps: {
      include: ['qrcode.react'],
    },
    server: {
      port: 5173,
      host: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
