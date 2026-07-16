/**
 * Popula dados fictícios via API e captura prints da landing.
 * Uso: node scripts/capture-landing-shots.mjs
 */
import { chromium } from 'playwright'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.join(__dirname, '../public/marketing')
const api = process.env.LANDING_API_BASE || 'http://localhost:8000/v1'
const app = process.env.LANDING_SHOT_BASE || 'http://localhost:5173'
const headersBase = { 'Content-Type': 'application/json', 'X-Dx-Tenant-Id': '1' }

async function apiJson(method, route, token, body) {
  const headers = { ...headersBase }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${api}${route}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { raw: text }
  }
  if (!res.ok) {
    throw new Error(`${method} ${route} → ${res.status} ${JSON.stringify(data)}`)
  }
  return data
}

async function ensureDemoData(token) {
  let empresas = await apiJson('GET', '/empresas?limit=5', token)
  let setores = await apiJson('GET', '/setores?limit=5', token)
  const statuses = await apiJson('GET', '/status-ticket?limit=20', token)
  const statusAberto =
    statuses.items?.find((s) => s.slug === 'aguardando_atendimento')?.id ||
    statuses.items?.[0]?.id

  if (!empresas.items?.length) {
    const rede = await apiJson('POST', '/redes', token, {
      nome: 'Rede Demo Landing',
      ativo: true,
    })
    await apiJson('POST', '/empresas', token, {
      nome: 'Posto Centro Demo',
      rede_id: rede.id,
      cnpj_cpf: '12345678000199',
      ativo: true,
    })
    empresas = await apiJson('GET', '/empresas?limit=5', token)
  }

  if (!setores.items?.length) {
    await apiJson('POST', '/setores', token, {
      nome: 'Suporte',
      slug: 'suporte-demo-landing',
      ativo: true,
    })
    setores = await apiJson('GET', '/setores?limit=5', token)
  }

  const empresaId = empresas.items?.[0]?.id
  const setorId = setores.items?.[0]?.id
  if (!empresaId || !setorId || !statusAberto) {
    console.warn('seed incompleto', { empresaId, setorId, statusAberto })
    return
  }

  const tickets = await apiJson('GET', '/tickets?limit=10', token)
  if ((tickets.items?.length || 0) >= 3) {
    console.log('tickets ok:', tickets.items.length)
    return
  }

  for (const [assunto, prioridade] of [
    ['PDV sem comunicação com a retaguarda', 'alta'],
    ['Erro ao emitir cupom fiscal', 'urgente'],
    ['Solicitar acesso remoto ao caixa 02', 'normal'],
  ]) {
    try {
      await apiJson('POST', '/tickets', token, {
        empresa_id: empresaId,
        setor_id: setorId,
        status_id: statusAberto,
        assunto,
        descricao: 'Demanda fictícia para demonstração da landing DeskRudder.',
        prioridade,
      })
      console.log('ticket:', assunto)
    } catch (err) {
      console.warn('falha ticket', String(err.message || err))
    }
  }
}

async function launchBrowser() {
  for (const channel of ['chrome', 'msedge']) {
    try {
      const browser = await chromium.launch({ channel, headless: true })
      console.log('using channel', channel)
      return browser
    } catch {
      /* next */
    }
  }
  return chromium.launch({ headless: true })
}

async function main() {
  await mkdir(outDir, { recursive: true })
  const login = await apiJson('POST', '/auth/login', null, {
    email: 'admin@email.com',
    senha: 'admin123',
  })
  const token = login.access_token
  if (!token) throw new Error('login sem access_token')
  await ensureDemoData(token)

  const browser = await launchBrowser()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  async function shot(name) {
    await page.waitForTimeout(1500)
    const file = path.join(outDir, `shot-${name}.png`)
    await page.screenshot({ path: file, fullPage: false })
    console.log('saved', file)
  }

  await page.goto(`${app}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await shot('login')
  await page.locator('input[type="email"], input[autocomplete="username"]').first().fill('admin@email.com')
  await page.locator('input[type="password"]').fill('admin123')
  await page.locator('button[type="submit"]').click()
  await page.waitForTimeout(4000)
  await shot('dashboard')

  for (const [name, route] of [
    ['tickets', '/tickets'],
    ['chat', '/chat/atendendo'],
    ['kb', '/ajuda/consultar'],
    ['sla', '/dashboard/tickets'],
  ]) {
    await page.goto(`${app}${route}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await shot(name)
  }

  await browser.close()
  await writeFile(
    path.join(outDir, 'README.txt'),
    'Prints do ambiente local com dados fictícios (seed/demo). Regenerar: node scripts/capture-landing-shots.mjs\n',
    'utf8',
  )
  console.log('OK')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
