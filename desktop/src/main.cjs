const { app, BrowserWindow, Tray, Menu, nativeImage, dialog, shell, ipcMain, net, session } = require('electron')
const path = require('node:path')
const fs = require('node:fs')
const { spawn } = require('node:child_process')
const {
  SETUP_NAME,
  compararVersao,
  downloadUrlPermitida,
  parseVersionJson,
  urlSetupGithub,
  urlVersionJson,
} = require('./versao.cjs')
const {
  slugDaOrigemPainel,
  montarCorpoSessao,
  origemPainelHttpsInstancia,
} = require('./sessaoDeskRemote.cjs')
const { itensMenuContexto, idiomasCorretor } = require('./menuContexto.cjs')

const APP_ID = 'br.com.deskrudder.desktop'
const APEX = 'deskrudder.com.br'
const ARG_OCULTO = '--oculto'
const SLUG_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/
const SLUGS_RESERVADOS = new Set(['www', 'api', 'mail', 'ftp', 'cdn', 'static', 'app', 'admin', 'status', 'portal'])
const ICONE_PNG = path.join(__dirname, '..', 'build', 'icon.png')
const CONTA_HTML = path.join(__dirname, 'conta.html')
const UA_DESKTOP = ' DeskRudderDesktop/1'
const PREFS_INSTALADOR = 'installer-prefs.json'
const INTERVALO_VERIFICAR_MS = 6 * 60 * 60 * 1000
const ATRASO_PRIMEIRA_VERIFICACAO_MS = 20_000

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
/** Fechar a janela esconde na bandeja (true) ou encerra o app (false). */
let alertasNaBandeja = true
/** @type {{ version: string, download_url: string } | null} */
let infoAtualizacao = null
let verificandoAtualizacao = false

/** Ícone do .exe empacotado (barra de tarefas) com fallback para PNG. */
function carregarIconeApp() {
  if (app.isPackaged) {
    const doExe = nativeImage.createFromPath(process.execPath)
    if (!doExe.isEmpty()) return doExe
  }
  const png = nativeImage.createFromPath(ICONE_PNG)
  return png.isEmpty() ? nativeImage.createEmpty() : png
}

// ── Configuração persistida (userData/config.json) ──────────────────────────

function caminhoConfig() {
  return path.join(app.getPath('userData'), 'config.json')
}

function caminhoSessaoDeskRemote() {
  return path.join(app.getPath('userData'), 'deskremote-sessao.json')
}

function salvarSessaoDeskRemote(slug, accessToken, refreshToken) {
  const corpo = montarCorpoSessao(slug, accessToken, refreshToken)
  if (!corpo) return { ok: false }
  fs.mkdirSync(path.dirname(caminhoSessaoDeskRemote()), { recursive: true })
  fs.writeFileSync(caminhoSessaoDeskRemote(), `${JSON.stringify(corpo)}\n`, 'utf8')
  return { ok: true }
}

function limparSessaoDeskRemote() {
  try {
    if (fs.existsSync(caminhoSessaoDeskRemote())) fs.unlinkSync(caminhoSessaoDeskRemote())
  } catch {
    /* ignore */
  }
  return { ok: true }
}

/**
 * Prefs gravadas pelo Setup NSIS (ao lado do .exe).
 * @returns {{ iniciarComWindows?: boolean, alertasNaBandeja?: boolean } | null}
 */
function lerPrefsInstalador() {
  const candidatos = []
  if (app.isPackaged) {
    candidatos.push(path.join(path.dirname(process.execPath), PREFS_INSTALADOR))
    candidatos.push(path.join(process.resourcesPath, PREFS_INSTALADOR))
  } else {
    candidatos.push(path.join(__dirname, '..', PREFS_INSTALADOR))
  }
  for (const p of candidatos) {
    try {
      if (!fs.existsSync(p)) continue
      return JSON.parse(fs.readFileSync(p, 'utf8'))
    } catch {
      /* tenta o próximo */
    }
  }
  return null
}

/**
 * Aplica prefs do Setup uma vez (autostart + modo bandeja).
 * @returns {boolean} true se havia prefs do instalador
 */
