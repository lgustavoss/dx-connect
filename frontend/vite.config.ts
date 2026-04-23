import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  if (mode === 'production' && !env.VITE_API_URL?.trim()) {
    throw new Error(
      'Build de produção exige VITE_API_URL. Crie frontend/.env.production (veja frontend/.env.example).',
    )
  }

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      // Evita falha de resolução/pré-bundle do pacote (exports condicionais) em alguns ambientes Windows/Vite.
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
