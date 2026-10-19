# Cliente acesso remoto DeskRudder (Windows)

**Produto:** um `.exe` só — `DeskRudder-AcessoRemoto-*.exe` — gerado pelo GitHub Actions.  
Cliente **só-recebe** (postos): ID/senha + status + logo; atalho **DeskRudder - Acesso Remoto**.

Como gerar: ver [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md)  
(Actions → «RustDesk DeskRudder Windows» → Run workflow → artefato **e** Release `acesso-remoto-windows`).  
No painel: **Acesso remoto** → **Baixar instalador Windows**.

| Pasta / arquivo | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública da Duplex |
| `branding/` | Arte oficial + PNGs/`icon.ico`/`tray-icon.ico` do acesso remoto |
| `branding/icon-source-official.png` | Arte-fonte (DeskRudder Acesso Remoto) |
| `scripts/render_remote_icons.py` | Regenera PNGs/ICO a partir da arte oficial |
| `scripts/apply_branding.py` | Patch no código RustDesk antes do build (inclui ícone Sciter em `get_icon()`) |
| `scripts/encode_config.py` | Debug da string `--config` |
| `windows/Install-DeskRudderRemote.ps1` | Legado / emergência (oficial + config) — **não** é o fluxo principal |
