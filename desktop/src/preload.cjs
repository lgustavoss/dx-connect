const { contextBridge, ipcRenderer } = require('electron')

const origem = typeof location !== 'undefined' ? location.href : ''
const isFile = origem.startsWith('file:')
const isPainel =
  typeof location !== 'undefined' &&
  location.protocol === 'https:' &&
  (location.hostname === 'deskrudder.com.br' || location.hostname.endsWith('.deskrudder.com.br'))

// Tela local de conta (file:).
if (isFile) {
  contextBridge.exposeInMainWorld('deskrudder', {
    definirConta: (slug) => ipcRenderer.invoke('conta:definir', slug),
    contaAtual: () => ipcRenderer.invoke('conta:atual'),
  })
}

// Painel remoto (https://*.deskrudder.com.br) + conta local: acesso remoto e recarga.
if (isFile || isPainel) {
  contextBridge.exposeInMainWorld('deskrudderDesktop', {
    remotoStatus: () => ipcRenderer.invoke('remoto:status'),
    conectarRemoto: (id, senha) => ipcRenderer.invoke('remoto:conectar', id, senha),
    recarregarPainel: () => ipcRenderer.invoke('painel:recarregar'),
  })
}
