/** Canal de update do app Windows (Release GitHub `desktop-windows`). */
const REPO = 'lgustavoss/dx-connect'
const TAG = 'desktop-windows'
const SETUP_NAME = 'DeskRudder-Setup.exe'
const APEX = 'deskrudder.com.br'

function urlVersionJson() {
  return `https://github.com/${REPO}/releases/download/${TAG}/version.json`
}

function urlSetupGithub() {
  return `https://github.com/${REPO}/releases/download/${TAG}/${SETUP_NAME}`
}

/**
 * Compara versões semver simples (1.1.4 vs 1.1.3).
 * @returns {number} >0 se a > b
 */
function compararVersao(a, b) {
  const pa = String(a || '')
    .trim()
    .split(/[^\d]+/)
    .filter(Boolean)
    .map((n) => parseInt(n, 10) || 0)
  const pb = String(b || '')
    .trim()
    .split(/[^\d]+/)
    .filter(Boolean)
    .map((n) => parseInt(n, 10) || 0)
  const n = Math.max(pa.length, pb.length)
  for (let i = 0; i < n; i++) {
    const da = pa[i] || 0
    const db = pb[i] || 0
    if (da > db) return 1
    if (da < db) return -1
  }
  return 0
}

function downloadUrlPermitida(url) {
  if (!url || typeof url !== 'string') return false
  try {
    const u = new URL(url)
    if (u.protocol !== 'https:') return false
    if (u.hostname === APEX || u.hostname.endsWith(`.${APEX}`)) {
      return u.pathname === '/app/download'
    }
    if (u.hostname === 'github.com') {
      return u.pathname === `/${REPO}/releases/download/${TAG}/${SETUP_NAME}`
    }
    return false
  } catch {
    return false
  }
}

/**
 * @param {unknown} data
 * @returns {{ version: string, download_url: string } | null}
 */
function parseVersionJson(data) {
  if (!data || typeof data !== 'object') return null
  const version = String(/** @type {{ version?: unknown }} */ (data).version || '').trim()
  if (!/^\d+\.\d+(\.\d+)?$/.test(version)) return null
  const raw = /** @type {{ download_url?: unknown }} */ (data).download_url
  const download_url =
    typeof raw === 'string' && downloadUrlPermitida(raw) ? raw : urlSetupGithub()
  return { version, download_url }
}

module.exports = {
  APEX,
  SETUP_NAME,
  compararVersao,
  downloadUrlPermitida,
  parseVersionJson,
  urlSetupGithub,
  urlVersionJson,
}