function aplicarPrefsInstaladorSeNecessario() {
  const cfg = lerConfig()
  if (cfg.prefsInstaladorAplicadas) {
    if (typeof cfg.alertasNaBandeja === 'boolean') alertasNaBandeja = cfg.alertasNaBandeja
    return true
  }
  const prefs = lerPrefsInstalador()
  if (!prefs) return false
  const iniciar = prefs.iniciarComWindows !== false
  alertasNaBandeja = prefs.alertasNaBandeja !== false
  if (app.isPackaged) definirAutostart(iniciar)
  salvarConfig({
    prefsInstaladorAplicadas: true,
    autostartPerguntado: true,
    alertasNaBandeja,
  })
  return true
}

/** @returns {{ slug?: string, autostartPerguntado?: boolean, avisoBandejaMostrado?: boolean, alertasNaBandeja?: boolean, prefsInstaladorAplicadas?: boolean, atualizacaoAvisada?: string }} */
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

/** Limpa cache HTTP + service workers para o painel refletir o deploy (não apaga login). */
async function limparCacheDoPainel() {
  const sess = session.defaultSession
  try {
    await sess.clearCache()
    await sess.clearStorageData({ storages: ['cachestorage', 'serviceworkers'] })
  } catch (err) {
    console.warn('DeskRudder: falha ao limpar cache do painel', err)
  }
}

async function abrirPainelOuConta() {
  if (!janela) return
  const { slug } = lerConfig()
  if (slug) {
    await limparCacheDoPainel()
    void janela.loadURL(urlPainel(slug), {
      userAgent: `${janela.webContents.getUserAgent()}${UA_DESKTOP}`,
      httpReferrer: { url: urlPainel(slug), policy: 'same-origin' },
      extraHeaders: 'Cache-Control: no-cache\nPragma: no-cache\n',
    })
  } else {
    void janela.loadFile(CONTA_HTML)
  }
}

function caminhosExeRemoto() {
  const x86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)'
  const pf = process.env.ProgramFiles || 'C:\\Program Files'
  return [
    path.join(x86, 'DeskRudder', 'Acesso Remoto', 'DeskRudder.exe'),
    path.join(pf, 'DeskRudder', 'Acesso Remoto', 'DeskRudder.exe'),
  ]
}

function acharExeRemoto() {
  for (const p of caminhosExeRemoto()) {
    try {
      if (fs.existsSync(p)) return p
    } catch {
      /* ignore */
    }
  }
  return null
}

/**
 * Abre sessão remota no DeskRudder Acesso Remoto (Sciter).
 * O cliente instalado só trata `--connect ID [senha]`. O URI deskrudder://
 * (que o RustDesk Flutter oficial aceita) era ignorado — o processo saía
 * com "Wrong command". rustdesk:// continua apontando ao RustDesk oficial.
 * @returns {{ ok: boolean, modo?: string, erro?: string }}
 */
function conectarRemoto(id, senha, tituloSessao) {
  const digitos = String(id || '').replace(/\s+/g, '')
  if (!/^\d{6,}$/.test(digitos)) {
    return { ok: false, erro: 'ID de acesso remoto inválido.' }
  }
  const senhaLimpa = senha != null ? String(senha).trim() : ''
  const titulo = tituloSessao != null ? String(tituloSessao).trim() : ''
  const args = ['--connect', digitos]
  if (senhaLimpa) args.push(senhaLimpa)
  if (titulo) {
    // Sem senha, o Sciter trata o próximo token como senha — usa placeholder vazio.
    if (!senhaLimpa) args.push('')
    args.push('--title', titulo)
  }
  const params = new URLSearchParams()
  if (senhaLimpa) params.set('password', senhaLimpa)
  if (titulo) params.set('name', titulo)
  const consulta = params.toString()
  const url = `deskrudder://connection/new/${digitos}${consulta ? `?${consulta}` : ''}`

  const exe = acharExeRemoto()
  if (exe) {
    try {
      const filho = spawn(exe, args, { detached: true, stdio: 'ignore' })
      filho.unref()
      return { ok: true, modo: 'exe' }
    } catch (err) {
      console.warn('DeskRudder: falha ao abrir exe remoto', err)
    }
  }
  try {
    void shell.openExternal(url)
  } catch (err) {
    console.warn('DeskRudder: falha ao abrir protocolo remoto', err)
    return {
      ok: false,
      erro:
        'Não foi possível abrir o acesso remoto. Confira se o DeskRemote (controle) está instalado.',
    }
  }
  return { ok: true, modo: 'protocolo' }
}

