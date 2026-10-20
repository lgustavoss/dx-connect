# Cliente acesso remoto DeskRudder (Windows)

**Produto:** builds Windows via GitHub Actions.

| Workflow (Actions) | Profile | Release |
|--------------------|---------|---------|
| **Acesso Remoto Cliente (Windows)** | `posto` | `acesso-remoto-windows` |
| **Acesso Remoto Atendente (Windows)** | `controle` | `acesso-remoto-controle-windows` |
| **App Atendente Setup (Windows)** | Electron (+ baixa o Release controle) | `desktop-windows` |

Atalho **DeskRudder - Acesso Remoto**; pasta `DeskRudder\Acesso Remoto`.  
Docs: [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md), Setup: [`docs/DESKTOP_ELECTRON.md`](../../docs/DESKTOP_ELECTRON.md).

| Pasta / arquivo | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública da Duplex |
| `branding/` | Arte oficial + PNGs/`icon.ico`/`tray-icon.ico` do acesso remoto |
| `branding/icon-source-official.png` | Arte-fonte (DeskRudder Acesso Remoto) |
| `scripts/render_remote_icons.py` | Regenera PNGs/ICO a partir da arte oficial |
| `scripts/apply_branding.py` | Patch no código RustDesk antes do build (inclui ícone Sciter em `get_icon()`) |
| `scripts/encode_config.py` | Debug da string `--config` |
| `windows/Install-DeskRudderRemote.ps1` | Legado / emergência (oficial + config) — **não** é o fluxo principal |
