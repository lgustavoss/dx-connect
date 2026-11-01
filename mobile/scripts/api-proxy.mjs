/**
 * Proxy só para `expo start --web`. O browser bloqueia CORS contra
 * api-{slug}.deskrudder.com.br; o celular (Expo Go) não usa isto.
 */
import http from 'node:http'
import https from 'node:https'
import { URL } from 'node:url'

const PORT = Number(process.env.MOBILE_API_PROXY_PORT || 8788)
const APEX = 'deskrudder.com.br'
const SLUG_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/

function targetOrigin(rawSlug) {
  const slug = String(rawSlug || 'duplexsoft')
    .trim()
    .toLowerCase()
  if (slug === 'local') return 'http://127.0.0.1:8000'
  if (!SLUG_RE.test(slug)) return null
  return `https://api-${slug}.${APEX}`
}

function applyCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD')
  res.setHeader('Access-Control-Allow-Headers', 'Authorization,Content-Type,Accept,X-Instance-Slug')
  res.setHeader('Access-Control-Allow-Private-Network', 'true')
  res.setHeader('Access-Control-Max-Age', '600')
}

const server = http.createServer((req, res) => {
  applyCors(res)
  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }

  const origin = targetOrigin(req.headers['x-instance-slug'])
  if (!origin) {
    res.writeHead(400, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ detail: 'Instância inválida' }))
    return
  }

  const dest = new URL(req.url || '/', origin)
  const lib = dest.protocol === 'https:' ? https : http
  const headers = { ...req.headers, host: dest.host }
  delete headers['x-instance-slug']
  delete headers.origin
  delete headers.referer

  const up = lib.request(
    dest,
    { method: req.method, headers },
    (incoming) => {
      const outHeaders = { ...incoming.headers }
      delete outHeaders['access-control-allow-origin']
      delete outHeaders['access-control-allow-credentials']
      applyCors(res)
      res.writeHead(incoming.statusCode || 502, outHeaders)
      incoming.pipe(res)
    },
  )
  up.on('error', (err) => {
    applyCors(res)
    res.writeHead(502, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ detail: `Não foi possível conectar à instância (${err.message}).` }))
  })
  req.pipe(up)
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Proxy API http://127.0.0.1:${PORT} → https://api-{slug}.${APEX}`)
})