function origemPermitidaPainel(url) {
  if (!url || typeof url !== 'string') return false
  if (url.startsWith('file:')) return true
  return hostDaInstancia(url)
}

ipcMain.handle('conta:definir', async (event, raw) => {
  if (!event.senderFrame?.url.startsWith('file:')) return { ok: false, erro: 'Origem não permitida.' }
  const slug = normalizarSlug(raw)
  if (!slug) return { ok: false, erro: 'Conta inválida. Use o identificador do endereço do painel (ex.: minhaempresa).' }
  const existe = await contaExiste(slug)
  if (existe === null) return { ok: false, erro: 'Sem conexão com a internet. Verifique a rede e tente de novo.' }
  if (!existe) return { ok: false, erro: 'Conta não encontrada. Confira o identificador com o administrador.' }
  salvarConfig({ slug })
  await abrirPainelOuConta()
  return { ok: true }
})

ipcMain.handle('conta:atual', (event) => {
  if (!event.senderFrame?.url.startsWith('file:')) return null
  return lerConfig().slug ?? null
})

ipcMain.handle('remoto:status', (event) => {
  if (!origemPermitidaPainel(event.senderFrame?.url)) return { instalado: false }
  return { instalado: Boolean(acharExeRemoto()), caminho: acharExeRemoto() }
})

ipcMain.handle('remoto:conectar', (event, id, senha, tituloSessao) => {
  if (!origemPermitidaPainel(event.senderFrame?.url)) {
    return { ok: false, erro: 'Origem não permitida.' }
  }
  return conectarRemoto(id, senha, tituloSessao)
})

ipcMain.handle('painel:recarregar', async (event) => {
  if (!origemPermitidaPainel(event.senderFrame?.url) && !event.senderFrame?.url?.startsWith('file:')) {
    return { ok: false }
  }
  await limparCacheDoPainel()
  if (janela) janela.webContents.reloadIgnoringCache()
  return { ok: true }
})

ipcMain.handle('sessao:salvar', (event, accessToken, refreshToken) => {
  const url = event.senderFrame?.url
  if (!origemPainelHttpsInstancia(url)) return { ok: false }
  const slug = slugDaOrigemPainel(url)
  if (!slug) return { ok: false }
  return salvarSessaoDeskRemote(slug, accessToken, refreshToken)
})

ipcMain.handle('sessao:limpar', (event) => {
  if (!origemPermitidaPainel(event.senderFrame?.url) && !event.senderFrame?.url?.startsWith('file:')) {
    return { ok: false }
  }
  return limparSessaoDeskRemote()
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
  const icone = carregarIconeApp()
  janela = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 420,
    minHeight: 560,
    show: false,
    title: 'DeskRudder',
    icon: icone.isEmpty() ? undefined : icone,
    backgroundColor: '#0b1220',
    autoHideMenuBar: false,
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
  montarMenuJanela()

  janela.once('ready-to-show', () => {
    if (!iniciarOculto) janela?.show()
  })

  janela.on('close', (e) => {
    if (saindo) return
    if (!alertasNaBandeja) {
      saindo = true
      return
    }
    e.preventDefault()
    janela?.hide()
    avisarQueContinuaNaBandeja()
  })

  janela.on('focus', () => janela?.flashFrame(false))
  janela.on('page-title-updated', (_e, titulo) => atualizarContagem(titulo))

  const wc = janela.webContents
  try {
    const idiomas = idiomasCorretor(wc.session.availableSpellCheckerLanguages || [])
    if (idiomas.length) wc.session.setSpellCheckerLanguages(idiomas)
  } catch {
    /* Chromium sem dicionário neste SO — o sublinhado nativo segue o padrão do sistema */
  }
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
    const itens = itensMenuContexto(params).map((item) => {
      if (item.role === 'separador') return { type: 'separator' }
      if (item.role === 'sugestao') {
        return { label: item.label, click: () => wc.replaceMisspelling(item.label) }
      }
      if (item.role === 'dicionario') {
        return {
          label: item.label,
          click: () => wc.session.addWordToSpellCheckerDictionary(params.misspelledWord),
        }
      }
      const temImagem = params.mediaType === 'image' && params.hasImageContents
      return {
        label: item.label,
        click: () => (temImagem ? wc.copyImageAt(params.x, params.y) : wc.copy()),
      }
    })
    if (!itens.length) return
    Menu.buildFromTemplate(itens).popup({ window: janela })
  })
  wc.on('before-input-event', (_e, input) => {
    if (input.type !== 'keyDown') return
    if (input.key === 'F5' || (input.control && input.key.toLowerCase() === 'r')) {
      void limparCacheDoPainel().then(() => wc.reloadIgnoringCache())
    }
    if (!app.isPackaged && input.key === 'F12') wc.toggleDevTools()
  })

  // No shell desktop o service worker do PWA compete com o deploy — desregistra no painel.
  wc.on('did-finish-load', () => {
    const url = wc.getURL()
    if (!hostDaInstancia(url)) return
    void wc.executeJavaScript(`
      (async () => {
        try {
          if (!('serviceWorker' in navigator)) return;
          const regs = await navigator.serviceWorker.getRegistrations();
          await Promise.all(regs.map((r) => r.unregister()));
          if (window.caches && caches.keys) {
            const keys = await caches.keys();
            await Promise.all(keys.map((k) => caches.delete(k)));
          }
        } catch (_) {}
      })();
    `).catch(() => {})
  })

  void abrirPainelOuConta()
}

