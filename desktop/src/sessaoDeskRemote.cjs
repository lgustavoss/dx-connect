const APEX = 'deskrudder.com.br'
const SLUG_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/
const SLUGS_RESERVADOS = new Set([
  'www',
  'api',
  'mail',
  'ftp',
  'cdn',
  'static',
  'app',
  'admin',
  'status',
  'portal',
])

function slugValido(slug) {
  const s = String(slug || '').trim().toLowerCase()
  return Boolean(s) && SLUG_RE.test(s) && !SLUGS_RESERVADOS.has(s)
}

/**
 * Slug da origem do painel (`https://{slug}.deskrudder.com.br`).
 * Se a URL não for do painel, usa o fallback (conta gravada no Electron).
 */
/** Painel da instância: `https://{slug}.deskrudder.com.br` (não file:, apex nem host reservado). */
function origemPainelHttpsInstancia(url) {
  try {
    const { protocol, hostname } = new URL(url)
    if (protocol !== 'https:') return false
    if (!hostname.endsWith(`.${APEX}`)) return false
    const slug = hostname.slice(0, -(APEX.length + 1)).toLowerCase()
    return slugValido(slug)
  } catch {
    return false
  }
}

function slugDaOrigemPainel(url, fallbackSlug) {
  try {
    const { hostname } = new URL(url)
    if (hostname.endsWith(`.${APEX}`)) {
      const slug = hostname.slice(0, -(APEX.length + 1)).toLowerCase()
      if (slugValido(slug)) return slug
    }
  } catch {
    /* ignore */
  }
  return slugValido(fallbackSlug) ? String(fallbackSlug).trim().toLowerCase() : null
}

function montarCorpoSessao(slug, accessToken, refreshToken) {
  const access = String(accessToken || '').trim()
  const s = String(slug || '').trim().toLowerCase()
  if (!access || !slugValido(s)) return null
  if (access.length > 16000) return null
  const refresh = String(refreshToken || '').trim()
  return {
    slug: s,
    access_token: access,
    ...(refresh ? { refresh_token: refresh } : {}),
  }
}

module.exports = {
  APEX,
  slugValido,
  origemPainelHttpsInstancia,
  slugDaOrigemPainel,
  montarCorpoSessao,
}
