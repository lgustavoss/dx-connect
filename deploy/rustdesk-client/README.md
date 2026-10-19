# Cliente acesso remoto DeskRudder (Windows)

**Produto:** um `.exe` só — `DeskRudder-AcessoRemoto-*.exe` — gerado pelo GitHub Actions.

Como gerar: ver [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md)  
(Actions → «RustDesk DeskRudder Windows» → Run workflow → baixar o artefato).  
O workflow só aparece em Actions depois de estar na `main`.

| Pasta / arquivo | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública da Duplex |
| `branding/` | Ícones do **acesso remoto** (duas setas opostas; distinto do mark do painel) |
| `scripts/render_remote_icons.py` | Regenera PNGs/`icon.ico`/`tray-icon.ico` a partir do mark de setas |
| `scripts/apply_branding.py` | Patch no código RustDesk antes do build (inclui ícone Sciter em `get_icon()`) |
| `scripts/encode_config.py` | Debug da string `--config` |
| `windows/Install-DeskRudderRemote.ps1` | Legado / emergência (oficial + config) — **não** é o fluxo principal |
