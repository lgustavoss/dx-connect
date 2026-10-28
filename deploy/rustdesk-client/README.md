# Cliente acesso remoto DeskRudder (Windows)

**Produto:** builds Windows via GitHub Actions.

| Workflow (Actions) | Profile | Release |
|--------------------|---------|---------|
| **DeskRemote Cliente v1** | `posto` Sciter **congelado 1.0.14** | `acesso-remoto-windows` |
| **DeskRemote Atendente v1** | `controle` Sciter **congelado 1.0.14** | `acesso-remoto-controle-windows` |
| **DeskRudder Painel v1** | Electron (+ baixa o Atendente v2) | `desktop-windows` |
| **DeskRemote Atendente v2** | Flutter x64 do atendente | `acesso-remoto-controle-flutter-windows` |
| **DeskRemote Cliente v2** | Flutter x64 do cliente (download do painel) | `acesso-remoto-windows-flutter` |

Atalho **DeskRemote**; pasta `DeskRudder\Acesso Remoto` (compatibilidade).  
Docs: [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md), Setup: [`docs/DESKTOP_ELECTRON.md`](../../docs/DESKTOP_ELECTRON.md).

| Pasta / arquivo | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública da Duplex |
| `branding/` | **Mesma arte** para `posto` e `controle` — ICO, tray, PNG Sciter e `ui-logo` |
| `branding/icon-source-final.jpg` | Master 1024 (fundo preto). `render_remote_icons.py` gera o PNG com alpha |
| `branding/icon-source-official.png` | Arte-fonte PNG com alpha (DeskRemote) |
| `branding/kit-1253/` | Kit por local de uso (titlebar, tray, taskbar, ico, Flutter) — issue #1253 |
| `scripts/render_remote_icons.py` | Regenera PNGs/ICO a partir da arte oficial |
| `CLIENT_VERSION` | Sciter **congelado** em **1.0.14** (hotfix 32-bit) |
| `CLIENT_VERSION_FLUTTER` | Flutter do atendente — linha **2.x.x** (2.3.0+ puxa o servidor da conta) |
| `CLIENT_VERSION_FLUTTER_CLIENTE` | Flutter do cliente — linha **2.x.x** (canal separado) |
| `scripts/apply_branding.py` | Patch no RustDesk antes do build (`--profile posto\|controle`; `--ui sciter\|flutter`) |
| `scripts/encode_config.py` | Debug da string `--config` |
| `windows/Install-DeskRudderRemote.ps1` | Legado / emergência (oficial + config) — **não** é o fluxo principal |

Cliente e atendente usam a mesma pasta `branding/`. Depois de atualizar a arte: regenerar com `render_remote_icons.py`, subir a versão do canal (`CLIENT_VERSION` no Sciter, `CLIENT_VERSION_FLUTTER` no Flutter do atendente, `CLIENT_VERSION_FLUTTER_CLIENTE` no Flutter do cliente) e rodar o workflow correspondente.
