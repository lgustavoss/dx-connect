/**
 * Build do SPA Capacitor (mesmo App do browser) + `cap sync android` (#735 / #736).
 *
 * Produção (um APK, várias empresas): não precisa de VITE_API_URL — o login pede a
 * conta (slug) e grava `https://api-{slug}.deskrudder.com.br`.
 *
 * Debug contra Docker no PC:
 *   $env:VITE_API_URL = "http://10.0.2.2:8000"   # emulador
 *   $env:VITE_API_URL = "http://192.168.x.x:8000" # telemóvel na Wi-Fi
 */
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** Placeholder do job frontend na CI — nunca embutir no APK. */
const CI_PLACEHOLDER = /ci\.invalid\.example/i

let api = (process.env.VITE_API_URL || '').trim()
if (api && CI_PLACEHOLDER.test(api)) {
  console.warn(
    `Ignorando VITE_API_URL=${api} (placeholder da CI). O APK usará a conta (slug) no login.`,
  )
  delete process.env.VITE_API_URL
  api = ''
}
if (api) {
  console.log(`VITE_API_URL=${api} (debug: esta URL prevalece sobre o slug)`)
} else {
  console.log('Sem VITE_API_URL: o APK usa a conta (slug) informada no login.')
}

process.env.VITE_CAPACITOR = 'true'

function run(cmd, args) {
  const r = spawnSync(cmd, args, { cwd: frontendRoot, stdio: 'inherit', env: process.env, shell: true })
  if (r.status !== 0) process.exit(r.status ?? 1)
}

run('npx', ['vite', 'build'])
run('npx', ['cap', 'sync', 'android'])
console.log('OK: frontend/android sincronizado. Abra o Android Studio: npm run cap:open')