// ── Bandeja e iniciar com o Windows ─────────────────────────────────────────

function autostartAtivo() {
  return app.getLoginItemSettings({ args: [ARG_OCULTO] }).openAtLogin
}

function definirAutostart(ativo) {
  if (!app.isPackaged) return
  app.setLoginItemSettings({ openAtLogin: ativo, args: [ARG_OCULTO] })
}

function versaoAtualApp() {
  return String(app.getVersion() || '0.0.0')
}

function haAtualizacao() {
  return Boolean(infoAtualizacao && compararVersao(infoAtualizacao.version, versaoAtualApp()) > 0)
}

function urlSetupNaInstancia() {
  const { slug } = lerConfig()
  if (!slug) return null
  return `https://${slug}.${APEX}/app/download`
}

function janelaDoDialogo() {
  return janela && !janela.isDestroyed() ? janela : undefined
}

async function buscarInfoAtualizacao() {
  const res = await net.fetch(urlVersionJson(), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      'User-Agent': `DeskRudderDesktop/${versaoAtualApp()}`,
      'Cache-Control': 'no-cache',
    },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const parsed = parseVersionJson(await res.json())
  if (!parsed) throw new Error('version.json inválido')
  return parsed
}

async function verificarAtualizacao({ silencioso } = {}) {
  if (verificandoAtualizacao) return
  verificandoAtualizacao = true
  sincronizarMenus()
  try {
    infoAtualizacao = await buscarInfoAtualizacao()
    const nova = haAtualizacao()
    sincronizarMenus()
    if (!nova) {
      if (!silencioso) {
        await dialog.showMessageBox(janelaDoDialogo(), {
          type: 'info',
          buttons: ['OK'],
          defaultId: 0,
          title: 'DeskRudder',
          message: 'O app já está atualizado',
          detail: `Versão instalada: ${versaoAtualApp()}.`,
        })
      }
      return
    }
    const versaoNova = infoAtualizacao.version
    if (silencioso) {
      const cfg = lerConfig()
      if (cfg.atualizacaoAvisada !== versaoNova && bandeja) {
        bandeja.displayBalloon({
          iconType: 'info',
          title: 'Atualização do DeskRudder',
          content: `A versão ${versaoNova} está disponível. Menu DeskRudder → Atualizar agora.`,
        })
        salvarConfig({ atualizacaoAvisada: versaoNova })
      }
      return
    }
    const { response } = await dialog.showMessageBox(janelaDoDialogo(), {
      type: 'info',
      buttons: ['Atualizar agora', 'Agora não'],
      defaultId: 0,
      cancelId: 1,
      title: 'DeskRudder',
      message: `Há uma versão nova do app (${versaoNova})`,
      detail: `Você está na ${versaoAtualApp()}. A atualização abre o instalador e pode fechar o DeskRudder.`,
    })
    if (response === 0) await baixarEInstalarAtualizacao({ confirmar: false })
  } catch (err) {
    console.warn('DeskRudder: falha ao verificar atualização', err)
    if (!silencioso) {
      await dialog.showMessageBox(janelaDoDialogo(), {
        type: 'warning',
        buttons: ['OK'],
        defaultId: 0,
        title: 'DeskRudder',
        message: 'Não foi possível verificar atualizações',
        detail: 'Confira a internet e tente de novo. Também dá para baixar o app em Sobre, no painel.',
      })
    }
  } finally {
    verificandoAtualizacao = false
    sincronizarMenus()
  }
}

