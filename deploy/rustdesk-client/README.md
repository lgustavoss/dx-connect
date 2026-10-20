# Cliente acesso remoto DeskRudder (Windows)

**Produto:** builds Windows via GitHub Actions (`apply_branding.py --profile posto|controle`).

| Profile | Artefato | Release | Comportamento |
|---------|----------|---------|---------------|
| `posto` | `DeskRudder-AcessoRemoto-*.exe` | `acesso-remoto-windows` | Só-recebe (PDV) |
| `controle` | `DeskRudder-AcessoRemoto-Controle-*.exe` | `acesso-remoto-controle-windows` | Atendente / frota; Setup Electron |

Atalho **DeskRudder - Acesso Remoto**; pasta `DeskRudder\Acesso Remoto`.  
Versão: `CLIENT_VERSION`. Update: banner → `version.json` do Release do profile.  
Docs: [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md), Setup atendente: [`docs/DESKTOP_ELECTRON.md`](../../docs/DESKTOP_ELECTRON.md).

| Pasta / arquivo | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública da Duplex |
| `branding/` | **Mesma arte** para `posto` e `controle` — ICO, tray, PNG Sciter e `ui-logo` |
| `branding/icon-source-official.png` | Arte-fonte PNG com alpha (DeskRudder Acesso Remoto) |
| `scripts/render_remote_icons.py` | Regenera PNGs/ICO a partir da arte oficial |
| `scripts/apply_branding.py` | Patch no RustDesk antes do build (`--profile posto\|controle`; branding compartilhado) |

O workflow **RustDesk DeskRudder Windows** usa sempre `deploy/rustdesk-client/branding/` nos dois profiles. Depois de atualizar a arte: regenerar com `render_remote_icons.py`, subir `CLIENT_VERSION` e rodar o Actions duas vezes (`posto` e `controle`).
| `scripts/encode_config.py` | Debug da string `--config` |
| `windows/Install-DeskRudderRemote.ps1` | Legado / emergência (oficial + config) — **não** é o fluxo principal |
