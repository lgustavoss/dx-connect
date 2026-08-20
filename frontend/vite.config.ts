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
    define: {
      __DX_CONNECT_CAPACITOR__: capacitorNative,
    },
    plugins: [
      react(),
      tailwindcss(),
      VitePWA({
        disable: capacitorNative,
        strategies: 'injectManifest',
        srcDir: 'src',
        filename: 'sw.ts',
        registerType: 'autoUpdate',
        injectRegister: 'auto',
        includeAssets: [
          'favicon.ico',
          'deskrudder-pwa-180.png',
          'deskrudder-pwa-192.png',
          'deskrudder-pwa-512.png',
          'deskrudder-pwa-192-outline.png',
          'deskrudder-pwa-512-outline.png',
        ],
        manifest: {
          name: 'DeskRudder',
          short_name: 'DeskRudder',
          description: 'Atendimento no telemóvel — chats WhatsApp e tickets, no endereço da sua instância.',
          lang: 'pt-BR',
          start_url: '/',
          scope: '/',
          display: 'standalone',
          background_color: '#F8FAFC',
          theme_color: '#f8fafc',
          icons: [
            {
              src: '/deskrudder-pwa-192-outline.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/deskrudder-pwa-512-outline.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            { src: '/deskrudder-pwa-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
            { src: '/deskrudder-pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
          ],
        },
        injectManifest: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2,webmanifest}'],
        },
        devOptions: { enabled: true, type: 'module' },
      }),
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
