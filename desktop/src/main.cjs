const { app, BrowserWindow, Tray, Menu, nativeImage, dialog, shell, ipcMain, net } = require('electron')
const path = require('node:path')
const fs = require('node:fs')

const APP_ID = 'br.com.deskrudder.desktop'
const APEX = 'deskrudder.com.br'
const ARG_OCULTO = '--oculto'
const SLUG_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/
const SLUGS_RESERVADOS = new Set(['www', 'api', 'mail', 'ftp', 'cdn', 'static', 'app', 'admin', 'status', 'portal'])
const ICONE = path.join(__dirname, '..', 'build', 'icon.png')
const CONTA_HTML = path.join(__dirname, 'conta.html')

// Alerta da fila (alerta.mp3 em loop) precisa tocar com a janela escondida na bandeja.
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required')
app.setAppUserModelId(APP_ID)

if (!app.requestSingleInstanceLock()) {
  app.quit()
}

/** @type {BrowserWindow | null} */
let janela = null
/** @type {Tray | null} */
let bandeja = null
let saindo = false
let ultimaContagem = 0

// ── Configuração persistida (userData/config.json) ──────────────────────────

function caminhoConfig() {
  return path.join(app.getPath('userData'), 'config.json')
}

/** @returns {{ slug?: string, autostartPerguntado?: boolean, avisoBandejaMostrado?: boolean }} */
function lerConfig() {
  try {
    return JSON.parse(fs.readFileSync(caminhoConfig(), 'utf8'))
  } catch {
    return {}
  }
}

function salvarConfig(parcial) {
  const atual = lerConfig()
  fs.mkdirSync(path.dirname(caminhoConfig()), { recursive: true })
  fs.writeFileSync(caminhoConfig(), JSON.stringify({ ...atual, ...parcial }, null, 2))
}

// ── Conta (slug) ────────────────────────────────────────────────────────────

function normalizarSlug(raw) {
  const slug = String(raw || '').trim().toLowerCase()
  if (!slug || !SLUG_RE.test(slug) || SLUGS_RESERVADOS.has(slug)) return null
  return slug
}

function urlPainel(slug) {
  return `https://${slug}.${APEX}/`
}

function hostDaInstancia(url) {
  try {
    const { protocol, hostname } = new URL(url)
    if (protocol !== 'https:') return false
    return hostname === APEX || hostname.endsWith(`.${APEX}`)
  } catch {
    return false
  }
}

async function contaExiste(slug) {
  try {
    const res = await net.fetch(`https://api-${slug}.${APEX}/health`, { method: 'GET' })
    return res.ok
  } catch {
    return null
  }
}

function abrirPainelOuConta() {
  if (!janela) return
  const { slug } = lerConfig()
  if (slug) {
    void janela.loadURL(urlPainel(slug))
  } else {
    void janela.loadFile(CONTA_HTML)
  }
}

ipcMain.handle('conta:definir', async (event, raw) => {
  if (!event.senderFrame?.url.startsWith('file:')) return { ok: false, erro: 'Origem não permitida.' }
  const slug = normalizarSlug(raw)
  if (!slug) return { ok: false, erro: 'Conta inválida. Use o identificador do endereço do painel (ex.: minhaempresa).' }
  const existe = await contaExiste(slug)
  if (existe === null) return { ok: false, erro: 'Sem conexão com a internet. Verifique a rede e tente de novo.' }
  if (!existe) return { ok: false, erro: 'Conta não encontrada. Confira o identificador com o administrador.' }
  salvarConfig({ slug })
  if (janela) void janela.loadURL(urlPainel(slug))
  return { ok: true }
})

ipcMain.handle('conta:atual', (event) => {
  if (!event.senderFrame?.url.startsWith('file:')) return null
  return lerConfig().slug ?? null
})

// ── Janela ──────────────────────────────────────────────────────────────────

function mostrarJanela() {
  if (!janela) return
  if (janela.isMinimized()) janela.restore()
  janela.show()
  janela.focus()
}

function avisarQueContinuaNaBandeja() {
  if (!bandeja || lerConfig().avisoBandejaMostrado) return
  bandeja.displayBalloon({
    iconType: 'info',
    title: 'O DeskRudder continua aberto',
    content: 'Os alertas da fila seguem funcionando. Para sair, clique com o botão direito no ícone da bandeja.',
  })
  salvarConfig({ avisoBandejaMostrado: true })
}

function atualizarContagem(titulo) {
  const m = /^\((\d+)\)\s/.exec(titulo || '')
  const n = m ? Number(m[1]) : 0
  if (bandeja) {
    bandeja.setToolTip(n > 0 ? `DeskRudder — ${n} ${n === 1 ? 'pendência' : 'pendências'}` : 'DeskRudder')
  }
  if (janela && n > ultimaContagem && !janela.isFocused()) {
    janela.flashFrame(true)
  }
  ultimaContagem = n
}

