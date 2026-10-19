# Cliente acesso remoto DeskRudder (Windows)

**Produto:** um `.exe` só — `DeskRudder-AcessoRemoto-*.exe` — gerado pelo GitHub Actions.

Como gerar: ver [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md)  
(Actions → «RustDesk DeskRudder Windows» → Run workflow → baixar o artefato).  
O workflow só aparece em Actions depois de estar na `main`.

| Pasta / arquivo | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública da Duplex |
| `branding/` | Ícones DeskRudder |
| `scripts/apply_branding.py` | Patch no código RustDesk antes do build |
| `scripts/encode_config.py` | Debug da string `--config` |
| `windows/Install-DeskRudderRemote.ps1` | Legado / emergência (oficial + config) — **não** é o fluxo principal |
