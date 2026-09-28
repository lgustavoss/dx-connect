const { contextBridge, ipcRenderer } = require('electron')

// Só a tela local de conta (file:) usa esta ponte; o main recusa chamadas vindas do painel remoto.
if (location.protocol === 'file:') {
  contextBridge.exposeInMainWorld('deskrudder', {
    definirConta: (slug) => ipcRenderer.invoke('conta:definir', slug),
    contaAtual: () => ipcRenderer.invoke('conta:atual'),
  })
}