function criarJanela(iniciarOculto) {
  janela = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 420,
    minHeight: 560,
    show: false,
    title: 'DeskRudder',
    icon: ICONE,
    backgroundColor: '#0b1220',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      // Timers e SSE não podem ser estrangulados com a janela escondida.
      backgroundThrottling: false,
      spellcheck: true,
    },
  })
  janela.removeMenu()

  janela.once('ready-to-show', () => {
    if (!iniciarOculto) janela?.show()
  })

  janela.on('close', (e) => {
    if (saindo) return
    e.preventDefault()
    janela?.hide()
    avisarQueContinuaNaBandeja()
  })

  janela.on('focus', () => janela?.flashFrame(false))
  janela.on('page-title-updated', (_e, titulo) => atualizarContagem(titulo))

  const wc = janela.webContents
  wc.setWindowOpenHandler(({ url }) => {
    if (hostDaInstancia(url)) return { action: 'allow' }
    if (/^(https?|mailto|tel):/i.test(url)) void shell.openExternal(url)
    return { action: 'deny' }
  })
  wc.on('will-navigate', (e, url) => {
    if (url.startsWith('file:') || hostDaInstancia(url)) return
    e.preventDefault()
    if (/^(https?|mailto|tel):/i.test(url)) void shell.openExternal(url)
  })
  wc.on('did-fail-load', (_e, codigo, _desc, url, principal) => {
    // -3 = navegação abortada (redirect/SPA); não é falha de rede.
    if (!principal || codigo === -3 || url.startsWith('file:')) return
    void janela?.loadFile(CONTA_HTML, { query: { erro: 'conexao' } })
  })
  wc.on('context-menu', (_e, params) => {
    const temImagem = params.mediaType === 'image' && params.hasImageContents
    const temTexto = params.selectionText.trim().length > 0
    if (!temImagem && !temTexto) return
    Menu.buildFromTemplate([
      {
        label: 'Copiar',
        click: () => (temImagem ? wc.copyImageAt(params.x, params.y) : wc.copy()),
      },
    ]).popup({ window: janela })
  })
  wc.on('before-input-event', (_e, input) => {
    if (input.type !== 'keyDown') return
    if (input.key === 'F5' || (input.control && input.key.toLowerCase() === 'r')) wc.reload()
    if (!app.isPackaged && input.key === 'F12') wc.toggleDevTools()
  })

  abrirPainelOuConta()
}

// ── Bandeja e iniciar com o Windows ─────────────────────────────────────────

function autostartAtivo() {
  return app.getLoginItemSettings({ args: [ARG_OCULTO] }).openAtLogin
}

function definirAutostart(ativo) {
  if (!app.isPackaged) return
  app.setLoginItemSettings({ openAtLogin: ativo, args: [ARG_OCULTO] })
}

function montarMenuBandeja() {
  if (!bandeja) return
  bandeja.setContextMenu(
    Menu.buildFromTemplate([
      { label: 'Abrir DeskRudder', click: mostrarJanela },
      { type: 'separator' },
      {
        label: 'Iniciar com o Windows',
        type: 'checkbox',
        checked: autostartAtivo(),
        enabled: app.isPackaged,
        click: (item) => {
          definirAutostart(item.checked)
          salvarConfig({ autostartPerguntado: true })
          montarMenuBandeja()
        },
      },
      { label: 'Trocar empresa…', click: () => void trocarEmpresa() },
      { type: 'separator' },
      {
        label: 'Sair',
        click: () => {
          saindo = true
          app.quit()
        },
      },
    ]),
  )
}

function criarBandeja() {
  const img = nativeImage.createFromPath(ICONE).resize({ width: 32, height: 32 })
  bandeja = new Tray(img)
  bandeja.setToolTip('DeskRudder')
  bandeja.on('click', mostrarJanela)
  bandeja.on('double-click', mostrarJanela)
  montarMenuBandeja()
}

async function trocarEmpresa() {
  mostrarJanela()
  const { response } = await dialog.showMessageBox(janela, {
    type: 'question',
    buttons: ['Trocar empresa', 'Cancelar'],
    defaultId: 0,
    cancelId: 1,
    title: 'DeskRudder',
    message: 'Trocar a empresa conectada?',
    detail: 'Você volta para a tela de conta e precisa entrar de novo.',
  })
  if (response !== 0) return
  salvarConfig({ slug: undefined })
  abrirPainelOuConta()
}

async function perguntarAutostartSeNecessario() {
  if (!app.isPackaged || lerConfig().autostartPerguntado || !janela) return
  const { response } = await dialog.showMessageBox(janela, {
    type: 'question',
    buttons: ['Sim', 'Agora não'],
    defaultId: 0,
    cancelId: 1,
    title: 'DeskRudder',
    message: 'Abrir o DeskRudder ao iniciar o computador?',
    detail: 'Assim você recebe os alertas da fila sem precisar abrir o app. Dá para mudar depois no ícone da bandeja.',
  })
  definirAutostart(response === 0)
  salvarConfig({ autostartPerguntado: true })
  montarMenuBandeja()
}

// ── Ciclo de vida ───────────────────────────────────────────────────────────

app.on('second-instance', mostrarJanela)
app.on('before-quit', () => {
  saindo = true
})
app.on('window-all-closed', () => {
  if (saindo) app.quit()
})

app.whenReady().then(() => {
  const iniciarOculto = process.argv.includes(ARG_OCULTO)
  criarBandeja()
  criarJanela(iniciarOculto)
  if (!iniciarOculto) {
    janela?.webContents.once('did-finish-load', () => void perguntarAutostartSeNecessario())
  }
})
