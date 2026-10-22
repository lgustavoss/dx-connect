# Cliente acesso remoto DeskRudder (Windows)

**Produto:** builds Windows via GitHub Actions.

| Workflow (Actions) | Profile | Release |
|--------------------|---------|---------|
| **Acesso Remoto Cliente (Windows)** | `posto` | `acesso-remoto-windows` |
| **Acesso Remoto Atendente (Windows)** | `controle` | `acesso-remoto-controle-windows` |
| **App Atendente Setup (Windows)** | Electron (+ baixa o Release controle) | `desktop-windows` |

Atalho **DeskRemote**; pasta `DeskRudder\Acesso Remoto` (compatibilidade).  
Docs: [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md), Setup: [`docs/DESKTOP_ELECTRON.md`](../../docs/DESKTOP_ELECTRON.md).

| Pasta / arquivo | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública da Duplex |
| `branding/` | **Mesma arte** para `posto` e `controle` — ICO, tray, PNG Sciter e `ui-logo` |
| `branding/icon-source-official.png` | Arte-fonte PNG com alpha (DeskRemote) |
| `scripts/render_remote_icons.py` | Regenera PNGs/ICO a partir da arte oficial |
| `scripts/apply_branding.py` | Patch no RustDesk antes do build (`--profile posto\|controle`; branding compartilhado) |
| `scripts/encode_config.py` | Debug da string `--config` |
| `windows/Install-DeskRudderRemote.ps1` | Legado / emergência (oficial + config) — **não** é o fluxo principal |

Cliente e atendente usam a mesma pasta `branding/`. Depois de atualizar a arte: regenerar com `render_remote_icons.py`, subir `CLIENT_VERSION` e rodar **Acesso Remoto Cliente** e **Acesso Remoto Atendente**.