async function baixarEInstalarAtualizacao({ confirmar } = {}) {
  mostrarJanela()
  if (confirmar !== false) {
    const versaoNova = infoAtualizacao?.version
    const { response } = await dialog.showMessageBox(janelaDoDialogo(), {
      type: 'question',
      buttons: ['Atualizar', 'Cancelar'],
      defaultId: 0,
      cancelId: 1,
      title: 'DeskRudder',
      message: versaoNova ? `Instalar a versão ${versaoNova}?` : 'Baixar e instalar a atualização?',
      detail: 'O instalador abre em seguida e o DeskRudder pode fechar.',
    })
    if (response !== 0) return
  }
  if (bandeja) {
    bandeja.displayBalloon({
      iconType: 'info',
      title: 'Atualizando o DeskRudder',
      content: 'Baixando o instalador. O assistente abre em seguida.',
    })
  }
  const candidatos = [
    urlSetupNaInstancia(),
    infoAtualizacao?.download_url,
    urlSetupGithub(),
  ].filter((u) => typeof u === 'string' && downloadUrlPermitida(u))
  if (!candidatos.length) {
    await dialog.showMessageBox(janelaDoDialogo(), {
      type: 'warning',
      buttons: ['OK'],
      title: 'DeskRudder',
      message: 'Não foi possível baixar a atualização',
      detail: 'Tente de novo ou baixe o app em Sobre, no painel.',
    })
    return
  }

  const dest = path.join(app.getPath('temp'), SETUP_NAME)
  let gravou = false
  for (const url of candidatos) {
    try {
      const res = await net.fetch(url, {
        method: 'GET',
        headers: { 'User-Agent': `DeskRudderDesktop/${versaoAtualApp()}` },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const buf = Buffer.from(await res.arrayBuffer())
      if (buf.length < 1_000_000) throw new Error('arquivo pequeno demais')
      fs.writeFileSync(dest, buf)
      gravou = true
      break
    } catch (err) {
      console.warn('DeskRudder: falha ao baixar Setup', url, err)
    }
  }
  if (!gravou) {
    await dialog.showMessageBox(janelaDoDialogo(), {
      type: 'warning',
      buttons: ['OK'],
      title: 'DeskRudder',
      message: 'Não foi possível baixar a atualização',
      detail: 'Tente de novo ou baixe o app em Sobre, no painel.',
    })
    return
  }

  try {
    const filho = spawn(dest, [], { detached: true, stdio: 'ignore' })
    filho.unref()
  } catch (err) {
    console.warn('DeskRudder: falha ao abrir Setup', err)
    await dialog.showMessageBox(janelaDoDialogo(), {
      type: 'warning',
      buttons: ['OK'],
      title: 'DeskRudder',
      message: 'Não foi possível abrir o instalador',
      detail: `O arquivo ficou em ${dest}. Abra-o manualmente se precisar.`,
    })
    return
  }
  saindo = true
  app.quit()
}

async function mostrarSobre() {
  mostrarJanela()
  const atual = versaoAtualApp()
  const nova = haAtualizacao() ? infoAtualizacao.version : null
  const botoes = nova ? ['Atualizar agora', 'Fechar'] : ['Fechar']
  const { response } = await dialog.showMessageBox(janelaDoDialogo(), {
    type: 'info',
    buttons: botoes,
    defaultId: 0,
    cancelId: botoes.length - 1,
    title: 'Sobre o DeskRudder',
    message: 'DeskRudder',
    detail: nova
      ? `Versão do aplicativo: ${atual}\nNova versão disponível: ${nova}\n\nEsta é a versão do app Windows. A versão do painel (Release Notes) fica em Sobre, no menu lateral.`
      : `Versão do aplicativo: ${atual}\n\nEsta é a versão do app Windows. A versão do painel (Release Notes) fica em Sobre, no menu lateral.`,
  })
  if (nova && response === 0) await baixarEInstalarAtualizacao({ confirmar: false })
}

function sincronizarMenus() {
  montarMenuBandeja()
  montarMenuJanela()
}

function itemIniciarComWindows() {
  return {
    label: 'Iniciar com o Windows',
    type: 'checkbox',
    checked: autostartAtivo(),
    enabled: app.isPackaged,
    click: (item) => {
      definirAutostart(item.checked)
      salvarConfig({ autostartPerguntado: true })
      sincronizarMenus()
    },
  }
}

function itemAlertasNaBandeja() {
  return {
    label: 'Manter na bandeja e alertar com o painel fechado',
    type: 'checkbox',
    checked: alertasNaBandeja,
    click: (item) => definirAlertasNaBandeja(item.checked),
  }
}

function itensMenuApp({ incluirAbrir } = {}) {
  const itens = []
  if (incluirAbrir) {
    itens.push({ label: 'Abrir DeskRudder', click: mostrarJanela }, { type: 'separator' })
  }
  itens.push(
    itemIniciarComWindows(),
    itemAlertasNaBandeja(),
    { type: 'separator' },
    {
      label: 'Recarregar painel',
      click: async () => {
        await limparCacheDoPainel()
        janela?.webContents.reloadIgnoringCache()
      },
    },
    { label: 'Trocar empresa…', click: () => void trocarEmpresa() },
    { type: 'separator' },
    {
      label: verificandoAtualizacao ? 'Verificando atualizações…' : 'Verificar atualizações',
      enabled: !verificandoAtualizacao,
      click: () => void verificarAtualizacao({ silencioso: false }),
    },
    {
      label: haAtualizacao() ? `Atualizar agora (${infoAtualizacao?.version})` : 'Atualizar agora',
      visible: haAtualizacao(),
      click: () => void baixarEInstalarAtualizacao(),
    },
    { label: 'Sobre', click: () => void mostrarSobre() },
    { type: 'separator' },
    {
      label: 'Sair',
      click: () => {
        saindo = true
        app.quit()
      },
    },
  )
  return itens
}

function definirAlertasNaBandeja(ativo) {
  alertasNaBandeja = Boolean(ativo)
  salvarConfig({ alertasNaBandeja })
  if (alertasNaBandeja) {
    criarBandeja()
  } else {
    destruirBandeja()
    mostrarJanela()
  }
  sincronizarMenus()
}

function montarMenuJanela() {
  if (!janela) return
  janela.setMenu(
    Menu.buildFromTemplate([
      {
        label: 'DeskRudder',
        submenu: itensMenuApp(),
      },
    ]),
  )
}

function montarMenuBandeja() {
  if (!bandeja) return
  bandeja.setContextMenu(Menu.buildFromTemplate(itensMenuApp({ incluirAbrir: true })))
}

function destruirBandeja() {
  if (!bandeja) return
  bandeja.destroy()
  bandeja = null
}

function criarBandeja() {
  if (bandeja) return
  let img = carregarIconeApp()
  if (img.isEmpty()) img = nativeImage.createFromPath(ICONE_PNG)
  if (!img.isEmpty()) img = img.resize({ width: 32, height: 32 })
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
    detail: 'Assim você recebe os alertas da fila sem precisar abrir o app. Dá para mudar depois no menu DeskRudder.',
  })
  definirAutostart(response === 0)
  salvarConfig({ autostartPerguntado: true })
  sincronizarMenus()
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
  const sess = session.defaultSession
  const ua = sess.getUserAgent()
  if (!ua.includes('DeskRudderDesktop')) {
    sess.setUserAgent(`${ua}${UA_DESKTOP}`)
  }
  const tinhaPrefsSetup = aplicarPrefsInstaladorSeNecessario()
  if (!tinhaPrefsSetup && typeof lerConfig().alertasNaBandeja === 'boolean') {
    alertasNaBandeja = lerConfig().alertasNaBandeja
  }
  const iniciarOculto = alertasNaBandeja && process.argv.includes(ARG_OCULTO)
  if (alertasNaBandeja) criarBandeja()
  criarJanela(iniciarOculto)
  if (!iniciarOculto && !tinhaPrefsSetup) {
    janela?.webContents.once('did-finish-load', () => void perguntarAutostartSeNecessario())
  }
  setTimeout(() => void verificarAtualizacao({ silencioso: true }), ATRASO_PRIMEIRA_VERIFICACAO_MS)
  setInterval(() => void verificarAtualizacao({ silencioso: true }), INTERVALO_VERIFICAR_MS)
})
